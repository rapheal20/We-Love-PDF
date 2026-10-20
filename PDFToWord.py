#This function converts a PDF file to a .docs 
#Coded by Anael

import os 
import re 
import zlib
from helperfunctions import *
from docx import Document 
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image

def PDFToWord(PDFPath):
    PDF = open(PDFPath, "rb")

    PDFSize = os.path.getsize(PDFPath)

    PDFVersion = PDFVersionFunc(PDFPath)

    XrefTable, XrefTableAddress = XrefTableFunc(PDFPath)

    RootObjectID = RootObjectIDFunc(PDFPath)

    RootObjectLocation = XrefTable[RootObjectID]

    PDF.seek(RootObjectLocation)
    buffer = PDF.read()

    CatalogObjectID = RootObjectID

    catalogObjectLocation = XrefTable[CatalogObjectID]

    PDF.seek(catalogObjectLocation)
    buffer = PDF.read(1024)

    pagesRefMatch = re.search(rb'/Pages\s+(\d+)\s+(\d+)\s+R', buffer)

    if pagesRefMatch:
        pagesObjectID = int(pagesRefMatch.group(1))
        pagesObjectLocation = XrefTable[pagesObjectID]

        PDF.seek(pagesObjectLocation)
        pagesBuffer = PDF.read(1024)

        countMatch = re.search(rb'/Count\s+(\d+)', pagesBuffer)
        
        if countMatch:
            numberOfPages = int(countMatch.group(1))
        else:
            numberOfPages = 0
    else:
        numberOfPages = 0

    def imageDictFinder(XObjectOffset):
        images = [] 

        PDF.seek(XObjectOffset)
        imgBuffer = PDF.read()
        imagePattern = rb"(\d+\s+\d+\s+obj\s*<<.*?(?:/Subtype\s*/Image).*?>>\s*stream\r?\n)(.*?)(?:\r?\nendstream)"
        imageBytesArray = re.findall(imagePattern, imgBuffer, re.DOTALL)

        for index, array in enumerate(imageBytesArray):
            imageHeader = array[0]
            imageBytes = array[1]

            imageID = re.search(rb"\d+", imageHeader).group().decode()

            imageWidth = re.search(rb"/Width\s+(\d+) ", imageHeader).group(1).decode()
            imageHeight = re.search(rb"/Height\s+(\d+)", imageHeader).group(1).decode()

            imageFilter =  re.search(rb"/Filter\s*/([A-Za-z0-9]+)", imageHeader).group(1).decode()

            imageDict = {"imageID": imageID, "imageWidth": imageWidth, "imageHeight": imageHeight, "imageBytes": imageBytes}
            images.append(imageDict)

            return images

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
                parts = [p.strip("<>") for p in line.split() if p.startswith("<")]
                if len(parts) >= 2:
                    srcHex, dstHex = parts[0].upper(), parts[1]
                    # Convert hex sequence to string
                    try:
                        charCode = "".join(chr(int(dstHex[j : j + 4], 16)) for j in range(0, len(dstHex), 4))
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
            for line in block.splitlines():
                parts = line.split()
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
                                array_start = line.find("[")
                                array_end = line.find("]")
                                arrTokens = [
                                    t.strip("<>")
                                    for t in line[array_start + 1 : array_end].split()
                                ]
                                for idx, codeVal in enumerate(range(startVal, endVal + 1)):
                                    if idx < len(arrTokens):
                                        srcKey = f"{codeVal:0{hexLen}X}"
                                        dstHex = arrTokens[idx]
                                        cmap[srcKey] = chr(int(dstHex, 16))
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
        if objectID not in XrefTable:
            return b""
        PDF.seek(XrefTable[objectID])

        # read until we actually reach 'endstream' (no fixed 8192 cap)
        data = b""
        while b"endstream" not in data:
            more = PDF.read(65536)
            if not more:
                break
            data += more

        m = re.search(rb"stream\r?\n", data)
        if not m:
            return b""
        header = data[:m.start()]
        end = data.find(b"endstream", m.end())
        raw = data[m.end():end if end != -1 else len(data)]
        if raw.endswith(b"\r\n"):
            raw = raw[:-2]
        elif raw.endswith(b"\n") or raw.endswith(b"\r"):
            raw = raw[:-1]

        if b"/FlateDecode" in header:
            try:
                return zlib.decompressobj().decompress(raw)   # tolerates trailing junk
            except zlib.error:
                try:
                    return zlib.decompressobj(-zlib.MAX_WBITS).decompress(raw)
                except zlib.error:
                    return raw
        return raw

    def readObject(objID):
        #Return the raw bytes of exactly one object (up to its endobj).
        if objID not in XrefTable:
            return b""
        PDF.seek(XrefTable[objID])
        data = b""
        while b"endobj" not in data:
            more = PDF.read(4096)
            if not more:
                break
            data += more
        return data.split(b"endobj")[0]

    fontInfo = {}   #font resource name -> BaseFont, refilled for every page by fontDictFinder

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

            tu = re.search(rb"/ToUnicode\s+(\d+)\s+\d+\s+R", fontBuf)
            if tu:
                fontcMaps[name] = parseCmap(readandDecompressStream(int(tu.group(1))))
        return fontcMaps

    allElements = []

    def pageParser(currentLocation):
        pagesIDGenList = []

        PDF.seek(currentLocation)
        buffer = PDF.read(2048)
        
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

            pageLocation = XrefTable[pageID]
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
                resourceIndex = buffer.find(b"/Resources")
                resBuffer = buffer
                fontInfo.clear()

                if resourceIndex != -1: 
                    resourceLine = buffer[resourceIndex:].split(b"\n")[0]
                    resourceList = resourceLine.split() #This will get us the list of stuff around /resources. There the object id of resources would be written in the next index. We will use the Xreftabelo and object id to get the location of resources 

                    resourceObject = None
                    resourceObjectID = None
                    
                    for idx, token in enumerate(resourceList):
                            if token == b"/Resources" and idx + 1 < len(resourceList):
                                if resourceList[idx + 1].isdigit():
                                    resourceObjectID = int(resourceList[idx + 1].decode("latin1"))
                                    break

                    resBuffer = buffer
                    if resourceObjectID and resourceObjectID in XrefTable:
                            resBuffer = readObject(resourceObjectID)     #PDF.read(4096)

                #Images processing
                XObjectPattern = rb"/XObject<<\s*/([^ ]+)\s+(\d+\s+\d+\s+R)"
                XObject = re.search(XObjectPattern, resBuffer)
                XObjectName = XObject.group(1)
                XObjectAddress = int(XObject.group(2).split()[0])
                XObjectOffset = XrefTable[XObjectAddress]

                imageDict = imageDictFinder(XObjectOffset)

                #with open("Outputs/image.jpg", "wb") as img:
                #    img.write(imageDict["imageBytes"])

                fontscMap = fontDictFinder(resBuffer) #This maps each font F1 F2 F5 etc to a dict with each value(but in hexadecimal). but I will do that at the end of the code.
                
                cMap = {}

                toUnicodeIndex = resBuffer.find(b"/ToUnicode")

                if toUnicodeIndex != -1:
                    toUnicodesnippet = resBuffer[toUnicodeIndex : toUnicodeIndex + 100].split()
                    toUnicodeObjectID = None
                    for idx, token in enumerate(toUnicodesnippet):
                        if token == b"/ToUnicode" and idx + 1 < len(toUnicodesnippet):
                            if toUnicodesnippet[idx + 1].isdigit():
                                toUnicodeID = int(toUnicodesnippet[idx + 1].decode("latin1"))
                                cmapBytes = readandDecompressStream(toUnicodeID)
                                cMap = parseCmap(cmapBytes)
                                break 
                else:
                    encodingIndex = resBuffer.find(b"/Encoding")
                    if encodingIndex != -1:
                        encSnippet = resBuffer[encodingIndex: encodingIndex + 200]
                        diffIndex = encSnippet.find(b"/Differences")
                        if diffIndex != -1:
                            diffStart = encSnippet.find(b"[", diffIndex)
                            diffEnd = encSnippet.find(b"]", diffStart)
                            if diffStart != -1 and diffEnd != -1:
                                tokens = encSnippet[diffStart + 1:diffEnd].split()
                                currCode = 0
                                for token in tokens:
                                    tStr = token.decode("latin1", errors="ignore")
                                    if tStr.isdigit():
                                        currCode = int(tStr)
                                    elif tStr.startswith("/"):
                                        glyphName = tStr[1:]
                                        srckey = f"{currCode:02X}" #formats as 2 digit hexadecimal key
                                        if glyphName == "space":
                                            cMap[srckey] = " "
                                        elif glyphName == "space":
                                            cMap[srckey] = " "
                                        currCode += 1

                #Work out the cm transform active at each BT block so positions are comparable across blocks
                ctmOps = re.compile(rb'(?<![A-Za-z0-9*])(q|Q)(?![A-Za-z0-9*])|((?:-?[\d.]+\s+){5}-?[\d.]+)\s+cm\b')
                opsList = list(ctmOps.finditer(decompressedStreamData))
                ctmStack, ctmNow, opIdx = [], (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 0
                textBlocks = []
                for bm in textBlockPattern.finditer(decompressedStreamData):
                    while opIdx < len(opsList) and opsList[opIdx].start() < bm.start():
                        om = opsList[opIdx]
                        if om.group(1) == b'q':
                            ctmStack.append(ctmNow)
                        elif om.group(1) == b'Q':
                            if ctmStack:
                                ctmNow = ctmStack.pop()
                        else:
                            a, b, c, d, e, f = [float(v) for v in om.group(2).split()]
                            a0, b0, c0, d0, e0, f0 = ctmNow
                            ctmNow = (a*a0 + b*c0, a*b0 + b*d0, c*a0 + d*c0, c*b0 + d*d0, e*a0 + f*c0 + e0, e*b0 + f*d0 + f0)
                        opIdx += 1
                    textBlocks.append((bm.group(1), ctmNow))
                extractedElements = [{'type': 'pageStart'}]

                for block, ctm in textBlocks:
                    blockElements = [(-1, {'type': 'blockStart', 'ctm': ctm})]

                    #Font details               
                    TfPattern = re.compile(rb'/([A-Za-z0-9\._\-]+)\s+(\d+\.?\d*)\s+Tf')
                    for match in TfPattern.finditer(block):
                        fontName, fontSize = match.groups()
                        blockElements.append((match.start(), {'type': 'font', 'name': fontName.decode('latin1'), 'size': float(fontSize), 'base': fontInfo.get(fontName.decode('latin1'))}))
 
                    #Text matrix (Tm) #(a, b, c, d, e, f)Tm . e f are the x and y cords
                    TmPattern = re.compile(rb'([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+Tm', re.DOTALL)
                    for match in TmPattern.finditer(block):
                        a, b, c, d, e, f = match.groups()
                        blockElements.append((match.start(), {'type': 'matrix', 'a': float(a), 'b': float(b), 'c': float(c), 'd': float(d), 'x': float(e), 'y': float(f)}))

                    #Text rise (Ts)
                    TsPattern = re.compile(rb'(-?\d+\.?\d*)\s+Ts')
                    for match in TsPattern.finditer(block):
                        blockElements.append((match.start(), {'type': "rise", 'value': float(match.group(1))}))

                    #Text leading (TL)
                    TLPattern = re.compile(rb'(-?\d+\.?\d*)\s+TL')
                    for match in TLPattern.finditer(block):
                        blockElements.append((match.start(), {'type': 'leading', 'value': float(match.group(1))}))

                    #Text rendering mode (Tr) #0 for normal text, 3 for invisible text 
                    TrPattern = re.compile(rb'(\d+)\s+Tr')
                    for match in TrPattern.finditer(block):
                        blockElements.append((match.start(), {'type': 'renderingMode', 'mode': float(match.group(1))}))              

                    #Text positions
                    TDPattern = re.compile(rb'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(Td|TD)')
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
                            rawHex = element['content'].decode('latin1', errors='ignore')
                            cleanHex = re.sub(r'\s+', '', rawHex).upper()

                            activeCMap = fontscMap.get(currentFont, {})
                            step = len(next(iter(activeCMap))) if activeCMap else 2   #hex digits per character code
                            if len(cleanHex) % step:
                                step = 2
                            decodedChars = ""

                            for i in range(0, len(cleanHex), step):
                                chunk = cleanHex[i: i + step]
                                if chunk in activeCMap:
                                    decodedChars += activeCMap[chunk]
                                else:
                                    try:
                                        decodedChars += bytes.fromhex(chunk).decode('cp1252', errors='ignore')   #cp1252 so WinAnsi bullets/quotes/dashes come out right
                                    except:
                                        pass

                            translatedBlockElements.append((position, {'type': 'text', 'content': decodedChars}))

                        else:
                            translatedBlockElements.append((position, element))          

                    translatedBlockElements.sort(key=lambda x: x[0])#sorts everything in the block by the character position

                    for position, element in translatedBlockElements:  
                        extractedElements.append(element) #appending each of the blocks elements in the right order

                #print(extractedElements) #This is all the elements like text in the file with their positions and stuff. 
                #print(fontscMap)

                allElements.extend(extractedElements)
            
            elif subkidsIndex != -1:
                pageParser(pageLocation)

    pageParser(pagesObjectLocation)
    extractedElements = allElements

    #Turns a PDF BaseFont like "ABCDEF+DejaVuSans-Bold" into (Word font name, bold, italic)
    def fontStyle(base):
        if not base:
            return "Calibri", False, False
        base = re.sub(r"^[A-Z]{6}\+", "", base)
        low = base.lower()
        bold = any(k in low for k in ("bold", "black", "heavy"))
        italic = "italic" in low or "oblique" in low
        family = re.split(r"[-,]", base)[0]
        fl = family.lower()
        if any(k in fl for k in ("helvetica", "arial", "liberationsans")):
            family = "Arial"
        elif any(k in fl for k in ("times", "liberationserif")):
            family = "Times New Roman"
        elif any(k in fl for k in ("courier", "liberationmono")):
            family = "Courier New"
        else:
            family = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", family)   # DejaVuSans -> DejaVu Sans
        return family, bold, italic

    #replay the PDF text operators so every piece of text knows its x, y, size and style
    spans = []
    x = y = 0.0
    scale = 1.0          #font scale coming from the text matrix (many PDFs use "1 Tf" + a scaled Tm)
    leading = 0.0
    size = 11.0
    base = None
    moved = False
    ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    currentPageSpans = []

    def flushPage():
        if not currentPageSpans:
            return
        spans.append({'page': True})
        currentPageSpans.sort(key=lambda s: (-s['y'], s['x']))
        spans.extend(currentPageSpans)
        currentPageSpans.clear()

    for element in extractedElements:

        t = element.get('type')

        if t == 'pageStart':
            flushPage()

        elif t == 'blockStart':
            ctm = element.get('ctm', ctm)
            x = y = 0.0
            scale = 1.0
            moved = True

        elif t == 'font':
            size = element.get('size', 11)
            base = element.get('base')

        elif t == 'matrix':
            scale = abs(element['d']) if element['d'] else 1.0
            x, y = element['x'], element['y']
            moved = True

        elif t == 'position':
            x += element['dx'] * scale
            y += element['dy'] * scale
            if element['operator'] == 'TD':
                leading = -element['dy']
            moved = True

        elif t == 'leading':
            leading = element['value']

        elif t == 'newline':
            y -= leading * scale
            moved = True

        elif t == 'text':
            txt = element.get('content', '')
            txt = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', txt)

            if txt == '':
                continue

            # Filter out exam footers, page numbers, and copyright stamps
            if re.match(r'^\d{1,2}$', txt.strip()):
                continue

            family, bold, italic = fontStyle(base)
            effSize = round(size * scale * abs(ctm[3]), 1)
            if effSize < 4:
                effSize = 11

            absX = ctm[0] * x + ctm[4]
            absY = ctm[3] * y + ctm[5]

            if absX < 45 or absX > 550:
                continue
            
            currentPageSpans.append({'text': txt, 'x': ctm[0] * x + ctm[4], 'y': ctm[3] * y + ctm[5], 'size': effSize, 'font': family,
                          'bold': bold, 'italic': italic, 'moved': moved,
                          'symbol': bool(base and re.search(r'dingbat|symbol', base, re.I))})
            moved = False

    flushPage()

    BULLETS = {'\u2022', '\u25aa', '\u25cf', '\u25e6', '\u2023', '\uf0b7'}
    leftMargin = min([s['x'] for s in spans if 'text' in s and s['text'].strip()], default=0)

    doc = Document()
    para = None
    lastY = lastSize = None
    seenPage = False

    for s in spans:
        if s.get('page'):
            if seenPage:
                doc.add_page_break()
            seenPage = True
            para = None
            continue

        text = s['text']
        stripped = text.strip()

        #A bullet glyph on its own starts a list item (only real bullet characters, never letters like "o")
        if stripped in BULLETS or (len(stripped) == 1 and s['symbol'] and not stripped.isprintable()):
            para = doc.add_paragraph(style='List Bullet')
            lastY, lastSize = s['y'], s['size']
            continue

        #Whitespace-only pieces are just gaps: add one space unless the text already ends with one
        if not stripped:
            if para is not None and para.runs and not para.runs[-1].text.endswith(' '):
                para.add_run(' ')
            continue

        newPara = False
        if para is None:
            newPara = True
        else:
            gap = abs(s['y'] - lastY)
            if gap < 0.5 * s['size']:
                pass                                   #same line
            elif abs(s['size'] - lastSize) > 1 or gap > 1.7 * s['size']:
                newPara = True                         #heading/size change or a paragraph-sized gap

        if newPara:
            para = doc.add_paragraph()
            if s['x'] - leftMargin > 80:               #starts far from the left margin: centered text
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif s['moved'] and para.runs and not para.runs[-1].text.endswith(' ') and not text.startswith(' '):
            para.add_run(' ')                          #wrapped line or a gap on the same line

        run = para.add_run(text)
        run.font.name = s['font']
        run.font.size = Pt(s['size'])
        if s['bold']:
            run.bold = True
        if s['italic']:
            run.italic = True

        lastY, lastSize = s['y'], s['size']

    os.makedirs("Outputs", exist_ok=True)
    outputPath = "Outputs/converted_document.docx"
    doc.save(outputPath)
    print("done")

PDFToWord("Inputs/emaar1.pdf")