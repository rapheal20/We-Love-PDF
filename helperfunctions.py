import os
import re
import zlib
import mmap

'''CONSTANTS'''

# OBJECT FIND STRING DETAILS
# the paranthesis divide it into groups so tha twe can later access the id directly
# with () we can use the .group command on it 
# .group(0) gives the whole match 
# .group(1) gives the first bracket 
# .group(2) gives the second bracket
# + sign here signifies or more digits so this allows for multiple digit ids
# .start() gives the byte offset which can also be taken from span[0]

#for finding objects
objectFindString = r"\b(\d+)\s+(\d+)\s+obj\b" 
objectEndString = r"\bendobj"

# for finding refernces
refFindString = r"\s*(\d+)\s+(\d+)\s+R" 

#for finding trailer
trailerFindString = r"/\s*Root\s+(\d+)\s+(\d+)\s+R" #\s* represents no or more spaces

#for finding catalog
catalogFindString = r"\s*/\s*Type\s*/\s*Catalog\s*"

#for finding images objects
imgFindStr = r"\s*/\s*Subtype\s*/\s*Image\s*"
'''END OF CONSTANTS'''




#Returns PDF version
def PDFVersionFunc(PDFPath):
    PDF = open(PDFPath, "rb")
    buffer = PDF.readline()
    PDFVersion = float(re.search(rb'%PDF-(\d\.\d)', buffer).group(1).decode('latin1'))
    PDF.close()

    return PDFVersion

def parseASCIIXref(PDFcontent: bytes, offset: int, xrefTable: dict):
    end = PDFcontent.find(b"trailer", offset)       #only this section, not the whole rest of the file
    lines = re.split(rb"\r\n|\r|\n", PDFcontent[offset:end + 7 if end != -1 else len(PDFcontent)])

    index = 1
    while index < len(lines):
        line = lines[index].strip()
        if not line or line.startswith(b"trailer") or line.startswith(b"startxref"):
            break

        parts = line.split()
        if len(parts) == 2:
            startID = int(parts[0])
            totalCount = int(parts[1])
            index += 1

            for i in range(totalCount):
                if index >= len(lines): 
                    break

                entry = lines[index].strip().split()

                if len(entry) >= 3:
                    objectID = startID + i
                    # xrefTable[objectID] = int(entry[0])
                    xrefTable[objectID] = {
                        "offset": int(entry[0]),
                        "generation": int(entry[1]),
                        "type": entry[2].decode('latin1')
                    }

                index += 1
            continue
        index += 1

#I don't really wanna know how this runs so I have copied from Gemini. 
def removePNGPredictor(data: bytes, columns: int, row_width: int, bpp: int = 1): 
    stride = columns + 1
    out = bytearray()
    prev_row = bytearray(columns)
    
    for r in range(0, len(data), stride):
        row = data[r:r+stride]
        if len(row) < stride: break
        filter_type = row[0]
        curr_filtered = row[1:]
        recon_row = bytearray(columns)
        
        for c in range(columns):
            raw_byte = curr_filtered[c]
            up = prev_row[c]
            left = recon_row[c-bpp] if c >= bpp else 0
            left_up = prev_row[c-bpp] if c >= bpp else 0
            
            if filter_type == 0:   recon = raw_byte # None
            elif filter_type == 1: recon = (raw_byte + left) & 0xFF # Sub
            elif filter_type == 2: recon = (raw_byte + up) & 0xFF # Up
            elif filter_type == 3: recon = (raw_byte + ((left + up) // 2)) & 0xFF # Average
            elif filter_type == 4: # Paeth
                p = left + up - left_up
                pa = abs(p - left)
                pb = abs(p - up)
                pc = abs(p - left_up)
                nearest = left if (pa <= pb and pa <= pc) else (up if pb <= pc else left_up)
                recon = (raw_byte + nearest) & 0xFF
            else: recon = raw_byte
            
            recon_row[c] = recon
        out.extend(recon_row)
        prev_row = recon_row
    return bytes(out)

def parseXrefStream(PDFcontent: bytes, offset: int, xrefTable: dict):
    objectData = PDFcontent[offset:offset + 5000]

    #the xref properties
    sizeM = re.search(rb"\/Size\s+(\d+)", objectData)
    wM = re.search(rb"\/W\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s*\]", objectData)
    predM = re.search(rb"\/Predictor\s+(\d+)", objectData)
    colsM = re.search(rb"\/Columns\s+(\d+)", objectData)
    indexM = re.search(rb"\/Index\s*\[\s*([0-9\s]+)\s*\]", objectData)

    if not sizeM or not wM:
        return 

    totalSize = int(sizeM.group(1))
    w = [int(wM.group(1)), int(wM.group(2)), int(wM.group(3))]
    rowWidth = sum(w)

    #Object IDs scope 
    subsections = [(0, totalSize)]
    if indexM: 
        rawIndex = indexM.group(1).split()
        subsections = [(int(rawIndex[i]), int(rawIndex[i+1])) for i in range(0, len(rawIndex), 2)]

    streamStart = PDFcontent.find(b"stream", offset)
    if streamStart == -1:
        return

    #This is to check if the stream has \r\n or only \n or neither.
    if PDFcontent[streamStart + 6: streamStart + 8] == b"\r\n":
        streamStart += 8
    elif PDFcontent[streamStart + 6: streamStart + 7] == b"\n":
        streamStart += 7
    else:
        streamStart += 6

    streamEnd = PDFcontent.find(b"endstream", streamStart)
    rawStream = PDFcontent[streamStart:streamEnd]

    try:
        decompressed = zlib.decompress(rawStream)
    except:
        return

    #Reverse PNG predictor filter
    # PNG predictor filter is a type of compression for images which makes the pixels more competitive.
    #so I need to remove it, it it was placed

    predictor = int(predM.group(1)) if predM else 1
    columns = int(colsM.group(1)) if colsM else rowWidth

    if predictor >= 10:
        decompressed = removePNGPredictor(decompressed, columns, rowWidth)

    byteIndex = 0
    for startID, count in subsections:
        for i in range(count):
            if byteIndex + rowWidth > len(decompressed):
                break
            row = decompressed[byteIndex: byteIndex + rowWidth]
            byteIndex += rowWidth

            f1 = int.from_bytes(row[:w[0]], "big") if w[0] > 0 else 1 # Default type to in-use
            f2 = int.from_bytes(row[w[0]:w[0]+w[1]], "big")
            f3 = int.from_bytes(row[w[0]+w[1]:], "big") if w[2] > 0 else 0

            objectID = startID + i
            if f1 == 0: 
                typeStr = "f"
            elif f1 == 1: 
                typeStr = "n"
            elif f1 == 2:
                typeStr = "compressedInsideStream"

            # xrefTable[objectID] = f2

            xrefTable[objectID] = {
                "offset": f2,
                "generation": f3,
                "type": typeStr
            }

#Returns XrefTable of the PDF
def XrefTableFunc(PDFPath):
    xrefTable = {}
    xrefAddresses = []

    with open(PDFPath, "rb") as PDF:
        PDFcontent = PDF.read()

    startXrefMatches = list(re.finditer(rb"startxref\s+(\d+)", PDFcontent))

    xrefStreamMatches = list(re.finditer(rb"(\d+)\s+(\d+)\s+obj\s*<<(?:(?!endobj)[\s\S]){0,600}?\/Type\s*\/XRef", PDFcontent)) 

    #Reads one xref section (old table or stream) and adds ONLY the objects not already known, so the newest section wins.
    #Returns the offsets of the sections it points to with /Prev (older section) and /XRefStm (hybrid files)
    def addSection(offset):
        section = {}
        if PDFcontent[offset: offset + 20].strip().startswith(b"xref"): #Older version
            parseASCIIXref(PDFcontent, offset, section)
            trailerStart = PDFcontent.find(b"trailer", offset)
            dictBytes = PDFcontent[trailerStart: trailerStart + 2000].split(b"startxref")[0] if trailerStart != -1 else b""
        else:
            parseXrefStream(PDFcontent, offset, section)
            dictBytes = PDFcontent[offset: offset + 5000].split(b"stream")[0]
        for objectID, entry in section.items():
            xrefTable.setdefault(objectID, entry)
        return [int(x) for x in re.findall(rb"/(?:XRefStm|Prev)\s+(\d+)", dictBytes)]

    #First method: the startxref pointers, newest first, and every /Prev after them (linearized and updated files have several sections)
    pending = [int(match.group(1)) for match in reversed(startXrefMatches)]
    seen = set()
    while pending:
        offset = pending.pop(0)
        if offset in seen or offset <= 0 or offset >= len(PDFcontent): #0 means the header so skip it 
            continue
        seen.add(offset)
        xrefAddresses.append(offset)
        try:
            pending[0:0] = addSection(offset)
        except Exception:
            continue
    
    #Second method: hybrid streams
    for match in xrefStreamMatches:
        if match.start() not in seen:
            xrefAddresses.append(match.start())
            try:
                addSection(match.start())
            except Exception:
                pass

    #this is another backup where if the xref table offset is wrong so I will find the xref table directly as work
    if not xrefTable:
        for backupOffset in re.finditer(rb"\bxref\b", PDFcontent):
            xrefAddresses.append(backupOffset.start())
            parseASCIIXref(PDFcontent, backupOffset.start(), xrefTable)
            if xrefTable:
                break

    #repair: adds objects the xref missed and fixes offsets which do not point to their object
    added = set()
    for found in re.finditer(rb"(?:^|[\r\n])[ \t]*(\d+)\s+\d+\s+obj\b", PDFcontent):
        objectID, position = int(found.group(1)), found.start(1)
        entry = xrefTable.get(objectID)
        if entry is None or objectID in added: #later copy of a missing object = newest one
            xrefTable[objectID] = {"offset": position, "generation": 0, "type": "n"}
            added.add(objectID)
        elif entry["type"] == "n" and entry["offset"] > 0:
            atOffset = re.match(rb"\s*(\d+)\s+\d+\s+obj\b", PDFcontent[entry["offset"]: entry["offset"] + 30])
            if atOffset is None or int(atOffset.group(1)) != objectID:
                entry["offset"] = position

    return xrefTable, xrefAddresses

#Returns the RootObjectID of the PDF
def RootObjectIDFunc(PDFPath):
    with open(PDFPath, "rb") as PDF:
        content = PDF.read()

    #The last /Root in the file belongs to the newest version of the file
    allRoots = re.findall(rb'/Root\s+(\d+)\s+\d+\s+R', content)

    if allRoots:
        return int(allRoots[-1])

    return None

#Finds where one object ends (its endobj) in the bytes read so far, or None if more bytes are needed.
#Streams are skipped using /Length so binary data that happens to contain "endobj" can't cut the object short
#some PDFs have no endobj: an object also ends at the next object header or at xref/trailer
endObjFindString = re.compile(rb"\d+\s+\d+\s+obj\b|[\r\n](?:xref|trailer|startxref)\b")
streamFindString = re.compile(rb"[>\s]stream(?:\r\n|\n|\r)")
lengthFindString = re.compile(rb"/Length\s+(\d+)(?!\d|\s+\d+\s+R)")

#Returns the bytes of the ONE object that starts at pos (without its endobj). data can be bytes or a memory mapped file.
#Streams are skipped using /Length so binary data that happens to contain "endobj" can't cut the object short
def cutObject(data, pos=0):
    nextObj = endObjFindString.search(data, data.find(b"obj", pos) + 3)
    endObj = data.find(b"endobj", pos, nextObj.start() if nextObj else len(data))
    limit = endObj if endObj != -1 else (nextObj.start() if nextObj else len(data))

    streamStart = streamFindString.search(data, pos, limit)
    if streamStart:
        endStream = -1
        lengthMatch = lengthFindString.search(data, pos, streamStart.start())
        if lengthMatch:
            skip = streamStart.end() + int(lengthMatch.group(1))
            if data[skip:skip + 12].lstrip().startswith(b"endstream"):
                endStream = skip
        if endStream == -1:
            endStream = data.find(b"endstream", streamStart.end())
        if endStream == -1:
            return data[pos:limit]
        nextObj = endObjFindString.search(data, endStream)
        endObj = data.find(b"endobj", endStream, nextObj.start() if nextObj else len(data))
        limit = endObj if endObj != -1 else (nextObj.start() if nextObj else len(data))
    return data[pos:limit]

#Returns the bytes of an object as "ID 0 obj ... endobj", for normal AND compressed objects
def GetObjectBytes(PDF, XrefTable, objectID, objStmCache):
    entry = XrefTable.get(objectID)

    if not entry or entry.get('type') == "f":
        return b""

    if entry.get('type') == "compressedInsideStream":
        #for these, 'offset' is NOT a file position. It is the ID of the object stream that holds it
        body = ReadObjectStream(PDF, XrefTable, entry['offset'], objStmCache).get(objectID, b"")
        return f"{objectID} 0 obj\n".encode('latin1') + body + b"\nendobj\n"

    #the file is memory mapped once (kept in the cache), so no object is ever copied around while searching for its end
    if "mm" not in objStmCache:
        objStmCache["mm"] = mmap.mmap(PDF.fileno(), 0, access=mmap.ACCESS_READ)
    return cutObject(objStmCache["mm"], entry['offset'])

#Opens one object stream and returns {objectID: bytes of that object}
def ReadObjectStream(PDF, XrefTable, streamID, objStmCache):
    if streamID in objStmCache:
        return objStmCache[streamID]

    streamObject = GetObjectBytes(PDF, XrefTable, streamID, objStmCache)

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

# Makes new header object
# input is the decoded string of the PDF
# returns the final header as a string, can be added to pdf directly
def Make_Header(pdfString):
    # this function takes a pdf decoded in latin1
    HeaderStr = r"%PDF-(\d+\.\d+)" 
    headermatch = re.search(HeaderStr, pdfString)
    version = headermatch.group(0)
    #these series of characters are added to tell that the pdf to read character like \n for new line
    PDFheader = version + "\n%âãÏÓ\n"
    return PDFheader

# makes the xref table with formatting as a string
# takes the object find string and the final pdf string
# returns the final xref table, can be directly added to the PDF string

def Make_Xref(objectFindString, FinalPDFStr):

    #makes a dictionary with object id as key and offset as value
    xrefDict = {}
    xrefTableMatch = re.finditer(objectFindString, FinalPDFStr, flags=re.IGNORECASE)
    for match in xrefTableMatch:
        xrefDict[int(match.group(1))] = match.start()

    #finds the number of objects in the combines pdf
    numberOfObj = max(xrefDict.keys())
    #adds a free object at start
    xrefStr = f"\n\nxref\n0 {numberOfObj+1}\n0000000000 65535 f\n"
    #iterates through all the possible object ids and adds them, if no obj at an id adds a free object
    for i in range(1,numberOfObj +1):
        try:
            if xrefDict[i]:
                idLen = len(str(xrefDict[i]))
                finalstr = str(xrefDict[i])
                for j in range(10-idLen):
                    finalstr = "0" + finalstr
                finalstr +=  " 00000 n \n"
                xrefStr += finalstr
            else:
                xrefStr += "0000000000 65535 f \n"
        except:
            xrefStr += "0000000000 65535 f \n"
    return xrefStr, numberOfObj 

#remaps the ids of PDF with the new ids
#returns the new pdf string, can be directly used
#PDF_Data is a list
#here PDF_Data is the list of all objects in the PDF
def PDF_ID_Remap(PDF_Data, PDFString, OriginalID):
    #Making a mapping dict what has originalID as key and NewID as value
    mapping_Dict = {}
    for obj in PDF_Data:
        # print(obj["NewID"])
        mapping_Dict[str(obj[OriginalID])] = str(obj["NewID"])
 
    def Obj_Declaration(match):
        oldID = match.group(1)
        newID = mapping_Dict.get(oldID, oldID)
        return f'{newID} 0 obj'

    def Obj_Reference(match):
        oldID = match.group(1)
        newID = mapping_Dict.get(oldID, oldID)
        return f'{newID} 0 R'

    PDFString = re.sub(r'\b(\d+)\s+0\s+obj\b', Obj_Declaration, PDFString, flags=re.IGNORECASE)
    PDFString = re.sub(r'\b(\d+)\s+0\s+R\b', Obj_Reference, PDFString, flags=re.IGNORECASE)
    return PDFString