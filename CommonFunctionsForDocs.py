import os
import re
import zlib
import base64
import io
import unicodedata
from helperfunctions import *
from PIL import Image


def parse_pdf_to_spans(PDFPath):
    PDF = open(PDFPath, "rb")
    
    PDFSize = os.path.getsize(PDFPath)

    PDFVersion = PDFVersionFunc(PDFPath)

    xrefResult = XrefTableFunc(PDFPath)

    if isinstance(xrefResult, tuple):
        AllXrefTable, XrefTableAddress = xrefResult
    else:
        AllXrefTable = xrefResult

        firstEntry = next(iter(AllXrefTable.values())) if AllXrefTable else 0
        firstOffset = firstEntry.get('offset', 0) if isinstance(firstEntry, dict) else firstEntry
        XrefTableAddress = [firstOffset] if AllXrefTable else [0]

    if isinstance(XrefTableAddress, list) and XrefTableAddress:
        XrefTableAddress = XrefTableAddress[-1]

    XrefTable = AllXrefTable

    validOffsets = []
    for entry in XrefTable.values():
        if entry.get('type') == "n": #objects in use
            validOffsets.append(entry['offset'])

    sortedOffsets = sorted(set(validOffsets))
    sortedOffsets.append(XrefTableAddress)

    #encrypted PDFs have scrambled streams, so say so instead of writing a garbage document
    PDF.seek(max(0, PDFSize - 2048))
    encryptCheck = PDF.read()
    if isinstance(XrefTableAddress, int):
        PDF.seek(XrefTableAddress)
        encryptCheck += PDF.read(2048)
    if b"/Encrypt" in encryptCheck:
        PDF.close()
        raise ValueError("This PDF is encrypted, so it can't be converted")

    objStmCache = {} #so every object stream is only decompressed once

    #Finds where one object ends (its endobj) in the bytes read so far, or None if more bytes are needed.
    #Streams are skipped using /Length so binary data that happens to contain "endobj" can't cut the object short
    def cutObject(data):
        endObj = data.find(b"endobj")
        streamStart = re.search(rb"[>\s]stream(?:\r\n|\n|\r)", data)
        if streamStart and (endObj == -1 or streamStart.start() < endObj):
            lengthMatch = re.search(rb"/Length\s+(\d+)(?!\d|\s+\d+\s+R)", data[:streamStart.start()])
            if lengthMatch:
                skip = streamStart.end() + int(lengthMatch.group(1))
                if len(data) < skip + 12:
                    return None
                if data[skip:skip + 12].lstrip().startswith(b"endstream"):
                    endStream = skip
                else:
                    endStream = data.find(b"endstream", streamStart.end())
            else:
                endStream = data.find(b"endstream", streamStart.end())
            if endStream == -1:
                return None
            endObj = data.find(b"endobj", endStream)
        return None if endObj == -1 else data[:endObj]

    #Returns the bytes of an object as "ID 0 obj ... endobj", for normal AND compressed objects
    def GetObjectBytes(objectID):
        entry = XrefTable.get(objectID)

        if not entry or entry.get('type') == "f":
            return b""

        if entry.get('type') == "compressedInsideStream":
            #for these, 'offset' is NOT a file position. It is the ID of the object stream that holds it
            body = ReadObjectStream(entry['offset']).get(objectID, b"")
            return f"{objectID} 0 obj\n".encode('latin1') + body + b"\nendobj\n"

        PDF.seek(entry['offset'])
        data = b""
        while True:
            more = PDF.read(65536)
            if not more:
                return data.split(b"endobj")[0]      #end of file: use what there is
            data += more
            cut = cutObject(data)
            if cut is not None:
                return cut

    #Opens one object stream and returns {objectID: bytes of that object}
    def ReadObjectStream(streamID):
        if streamID in objStmCache:
            return objStmCache[streamID]

        streamObject = GetObjectBytes(streamID)

        countMatch = re.search(rb'/N\s+(\d+)', streamObject)         #how many objects are inside
        firstMatch = re.search(rb'/First\s+(\d+)', streamObject)     #where the objects start after the id/offset list
        if not countMatch or not firstMatch:
            return {}
        count = int(countMatch.group(1))
        first = int(firstMatch.group(1))

        start = streamObject.find(b"stream") + 6
        if streamObject[start:start + 2] == b"\r\n":
            start += 2
        elif streamObject[start:start + 1] == b"\n":
            start += 1

        end = streamObject.rfind(b"endstream")
        decompressed = zlib.decompressobj().decompress(streamObject[start:end])

        #the start of the stream is a list like: id1 offset1 id2 offset2 ...
        numbers = decompressed[:first].split()
        result = {}
        for i in range(count):
            objectID = int(numbers[2 * i])
            offset = int(numbers[2 * i + 1])
            if i + 1 < count:
                nextOffset = int(numbers[2 * i + 3])
            else:
                nextOffset = len(decompressed) - first
            result[objectID] = decompressed[first + offset: first + nextOffset].strip()

        objStmCache[streamID] = result
        return result

    RootObjectID = RootObjectIDFunc(PDFPath)

    CatalogObjectID = RootObjectID

    buffer = GetObjectBytes(CatalogObjectID)

    pagesRefMatch = re.search(rb'/Pages\s+(\d+)\s+(\d+)\s+R', buffer)

    if pagesRefMatch:
        pagesObjectID = int(pagesRefMatch.group(1))
        pagesBuffer = GetObjectBytes(pagesObjectID)

        countMatch = re.search(rb'/Count\s+(\d+)', pagesBuffer)
        
        if countMatch:
            numberOfPages = int(countMatch.group(1))
        else:
            numberOfPages = 0
    else:
        pagesObjectID = None
        numberOfPages = 0

    #Turns the hex destination of a cmap entry into text (UTF-16BE, so ligatures like fi and surrogate pairs work)
    def hexToText(hexStr):
        hexStr = re.sub(r"\s+", "", hexStr)
        if len(hexStr) <= 2:
            return chr(int(hexStr, 16)) if hexStr else ""
        if len(hexStr) % 4:
            hexStr = hexStr.zfill(len(hexStr) + 4 - len(hexStr) % 4)
        return bytes.fromhex(hexStr).decode("utf-16-be", errors="ignore")

    #This function parses /Tounicode Cmap stream into a dictionary map {hex_code: unicode_char}. Copied from ReadPDF.py
    def parseCmap(cmapBytes):
        cmap = {}
        cmapText = cmapBytes.decode("latin1", errors="ignore")

        # Parse beginbfchar ... endbfchar
        bfcharStart = 0
        while True:
            pos = cmapText.find("beginbfchar", bfcharStart)
            if pos == -1:
                break
            endPos = cmapText.find("endbfchar", pos)
            if endPos == -1:
                break

            block = cmapText[pos + 11 : endPos].strip()
            lines = block.splitlines()
            for line in lines:
                parts = re.findall(r"<([0-9A-Fa-f\s]*)>", line)     #works with "<01> <0041>" and "<01><0041>"
                if len(parts) >= 2:
                    srcHex, dstHex = re.sub(r"\s+", "", parts[0]).upper(), parts[1]
                    # Convert hex sequence to string
                    try:
                        charCode = hexToText(dstHex)
                        cmap[srcHex] = charCode
                    except:
                        pass
            bfcharStart = endPos + 9

        # Parse beginbfrange ... endbfrange
        bfrangeStart = 0
        while True:
            pos = cmapText.find("beginbfrange", bfrangeStart)
            if pos == -1:
                break
            endPos = cmapText.find("endbfrange", pos)
            if endPos == -1:
                break

            block = cmapText[pos + 12 : endPos].strip()
            for line in re.findall(r"<[^>]*>\s*<[^>]*>\s*(?:\[[^\]]*\]|<[^>]*>)", block):   #a range can span many lines: <lo> <hi> [ <d1> <d2> ... ]
                parts = re.findall(r"<([0-9A-Fa-f\s]*)>", line)
                if len(parts) >= 3:
                    srcStart = parts[0].strip("<>").upper()
                    srcEnd = parts[1].strip("<>").upper()

                    if srcStart and srcEnd:
                        try:
                            startVal = int(srcStart, 16)
                            endVal = int(srcEnd, 16)
                            hexLen = len(srcStart)

                            # Range to single array: <srcStart> <srcEnd> [<dst1> <dst2>]
                            if "[" in line:
                                arrTokens = parts[2:]
                                for idx, codeVal in enumerate(range(startVal, endVal + 1)):
                                    if idx < len(arrTokens):
                                        srcKey = f"{codeVal:0{hexLen}X}"
                                        dstHex = arrTokens[idx]
                                        cmap[srcKey] = hexToText(dstHex)
                            # Continuous sequence: <srcStart> <srcEnd> <dstStart>
                            else:
                                dst_start = parts[2].strip("<>")
                                dstVal = int(dst_start, 16)
                                for idx, codeVal in enumerate(range(startVal, endVal + 1)):
                                    srcKey = f"{codeVal:0{hexLen}X}"
                                    cmap[srcKey] = chr(dstVal + idx)
                        except:
                            pass

            bfrangeStart = endPos + 10

        return cmap

    #Function which extracts and decompresses a PDF stream object
    def readandDecompressStream(objectID):
        data = GetObjectBytes(objectID)

        m = re.search(rb"stream\r?\n", data)
        if not m:
            return b""
        header = data[:m.start()]
        end = data.find(b"endstream", m.end())
        lengthMatch = re.search(rb"/Length\s+(\d+)(?!\d|\s+\d+\s+R)", header)
        if lengthMatch and data[m.end() + int(lengthMatch.group(1)):].lstrip().startswith(b"endstream"):
            end = m.end() + int(lengthMatch.group(1))
        raw = data[m.end():end if end != -1 else len(data)]
        if raw.endswith(b"\r\n"):
            raw = raw[:-2]
        elif raw.endswith(b"\n") or raw.endswith(b"\r"):
            raw = raw[:-1]

        #apply every filter the stream lists, in order (e.g. [/ASCII85Decode /FlateDecode] from ReportLab)
        filterMatch = re.search(rb"/Filter\s*(\[[^\]]*\]|/[A-Za-z0-9]+)", header)
        try:
            for name in re.findall(rb"/([A-Za-z0-9]+)", filterMatch.group(1)) if filterMatch else []:
                if name in (b"ASCIIHexDecode", b"AHx"):
                    hexDigits = re.sub(rb"[^0-9A-Fa-f]", b"", raw.split(b">")[0])
                    raw = bytes.fromhex((hexDigits + b"0" * (len(hexDigits) % 2)).decode())
                elif name in (b"ASCII85Decode", b"A85"):
                    raw = raw.strip()
                    if raw.startswith(b"<~"):
                        raw = raw[2:]
                    if raw.endswith(b"~>"):
                        raw = raw[:-2]
                    raw = base64.a85decode(raw)
                elif name in (b"FlateDecode", b"Fl"):
                    try:
                        raw = zlib.decompressobj().decompress(raw)   # tolerates trailing junk
                    except zlib.error:
                        raw = zlib.decompressobj(-zlib.MAX_WBITS).decompress(raw)
        except Exception:
            pass
        return raw

    def readObject(objID):
        #Return the raw bytes of exactly one object (up to its endobj).
        return GetObjectBytes(objID).split(b"endobj")[0]

    #Maps the XObject names of a resources dictionary (Im0, R, Fm1...) to object ids
    def xobjectMap(resBuffer):
        rr = re.search(rb"/Resources\s*(\d+)\s+\d+\s+R", resBuffer)
        if rr and b"/XObject" not in resBuffer:
            resBuffer = readObject(int(rr.group(1)))
        xm = re.search(rb"/XObject\s*(?:(\d+)\s+\d+\s+R|(<<))", resBuffer)
        xd = (readObject(int(xm.group(1))) if xm.group(1) else balancedDict(resBuffer, xm.start(2))) if xm else b""
        return {n.decode('latin1'): int(i) for n, i in re.findall(rb"/([^\s/<>\[\]()]+)\s+(\d+)\s+\d+\s+R", xd)}

    def expandForms(content, local, fontsMap, xobjects, depth=0):
        def inline(m):
            fid = local.get(m.group(1).decode('latin1'))
            head = GetObjectBytes(fid).split(b"stream")[0] if fid else b""
            if not re.search(rb"/Subtype\s*/Form", head) or depth > 5:
                return m.group(0)
            pre = f"f{fid}_".encode()
            resBuf = head
            rr = re.search(rb"/Resources\s*(\d+)\s+\d+\s+R", head)
            if rr:
                resBuf = readObject(int(rr.group(1)))
            savedInfo, savedUndec = dict(fontInfo), set(undecodable)
            fontInfo.clear()
            undecodable.clear()
            formFonts = fontDictFinder(resBuf)
            formInfo, formUndec = dict(fontInfo), set(undecodable)
            fontInfo.clear()
            fontInfo.update(savedInfo)
            undecodable.clear()
            undecodable.update(savedUndec)
            for n in set(formFonts) | formUndec | set(formInfo):
                fontsMap[pre.decode() + n] = formFonts.get(n, {})
                fontInfo[pre.decode() + n] = formInfo.get(n)
                if n in fontWidths: fontWidths[pre.decode() + n] = fontWidths[n]      #the form's widths too, under its renamed font
                if n in formUndec:
                    undecodable.add(pre.decode() + n)
            formX = xobjectMap(resBuf)
            body = expandForms(readandDecompressStream(fid), formX, fontsMap, xobjects, depth + 1)
            def rename(r):
                n = r.group(1).decode('latin1')
                return b"/" + pre + r.group(1) + r.group(2) if n in fontsMap_names else r.group(0)
            fontsMap_names = set(formFonts) | formUndec | set(formInfo)
            body = re.sub(rb"/([^\s/<>\[\]()]+)(\s+-?[\d.]+\s+Tf\b)", rename, body)
            def renameImg(r):
                n = r.group(1).decode('latin1')
                if n in formX:
                    xobjects[pre.decode() + n] = formX[n]
                    return b"/" + pre + r.group(1) + r.group(2)
                return r.group(0)
            body = re.sub(rb"/([^\s/<>\[\]()]+)(\s+Do\b)", renameImg, body)
            mx = re.search(rb"/Matrix\s*\[([^\]]*)\]", head)
            return b"\nq " + (mx.group(1) + b" cm" if mx else b"") + b"\n" + body + b"\nQ\n"
        return re.sub(rb"/([^\s/<>\[\]()]+)\s+Do\b", inline, content)

    #Turns an image XObject into PNG/JPEG bytes Word can embed (None if it can't be decoded: masks, indexed colour, CCITT/JBIG2...)
    def imageBytes(objectID):
        try:
            header = GetObjectBytes(objectID).split(b"stream")[0]
            if not re.search(rb"/Subtype\s*/Image", header) or re.search(rb"/ImageMask\s+true", header):
                return None
            raw = readandDecompressStream(objectID)
            w, h = [int(re.search(rb"/" + k + rb"\s+(\d+)", header).group(1)) for k in (b"Width", b"Height")]
            smask = re.search(rb"/SMask\s+(\d+)\s+\d+\s+R", header)
            if re.search(rb"/(DCT|JPX)Decode", header):
                if smask is None and b"/DCTDecode" in header and raw[6:10] in (b"JFIF", b"Exif"):   #python-docx only accepts JPEGs with these markers
                    return raw                                    #a JPEG is already a normal image file
                im = Image.open(io.BytesIO(raw))
            else:
                cs = re.search(rb"/ColorSpace\s*(\[[^\]]*\]|/\w+|\d+\s+\d+\s+R)", header)
                cs = cs.group(1) if cs else b"/DeviceGray"
                if cs[:1].isdigit():
                    cs = readObject(int(cs.split()[0]))
                icc = re.search(rb"/ICCBased\s+(\d+)", cs)
                n = int(re.search(rb"/N\s+(\d)", readObject(int(icc.group(1)))).group(1)) if icc else 3 if b"RGB" in cs else 4 if b"CMYK" in cs else 1
                bpc = int(re.search(rb"/BitsPerComponent\s+(\d+)", header).group(1))
                if b"/Indexed" in cs or (bpc != 8 and not (bpc == 1 and n == 1)):
                    return None
                pm = re.search(rb"/Predictor\s+(\d+)", header)
                if pm and int(pm.group(1)) >= 10:
                    raw = removePNGPredictor(raw, (w * n * bpc + 7) // 8, 0, max(1, n * bpc // 8))
                im = Image.frombytes("1" if bpc == 1 else {1: "L", 3: "RGB", 4: "CMYK"}[n], (w, h), raw)
            if smask:                                              #transparency
                alpha = Image.open(io.BytesIO(imageBytes(int(smask.group(1))))).convert("L").resize(im.size)
                im = im.convert("RGB")
                im.putalpha(alpha)
            if im.mode not in ("1", "L", "RGB", "RGBA"):
                im = im.convert("RGB")
            buf = io.BytesIO()
            im.save(buf, "PNG")
            return buf.getvalue()
        except Exception:
            return None

    fontInfo = {}   #font resource name -> BaseFont, refilled for every page by fontDictFinder
    undecodable, fontWidths = set(), {}   #two-byte (Identity-H) fonts without a ToUnicode map: their codes can't be turned into text
    SYMS = {('AllAndNone', k): v for k, v in {'0093': '(', '0094': ')', '00CC': '\u03c0', '00ED': '\u03b2', '00F6': '\u03b8', '0100': '\u211d', '0101': '\u2208', '0106': '\u2264', '00FA': '>', '00F8': '<'}.items()}   #symbol glyphs whose ToUnicode entry is a plain letter or digit

    def pdfUnescape(raw):
        #Decode the escapes inside a PDF literal string ( \\n \\( \\) \\\\ \\ddd ) into bytes
        simple = {ord('n'): 10, ord('r'): 13, ord('t'): 9, ord('b'): 8, ord('f'): 12,
                    ord('('): 40, ord(')'): 41, ord('\\'): 92}
        out = bytearray()
        i = 0
        while i < len(raw):
            c = raw[i]
            if c == 0x5C and i + 1 < len(raw):
                n = raw[i + 1]
                if n in simple:
                    out.append(simple[n])
                    i += 2
                elif 48 <= n <= 55:
                    j, val, cnt = i + 1, 0, 0
                    while j < len(raw) and cnt < 3 and 48 <= raw[j] <= 55:
                        val = val * 8 + (raw[j] - 48)
                        j += 1
                        cnt += 1
                    out.append(val & 0xFF)
                    i = j
                elif n in (10, 13):
                    i += 2
                    if n == 13 and i < len(raw) and raw[i] == 10:
                        i += 1
                else:
                    out.append(n)
                    i += 2
            else:
                out.append(c)
                i += 1
        return bytes(out)

    def balancedDict(buf, start):
        #buf[start:] begins with '<<'; return the full << ... >> including nesting.
        depth, i = 0, start
        while i < len(buf) - 1:
            two = buf[i:i+2]
            if two == b"<<":
                depth += 1
                i += 2
            elif two == b">>":
                depth -= 1
                i += 2
                if depth == 0:
                    return buf[start:i]
            else:
                i += 1
        return buf[start:]

    GLYPHS = {'space': ' ', 'bullet': '\u2022', 'hyphen': '-', 'endash': '\u2013', 'emdash': '\u2014', 'quoteright': '\u2019', 'quoteleft': '\u2018', 'quotedblleft': '\u201c', 'quotedblright': '\u201d', 'quotesingle': "'", 'quotedbl': '"',
                'period': '.', 'comma': ',', 'colon': ':', 'semicolon': ';', 'exclam': '!', 'question': '?', 'parenleft': '(', 'parenright': ')', 'bracketleft': '[', 'bracketright': ']', 'slash': '/', 'plus': '+', 'minus': '-', 'equal': '=', 'less': '<', 'greater': '>',
                'asterisk': '*', 'ampersand': '&', 'at': '@', 'percent': '%', 'dollar': '$', 'numbersign': '#', 'underscore': '_', 'fi': '\ufb01', 'fl': '\ufb02', 'ellipsis': '\u2026', 'degree': '\u00b0', 'copyright': '\u00a9', 'registered': '\u00ae', 'trademark': '\u2122', 'Euro': '\u20ac', 'germandbls': '\u00df'}
    GLYPHS.update(zip("zero one two three four five six seven eight nine".split(), "0123456789"))
    def glyphChar(g):
        m = re.fullmatch(r'[A-Za-z](acute|grave|circumflex|dieresis|tilde|ring|cedilla|caron)', g)
        try: return g if len(g) == 1 else GLYPHS[g] if g in GLYPHS else chr(int(g[3:], 16)) if re.fullmatch(r'uni[0-9A-Fa-f]{4}', g) else unicodedata.lookup(f"LATIN {'CAPITAL' if g[0].isupper() else 'SMALL'} LETTER {g[0].upper()} WITH {({'dieresis': 'DIAERESIS', 'ring': 'RING ABOVE'}).get(m.group(1), m.group(1).upper())}")
        except Exception: return ''
    def diffMap(arr):
        out, code = {}, 0
        for tok in re.findall(rb"/[^\s/\[\]]+|\d+", arr):
            if tok.isdigit(): code = int(tok)
            else: out[f"{code:02X}"], code = glyphChar(tok[1:].decode('latin1')), code + 1
        return {k: v for k, v in out.items() if v}
    def toRGB(nums, op):
        v = [float(n) for n in nums.split()][-{b'g': 1, b'rg': 3, b'k': 4}[op]:]
        v = v * 3 if op == b'g' else [(1 - c) * (1 - v[3]) for c in v[:3]] if op == b'k' and len(v) == 4 else v
        return tuple(int(max(0, min(1, c)) * 255) for c in v) if len(v) == 3 else (0, 0, 0)
    def fontDictFinder(resBuffer):
        fontcMaps = {}
        resBuffer = resBuffer.split(b"endobj")[0]      # never look past this object

        m = re.search(rb"/Font\b", resBuffer)
        if not m:
            # we were given the page object: follow /Resources N 0 R
            r = re.search(rb"/Resources\s+(\d+)\s+\d+\s+R", resBuffer)
            if r:
                return fontDictFinder(readObject(int(r.group(1))))
            return fontcMaps

        rest = resBuffer[m.end():]
        ref = re.match(rb"\s*(\d+)\s+\d+\s+R", rest)       # /Font 12 0 R
        if ref:
            rest = readObject(int(ref.group(1)))
        start = rest.find(b"<<")                            # /Font << ... >>
        if start == -1:
            return fontcMaps
        inner = balancedDict(rest, start)[2:-2]

        # entries are either  /F1 5 0 R   or an embedded  /F1 << ... >>
        entry = re.compile(rb"(/[^\s/<>\[\]()]+)(?:\s+(\d+)\s+\d+\s+R|\s*(<<))")
        pos = 0
        while True:
            e = entry.search(inner, pos)
            if not e:
                break
            name = e.group(1).decode("latin1").lstrip('/')
            if e.group(2):
                fontBuf = readObject(int(e.group(2)))
                pos = e.end()
            else:
                fontBuf = balancedDict(inner, e.start(3))
                pos = e.start(3) + len(fontBuf)

            bf = re.search(rb"/BaseFont\s*/([^\s/<>\[\]()]+)", fontBuf)
            if bf:
                fontInfo[name] = bf.group(1).decode("latin1")

            fc, ws = re.search(rb"/FirstChar\s+(\d+)", fontBuf), re.search(rb"/Widths\s*(\d+\s+\d+\s+R|\[[^\]]*\])", fontBuf)
            if fc and ws: fontWidths[name] = (int(fc.group(1)), [float(v) for v in re.findall(rb"-?[\d.]+", re.search(rb"\[[^\]]*\]", readObject(int(ws.group(1).split()[0])) if ws.group(1)[-1:] == b'R' else ws.group(1)).group(0))])
            if (df := re.search(rb"/DescendantFonts\s*\[\s*(\d+)\s+\d+\s+R", fontBuf)) and (wa := re.search(rb"/W\s*\[", cidBuf := readObject(int(df.group(1))))):      #widths of a two-byte font: [first [w w ..]] or [first last w]
                toks, cw, k = re.findall(rb"\[[^\]]*\]|-?[\d.]+|\]", cidBuf[wa.end():]), {}, 0
                while k + 1 < len(toks) and toks[k] != b']':
                    if toks[k + 1][:1] == b'[': cw.update({int(toks[k]) + j: float(v) for j, v in enumerate(re.findall(rb"-?[\d.]+", toks[k + 1]))}); k += 2
                    else: cw.update({c: float(toks[k + 2]) for c in range(int(toks[k]), int(toks[k + 1]) + 1)}); k += 3
                fontWidths[name] = (0, [cw.get(i, 1000.0) for i in range(max(cw, default=0) + 1)])
            tu = re.search(rb"/ToUnicode\s+(\d+)\s+\d+\s+R", fontBuf)
            if tu:
                fontcMaps[name] = parseCmap(readandDecompressStream(int(tu.group(1))))
            elif b"/Identity-H" in fontBuf:
                undecodable.add(name)
            elif dm := re.search(rb"/Differences\s*\[([^\]]*)\]", readObject(int(enc.group(1))) if (enc := re.search(rb"/Encoding\s+(\d+)\s+\d+\s+R", fontBuf)) else fontBuf):
                fontcMaps[name] = diffMap(dm.group(1))
            elif b"/MacRomanEncoding" in fontBuf: fontcMaps[name] = {f"{c:02X}": bytes([c]).decode('mac_roman') for c in range(128, 256)}
        return fontcMaps

    #Page attributes like /Resources and /MediaBox can be written only on a parent /Pages node, so walk up through /Parent until one has the key
    def findInherited(pageBuffer, key):
        current = pageBuffer
        for _ in range(32):
            if key in current:
                return current
            parent = re.search(rb"/Parent\s+(\d+)\s+\d+\s+R", current)
            if not parent:
                break
            current = readObject(int(parent.group(1)))
        return pageBuffer

    allElements = []

    def pageParser(currentObjectID):
        pagesIDGenList = []
        buffer = readObject(currentObjectID)
        kidsIndex = buffer.find(b"/Kids")

        if kidsIndex == -1:
            return 

        startBracket = buffer.find(b"[", kidsIndex)
        endBracket = buffer.find(b"]", startBracket)

        kidsList = buffer[startBracket + 1 : endBracket].split()

        for i in range(len(kidsList)):
            if kidsList[i] == b"R":
                objectID = int(kidsList[i-2].decode('latin1'))
                objectGen = int(kidsList[i-1].decode('latin1'))
                pagesIDGenList.append([objectID, objectGen])


        for pages in pagesIDGenList:
            pageID = pages[0]
            pageGen = pages[1]

            buffer = readObject(pageID)

            contentIndex = buffer.find(b"/Contents")
            subkidsIndex = buffer.find(b"/Kids")

            if contentIndex != -1:
                #/Contents is either one reference or an array of references
                cm = re.search(rb'/Contents\s*(\[[^\]]*\]|\d+\s+\d+\s+R)', buffer)
                contentIDs = [int(n) for n in re.findall(rb'(\d+)\s+\d+\s+R', cm.group(1))] if cm else []

                decompressedStreamData = b"\n".join(readandDecompressStream(cid) for cid in contentIDs)

                #Parsing all text operators (BT TJ Tj ET)
                '''
                BT = start text
                ET = end text 
                Tf = fonts 
                Td TD = text positions
                Tm = text Matrix for positioning
                Ts = text rise for superscripts sub scripts
                TL = line spacing
                Tr = Text rendering mode for hidden text
                Tj = text string
                TJ = text from array 
                '''
                textBlockPattern = re.compile(rb'\bBT\b(.*?)\bET\b', re.DOTALL)

                #Getting the fontsCMap table
                resSource = findInherited(buffer, b"/Resources")   #Resources can be inherited from a parent /Pages node
                resourceIndex = resSource.find(b"/Resources")
                resBuffer = resSource
                fontInfo.clear()
                undecodable.clear()

                if resourceIndex != -1: 
                    resourceLine = resSource[resourceIndex:].split(b"\n")[0]
                    resourceList = resourceLine.split() #This will get us the list of stuff around /resources. There the object id of resources would be written in the next index. We will use the Xreftabelo and object id to get the location of resources 

                    resourceObject = None
                    resourceObjectID = None
                    
                    for idx, token in enumerate(resourceList):
                            if token == b"/Resources" and idx + 1 < len(resourceList):
                                if resourceList[idx + 1].isdigit():
                                    resourceObjectID = int(resourceList[idx + 1].decode("latin1"))
                                    break

                    resBuffer = resSource
                    if resourceObjectID and resourceObjectID in XrefTable:
                            resBuffer = readObject(resourceObjectID)     #PDF.read(4096)

                #Images processing
                xobjects = xobjectMap(resBuffer)

                fontscMap = fontDictFinder(resBuffer) #This maps each font F1 F2 F5 etc to a dict with each value(but in hexadecimal). but I will do that at the end of the code.
                decompressedStreamData = expandForms(decompressedStreamData, xobjects, fontscMap, xobjects)
                
                #Work out the cm transform active at each BT block so positions are comparable across blocks
                ctmOps = re.compile(rb'(?<![A-Za-z0-9*])(q|Q)(?![A-Za-z0-9*])|((?:-?[\d.]+\s+){5}-?[\d.]+)\s+cm\b|/([^\s/<>\[\]()]+)\s+Do\b|((?:-?[\d.]+\s+){0,3}-?[\d.]+)\s+(rg|g|k)\b|((?:-?[\d.]+\s+){3}-?[\d.]+)\s+re\b|(-?[\d.]+)\s+(-?[\d.]+)\s+m\s+(-?[\d.]+)\s+(-?[\d.]+)\s+l\b')
                opsList = list(ctmOps.finditer(decompressedStreamData))
                ctmStack, ctmNow, opIdx, colNow, blockEnd = [], (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 0, (0, 0, 0), 0
                textBlocks, placedImages, rules = [], [], []
                for bm in list(textBlockPattern.finditer(decompressedStreamData)) + [None]:   #None = the ops after the last text block
                    while opIdx < len(opsList) and (bm is None or opsList[opIdx].start() < bm.start()):
                        om = opsList[opIdx]
                        if om.group(1) and om.start() < blockEnd: pass          #a lone q or Q inside a text block is just a letter
                        elif om.group(1) == b'q':
                            ctmStack.append((ctmNow, colNow))
                        elif om.group(1) == b'Q':
                            if ctmStack:
                                ctmNow, colNow = ctmStack.pop()
                        elif om.group(3):
                            placedImages.append((om.group(3).decode('latin1'), ctmNow))
                        elif om.group(5): colNow = toRGB(om.group(4), om.group(5))
                        elif om.group(6) or om.group(7):
                            v = [float(g) for g in (om.group(6).split() if om.group(6) else om.group(7, 8, 9, 10))]
                            w, h = (v[2], v[3]) if om.group(6) else (v[2] - v[0], v[3] - v[1])
                            if abs(ctmNow[3] * h) <= 1.5 and abs(ctmNow[0] * w) > 3: rules.append((*sorted((ctmNow[0] * v[0] + ctmNow[4], ctmNow[0] * (v[0] + w) + ctmNow[4])), ctmNow[3] * (v[1] + h / 2) + ctmNow[5]))
                        else:
                            a, b, c, d, e, f = [float(v) for v in om.group(2).split()]
                            a0, b0, c0, d0, e0, f0 = ctmNow
                            ctmNow = (a*a0 + b*c0, a*b0 + b*d0, c*a0 + d*c0, c*b0 + d*d0, e*a0 + f*c0 + e0, e*b0 + f*d0 + f0)
                        opIdx += 1
                    if bm:
                        textBlocks.append((bm.group(1), ctmNow, colNow))
                        blockEnd = bm.end()
                box = None
                mediaBox = re.search(rb"/MediaBox\s*\[\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*\]", findInherited(buffer, b"/MediaBox"))
                if mediaBox:
                    bx0, by0, bx1, by1 = [float(v) for v in mediaBox.groups()]
                    box = (min(bx0, bx1), min(by0, by1), max(bx0, bx1), max(by0, by1))
                links, am = [], re.search(rb'/Annots\s*(\[[^\]]*\]|\d+\s+\d+\s+R)', buffer)
                for aid in re.findall(rb'(\d+)\s+\d+\s+R', (am.group(1) if am.group(1).startswith(b'[') else readObject(int(am.group(1).split()[0]))) if am else b''):
                    ab = readObject(int(aid))
                    ab += readObject(int(ref.group(1))) if (ref := re.search(rb'/A\s+(\d+)\s+\d+\s+R', ab)) else b''
                    u, r = re.search(rb'/URI\s*\(((?:\\.|[^\\()])*)\)', ab), re.search(rb'/Rect\s*\[([^\]]*)\]', ab)
                    if u and r and b'/Link' in ab:
                        q = [float(v) for v in r.group(1).split()]
                        links.append(((min(q[0], q[2]), min(q[1], q[3]), max(q[0], q[2]), max(q[1], q[3])), pdfUnescape(u.group(1)).decode('latin1')))
                extractedElements = [{'type': 'pageStart', 'box': box, 'links': links, 'rules': rules}]
                for name, m in placedImages:
                    data = imageBytes(xobjects[name]) if name in xobjects else None
                    if data and abs(m[0]) > 5 and abs(m[3]) > 5:
                        extractedElements.append({'type': 'image', 'data': data, 'x': m[4], 'y': max(m[5], m[5] + m[3]), 'w': abs(m[0])})

                for block, ctm, col in textBlocks:
                    blockElements = [(-1, {'type': 'blockStart', 'ctm': ctm, 'color': col})]

                    #Font details               
                    TfPattern = re.compile(rb'/([^\s/<>\[\]()]+)\s+(-?(?:\d+\.?\d*|\.\d+))\s+Tf')
                    for match in TfPattern.finditer(block):
                        fontName, fontSize = match.groups()
                        blockElements.append((match.start(), {'type': 'font', 'name': fontName.decode('latin1'), 'size': float(fontSize), 'base': fontInfo.get(fontName.decode('latin1'))}))
    
                    #Text matrix (Tm) #(a, b, c, d, e, f)Tm . e f are the x and y cords
                    TmPattern = re.compile(rb'([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+Tm', re.DOTALL)
                    for match in TmPattern.finditer(block):
                        a, b, c, d, e, f = match.groups()
                        blockElements.append((match.start(), {'type': 'matrix', 'a': float(a), 'b': float(b), 'c': float(c), 'd': float(d), 'x': float(e), 'y': float(f)}))

                    #Text rise (Ts)
                    TsPattern = re.compile(rb'(-?(?:\d+\.?\d*|\.\d+))\s+Ts')
                    for match in TsPattern.finditer(block):
                        blockElements.append((match.start(), {'type': "rise", 'value': float(match.group(1))}))

                    #Text leading (TL)
                    TLPattern = re.compile(rb'(-?(?:\d+\.?\d*|\.\d+))\s+TL')
                    for match in TLPattern.finditer(block):
                        blockElements.append((match.start(), {'type': 'leading', 'value': float(match.group(1))}))

                    #Text rendering mode (Tr) #0 for normal text, 3 for invisible text 
                    TrPattern = re.compile(rb'(\d+)\s+Tr')
                    for match in TrPattern.finditer(block):
                        blockElements.append((match.start(), {'type': 'renderingMode', 'mode': float(match.group(1))}))              

                    blockElements += [(m.start(), {'type': 'charSpace', 'value': float(m.group(1))}) for m in re.finditer(rb'(-?[\d.]+)\s+Tc\b', block)]
                    blockElements += [(m.start(), {'type': 'color', 'rgb': toRGB(m.group(1), m.group(2))}) for m in re.finditer(rb'((?:-?[\d.]+\s+){0,3}-?[\d.]+)\s+(rg|g|k)\b', block)]
                    #Text positions
                    TDPattern = re.compile(rb'(-?(?:\d+\.?\d*|\.\d+))\s+(-?(?:\d+\.?\d*|\.\d+))\s+(Td|TD)')
                    for match in TDPattern.finditer(block):
                        xOffset, yOffset, operator = match.groups()
                        blockElements.append((match.start(), {'type': 'position', 'dx': float(xOffset), 'dy': float(yOffset), 'operator': operator.decode('latin1')}))              

                    #Next line (Also known as T*)
                    TStarPattern = re.compile(rb'(?<![A-Za-z])T\*')
                    for match in TStarPattern.finditer(block):
                        blockElements.append((match.start(), {'type': 'newline'}))

                    #Text (single text string). Literal strings are unescaped and stored as hex so they pass through the font's ToUnicode map
                    TjPattern = re.compile(rb'(?:\(((?:\\.|[^\\()])*)\)|<([0-9A-Fa-f\s]+)>)\s*(Tj|\'|")', re.DOTALL)
                    for match in TjPattern.finditer(block):
                        literalString, HexString, operator = match.groups()

                        if operator in (b"'", b'"'):
                            blockElements.append((match.start(), {'type': 'newline'}))

                        if literalString is not None:
                            blockElements.append((match.start(), {'type': 'textHex', 'content': pdfUnescape(literalString).hex().upper().encode('ascii')}))
                        elif HexString:
                            blockElements.append((match.start(), {'type': 'textHex', 'content': HexString}))

                    #text with arrays containing strings and numbers (Also known as TJ)
                    TJPattern = re.compile(rb'\[(.*?)\]\s*TJ', re.DOTALL)
                    for match in TJPattern.finditer(block):
                        TJs = match.group(1)

                        arrayItems = re.findall(rb'\(((?:\\.|[^\\()])*)\)|<([0-9A-Fa-f\s]+)>|(-?\d+\.?\d*)', TJs, re.DOTALL)
                        for literal, hexItem, number in arrayItems:
                            if literal:    #literal text strings
                                blockElements.append((match.start(), {'type': 'textHex', 'content': pdfUnescape(literal).hex().upper().encode('ascii')}))

                            elif hexItem:  #hex strings
                                blockElements.append((match.start(), {'type': 'textHex', 'content': hexItem}))

                            elif number:   #big negative adjustment = a word gap
                                if float(number) < -200:
                                    blockElements.append((match.start(), {'type': 'text', 'content': ' '}))

                    #Translating all hexes into string using the fontsCMap
                    translatedBlockElements = []
                    currentFont = 'F1' #Default font

                    for position, element in blockElements:
                        if element['type'] == 'font':
                            currentFont = element['name']  
                            translatedBlockElements.append((position, element))
                        
                        elif element['type'] == 'textHex':
                            if currentFont in undecodable:
                                continue
                            rawHex = element['content'].decode('latin1', errors='ignore')
                            cleanHex = re.sub(r'\s+', '', rawHex).upper()

                            activeCMap = fontscMap.get(currentFont, {})
                            step = len(next(iter(activeCMap))) if activeCMap else 2   #hex digits per character code
                            if len(cleanHex) % step:
                                step = 2
                            decodedChars, fw, width = "", fontWidths.get(currentFont), 0.0

                            for i in range(0, len(cleanHex), step):
                                chunk = cleanHex[i: i + step]
                                if fw and 0 <= int(chunk, 16) - fw[0] < len(fw[1]): width += fw[1][int(chunk, 16) - fw[0]] / 1000
                                if chunk in activeCMap:
                                    decodedChars += SYMS.get((fontInfo.get(currentFont), chunk), activeCMap[chunk])
                                else:
                                    try:
                                        decodedChars += bytes.fromhex(chunk).decode('cp1252', errors='ignore')   #cp1252 so WinAnsi bullets/quotes/dashes come out right
                                    except:
                                        pass

                            translatedBlockElements.append((position, {'type': 'text', 'content': decodedChars, 'w': width}))

                        else:
                            translatedBlockElements.append((position, element))          

                    translatedBlockElements.sort(key=lambda x: x[0])#sorts everything in the block by the character position

                    for position, element in translatedBlockElements:  
                        extractedElements.append(element) #appending each of the blocks elements in the right order

                allElements.extend(extractedElements)
            
            elif subkidsIndex != -1:
                pageParser(pageID)
            else: allElements.append({'type': 'pageStart', 'box': None})

    if pagesObjectID:
        pageParser(pagesObjectID)
    PDF.close()
    return allElements, None
