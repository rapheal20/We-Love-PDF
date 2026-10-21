import os
import re
import zlib

delimiterList = [" ", "\n", "\r", ">", "/"]

#Returns PDF version
def PDFVersionFunc(PDFPath):
    PDF = open(PDFPath, "rb")
    buffer = PDF.readline()
    PDFVersion = float(re.search(rb'%PDF-(\d\.\d)', buffer).group(1).decode('latin1'))
    PDF.close()

    return PDFVersion

def parseASCIIXref(PDFcontent: bytes, offset: int, xrefTable: dict):
    lines = PDFcontent[offset:].split(b"\n")

    if not lines[0].startswith(b"xref"):
        lines = PDFcontent[offset:].replace(b"\r", b"\n").split(b"\n")

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
                    xrefTable[objectID] = {
                        "offset": int(entry[0]),
                        "generation": int(entry[1]),
                        "type": entry[2].decode('latin1')
                    }

                index += 1
            continue
        index += 1

#I don't really wanna know how this runs so I have copied from Gemini. 
def removePNGPredictor(data: bytes, columns: int, row_width: int): 
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
            left = recon_row[c-1] if c > 0 else 0
            left_up = prev_row[c-1] if c > 0 else 0
            
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
    sizeM = re.search(b"\/Size\s+(\d+)", objectData)
    wM = re.search(b"\/W\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s*\]", objectData)
    predM = re.search(b"\/Predictor\s+(\d+)", objectData)
    colsM = re.search(b"\/Columns\s+(\d+)", objectData)
    indexM = re.search(b"\/Index\s*\[\s*([0-9\s]+)\s*\]", objectData)

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

            xrefTable[objectID] = {
                "offset": f2,
                "generation": f3,
                "type": typeStr
            }

#Returns XrefTable of the PDF
def XrefTableFunc(PDFPath):
    xrefTable = {}

    PDF = open(PDFPath, "rb")
    PDFcontent = PDF.read()

    startXrefMatches = list(re.finditer(b"startxref\s+(\d+)", PDFcontent))

    xrefStreamMatches = list(re.finditer(b"(\d+)\s+(\d+)\s+obj\s*<<[^>]*\/Type\s*\/XRef", PDFcontent))

    #First method: Processing using the startxref pointers
    if startXrefMatches:
        for match in startXrefMatches:
            offset = int(match.group(1))
            if offset >= len(PDFcontent):
                continue

            peek = PDFcontent[offset: offset + 20].strip() #checking the offset location to find format

            if peek.startswith(b"xref"): #Older version
                parseASCIIXref(PDFcontent, offset, xrefTable)
            else: 
                objectMatch = re.search(b"(\d+)\s+(\d+)\s+obj", PDFcontent[max(0, offset-100):offset+50])
                if objectMatch:
                    objectID = int(objectMatch.group(1))
                    parseXrefStream(PDFcontent, PDFcontent.find(f"{objectID} ".encode() + b"0 obj", max(0, offset-200)), xrefTable)
    
    #Second method: hybrid streams
    if xrefStreamMatches:
        for match in xrefStreamMatches:
            streamOffset = match.start()
            parseXrefStream(PDFcontent, streamOffset, xrefTable)

    return xrefTable

    PDF.close()      

#Returns the RootObjectID of the PDF
def RootObjectIDFunc(PDFPath):
    PDF = open(PDFPath, "rb")
    PDFSize = os.path.getsize(PDFPath) - 1

    bufferSize = min(4096, PDFSize)

    PDF.seek(PDFSize - bufferSize)
    buffer = PDF.read()

    rootObject = re.search(rb'/Root\s+(\d+)\s+\d+\s+R', buffer)

    if rootObject:
        return int(rootObject.group(1))

    rootobjectAlt = re.search(rb'/Root\s+(\d+)', buffer)

    if rootobjectAlt:
        return int(rootobjectAlt.group(1))
    
    PDF.close()







'''BY RAPHEAL'''

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

#here PDF_Data is the list of all objects in the PDF
def PDF_ID_Remap(PDF_Data, PDFString, OriginalID):
    #Making a mapping dict what has originalID as key and NewID as value
    mapping_Dict = {}
    for obj in PDF_Data:
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

