import os #file managment
import zlib #decompression
import re

PDFPath = "Inputs/file-example_PDF_1MB.pdf"
PDF = open(PDFPath, "rb") #rb is binary read mode

#This function parses /Tounicode Cmap stream into a dictionary map {hex_code: unicode_char}
def parseCmap(cmap_bytes):
    cmap = {}
    cmap_text = cmap_bytes.decode("latin1", errors="ignore")

    # Parse beginbfchar ... endbfchar
    bfchar_start = 0
    while True:
        pos = cmap_text.find("beginbfchar", bfchar_start)
        if pos == -1:
            break
        end_pos = cmap_text.find("endbfchar", pos)
        if end_pos == -1:
            break

        block = cmap_text[pos + 11 : end_pos].strip()
        lines = block.splitlines()
        for line in lines:
            parts = [p.strip("<>") for p in line.split() if p.startswith("<")]
            if len(parts) >= 2:
                src_hex, dst_hex = parts[0].upper(), parts[1]
                # Convert hex sequence to string
                try:
                    char_code = "".join(
                        chr(int(dst_hex[j : j + 4], 16))
                        for j in range(0, len(dst_hex), 4)
                    )
                    cmap[src_hex] = char_code
                except ValueError:
                    pass
        bfchar_start = end_pos + 9

    # Parse beginbfrange ... endbfrange
    bfrange_start = 0
    while True:
        pos = cmap_text.find("beginbfrange", bfrange_start)
        if pos == -1:
            break
        end_pos = cmap_text.find("endbfrange", pos)
        if end_pos == -1:
            break

        block = cmap_text[pos + 12 : end_pos].strip()
        lines = block.splitlines()
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                src_start = parts[0].strip("<>").upper()
                src_end = parts[1].strip("<>").upper()

                if src_start and src_end:
                    try:
                        start_val = int(src_start, 16)
                        end_val = int(src_end, 16)
                        hex_len = len(src_start)

                        # Range to single array: <srcStart> <srcEnd> [<dst1> <dst2>]
                        if "[" in line:
                            array_start = line.find("[")
                            array_end = line.find("]")
                            arr_tokens = [
                                t.strip("<>")
                                for t in line[array_start + 1 : array_end].split()
                            ]
                            for idx, val in enumerate(range(start_val, end_val + 1)):
                                if idx < len(arr_tokens):
                                    src_key = f"{val:0{hex_len}X}"
                                    dst_hex = arr_tokens[idx]
                                    cmap[src_key] = chr(int(dst_hex, 16))
                        # Continuous sequence: <srcStart> <srcEnd> <dstStart>
                        else:
                            dst_start = parts[2].strip("<>")
                            dst_val = int(dst_start, 16)
                            for idx, val in enumerate(range(start_val, end_val + 1)):
                                src_key = f"{val:0{hex_len}X}"
                                cmap[src_key] = chr(dst_val + idx)
                    except ValueError:
                        pass
        bfrange_start = end_pos + 10

    return cmap

#Fucntion which extracts and decompresses a PDF stream object
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
    if raw.endswith(b"\r\n"): raw = raw[:-2]
    elif raw.endswith(b"\n") or raw.endswith(b"\r"): raw = raw[:-1]

    if b"/FlateDecode" in header:
        try:
            return zlib.decompressobj().decompress(raw)   # tolerates trailing junk
        except zlib.error:
            try:
                return zlib.decompressobj(-zlib.MAX_WBITS).decompress(raw)
            except zlib.error:
                return raw
    return raw

import re

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

def balancedDict(buf, start):
    #buf[start:] begins with '<<'; return the full << ... >> including nesting.
    depth, i = 0, start
    while i < len(buf) - 1:
        two = buf[i:i+2]
        if two == b"<<":
            depth += 1; i += 2
        elif two == b">>":
            depth -= 1; i += 2
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
        name = e.group(1).decode("latin1")
        if e.group(2):
            fontBuf = readObject(int(e.group(2)))
            pos = e.end()
        else:
            fontBuf = balancedDict(inner, e.start(3))
            pos = e.start(3) + len(fontBuf)

        tu = re.search(rb"/ToUnicode\s+(\d+)\s+\d+\s+R", fontBuf)
        if tu:
            fontcMaps[name] = parseCmap(readandDecompressStream(int(tu.group(1))))
    return fontcMaps

#The version will then decide if decompression is needed.
#1.4 or older are already written in plain ASCII text
#Above that, it will be compressed with /FlatDecode
PDFVersion = PDF.readline()
PDFVersion = PDFVersion.decode('latin1').strip()
PDFVersion = PDFVersion.split('-')[1]

totalLines = os.path.getsize(PDFPath) - 1

bufferSize = 1024 #bytes

PDF.seek(totalLines - bufferSize)
buffer = PDF.read()

cursor = 0
XrefTable = ['s', 't', 'a', 'r', 't', 'x', 'r', 'e', 'f']
XrefTableAddress = ""
delimiterList = [" ", "\n", "\r", ">", "/"]

while cursor < bufferSize:
    currentByte = chr(buffer[cursor]) #This returns bytes as ASCII integer values. chr converts back into characters etc.
    cursor += 1

    #print(currentByte)

    word = []

    for i in range(9):
        if cursor + i < bufferSize:
            word.append(chr(buffer[cursor + i]))
        else:
            break

    if word == XrefTable:
        XrefTableEnd = cursor + 8

n = 0
#TESTING: output should be 468188
while XrefTableEnd+2+n < bufferSize:
    if chr(buffer[XrefTableEnd+2+n]) in delimiterList:
        break
    XrefTableAddress += (chr(buffer[XrefTableEnd+2+n])) # +2 for 2 spaces
    n += 1

#print(XrefTableAddress)

XrefTableAddress = int(XrefTableAddress)
PDF.seek(XrefTableAddress)

#print(PDF.read()) # \n0000000000 65535 f \n is each value in the table
# [10 digit offset] [5 digit generation] [flag]
# f entries are free so I will ignore those
# Save n entries to a dict where objectID: offset
# Stop when I hit the word trailer

rawXrefTableTrailer = PDF.read()
rawXrefTable = rawXrefTableTrailer.split(b'trailer')[0] # b converts trailer to binary

XrefTable = {}

rows = rawXrefTable.decode('latin1').splitlines() #Separating each entry into a list
#0 row is xref 
#1 row is total number of entries in the form 0 56 (start ID, Number of entries)
#2 row to last are entries

i = 0
#print(rows)

while i < len(rows):
    row = rows[i].strip()
    parts = row.split() #Getting each part

    if row == 'xref' or not row: #This targets row 0
        i += 1
        continue

    if len(parts) == 2 and parts[0].isdigit(): #This targets row 1
        currentID = int(parts[0])
        count = int(parts[1])

        for rownumber in range(count): 
            i += 1 #moving to row 3 now
            
            if i >= len(rows):
                break

            entryRow = rows[i].strip() 
            entryParts = entryRow.split()

            if len(entryParts) >= 3 and entryParts[2] == 'n':
                offset = int(entryParts[0])
                XrefTable[currentID] = offset

            currentID += 1
    i += 1

#print(XrefTable)
#Now I will find the /Root in trailer dictionary to know which object is the start.

rawTrailer = rawXrefTableTrailer.split(b'trailer')[1]
rawTrailer = rawTrailer.strip()

i = 0
root = ['/', 'R', 'o', 'o', 't']
rootObjectID = ""

while i < len(rawTrailer):
    line = chr(rawTrailer[i])

    #print(word)
    word = []

    for n in range(5):
        if n + i < len(rawTrailer):
            word.append(chr(rawTrailer[n + i]))
        else:
            break
            
    if word == root:
        #print(chr(rawTrailer[i+n+2]))
        while chr(rawTrailer[i+n+2]) not in delimiterList:
            rootObjectID += chr(rawTrailer[i+n+2])
            i += 1
    i += 1

rootObjectID = int(rootObjectID)

#print(rootObjectID)
#print(XrefTable)

#Now I need to get the root object from my Xref table. Read it to find the key document structure.

#Getting the structure. The root will hhave the address /Type/Catalog/Pages . We need to go to that object now
rootObjectLocation = XrefTable[rootObjectID]
PDF.seek(rootObjectLocation)
buffer = PDF.read()

catalogIndex = buffer.find(b"/Type/Catalog/Pages ") #This will return the index of the byte where it found the phrase

index = 0
catalogObjectID = "" 
while chr(buffer[catalogIndex+20+index]) not in delimiterList:
    if catalogIndex+20+index > len(buffer):
        break
    catalogObjectID += chr(buffer[catalogIndex+20+index])
    index += 1

catalogObjectID = int(catalogObjectID)

catalogObjectLocation = XrefTable[catalogObjectID]
PDF.seek(catalogObjectLocation)
buffer = PDF.read(1024)

#print(buffer)

countIndex = buffer.find(b"/Count ") #This will return the index of the byte where it found the phrase

#print(countIndex)

index = 0
numberOfPages = "" 
while chr(buffer[countIndex+index+7]) not in delimiterList:
    if countIndex+index+7 > len(buffer):
        break
    numberOfPages += chr(buffer[countIndex+index+7])
    index += 1

#I need to convert the pages code into a functions so that I can recursively call it
#We will extract all references inside /Kids and get their object id
#fetch each object and go to its details
#if it is a /Type/Page then its an actual leaf page so collect its /Contents
#if it has /Kids so recall the function

def pagesParse(currentLocation):
    objectList = []
    contentStreams = []

    PDF.seek(currentLocation)
    buffer = PDF.read(1024)

    kidsIndex = buffer.find(b"/Kids")
    if kidsIndex == -1:
        return contentStreams

    startBracket = buffer.find(b"[", kidsIndex)
    endBracket = buffer.find(b"]", startBracket)

    kidsList = buffer[startBracket + 1 : endBracket]
    
    kidsList = kidsList.split()

    i = 0
    for i in range(len(kidsList)):
        if kidsList[i] == b"R":
            object = int(kidsList[i-2].decode('latin1'))
            objectList.append(object)

    for object in objectList:  
        objectLocation = XrefTable[object]
        PDF.seek(objectLocation)
        buffer = PDF.read(1024)

        contentIndex = buffer.find(b"/Contents") #These return -1 if they can't find
        subkidsIndex = buffer.find(b"/Kids")

        if contentIndex != -1:
            #Its a leaf page so we will extract the content stream object ID after /contents

            resourceIndex = buffer.find(b"/Resources") #Going to resources

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

                #I have tried a lot to get the /ToUnicode but I can't find it anywehre in the file
                #Before toUnicode, I need to go into each font F1, F2 etc
                #I need to follow the flowchart. 
                #if to unicode exists, use cmap parser
                #if tounicode doesn't exist, check encoding
                #if its named /Encoding decode using Latin1 
                #if its named /Differences array, map glyph names to unicode
                
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
                                        currCode = int(str)
                                    elif tStr.startswith("/"):
                                        glyphName = tStr[1:]
                                        srckey = f"{currCode:02X}" #formats as 2 digit hexadecimal key
                                        if len(glyphName) == "space":
                                            cMap[srckey] = " "
                                        elif glyphName == "space":
                                            cMap[srckey] = " "
                                        currCode += 1

            contents = buffer[contentIndex:].split(b"\n")[0] #This will get us the first line. eg b'/Contents 12 0 R'
            characters = contents.split()
            contentObjectID = int(characters[1].decode("latin1"))

            contentObjectLocation = XrefTable[contentObjectID]

            PDF.seek(contentObjectLocation)
            buffer = PDF.read()

            contentStreams.append(buffer)
            
        elif subkidsIndex != -1:
            #This is the sub tree node
            nestedStreams = pagesParse(objectLocation)
            contentStreams.extend(nestedStreams)

    return contentStreams, fontscMap #This gives us all the content 

contentStreams, fontscMap = pagesParse(catalogObjectLocation) #contentstreams is a list so a for loop is needed

for contentStream in contentStreams:
    #Now we will find each stream of data and decode it using zlib
    streamStart = contentStream.find(b"stream")
    streamEnd = contentStream.find(b"endstream", streamStart)

    #skip 'stream\r\n' or 'stream\n'
    if contentStream[streamStart + 6: streamStart + 8] == b"\r\n":
        rawDataStart = streamStart + 8 
    else:
        rawDataStart = streamStart + 7

    rawBytes = contentStream[rawDataStart:streamEnd].strip()

    #Checking if stream is flatedecode compressed and decompressed
    if b"/FlateDecode" in contentStream:
        try:
            decompressed = zlib.decompress(rawBytes) 
            decompressed = decompressed.decode("latin1", errors="ignore")
        except:
            decompressed = zlib.decompress(rawBytes, -zlib.MAX_WBITS) #-zlib.MAX_WBITS is a decompression method
            decompressed = decompressed.decode("latin1", errors="ignore")
    else:
        decompressed = rawBytes.decode("latin1", errors="ignore")

    #Now I need to parse text instructions from the PDF layout commands.  
    #BT ET are begin text and end text blocks
    #Td is text move eg 95.6 422.1 Td . first 2 are coordinates(from left, from bottom)
    # /F2 10.5 Tf: this is text fond and size
    #[ <1D0B> -4 <0A> 3 ... ] TJ: Tj is an array operator which renders text, angle brackets contain hexadecimal character code, numbers are micor adjustments
    # AND SO ON 

    #First step is separating all text parts into text or Tj (hex)
    #and then save it 

    #BT is start, ET is end, TJ is hexacode array, Tj is string 

    extractedData = []
    cursor = 0

    while True:
        BTPosition = decompressed.find("BT", cursor)
        ETPosition = decompressed.find("ET", BTPosition + 2)

        if BTPosition == -1 or ETPosition == -1:
            break

        block = decompressed[BTPosition:ETPosition]

        #Track search index inside the block so find() doesn't get stuck in an infinite loop
        blockCursor = 0

        while True:
            #Look for TJ and Tj starting from blockCursor
            TJPosition = block.find("TJ", blockCursor)
            TjPosition = block.find("Tj", blockCursor)

            #Break when no more text operators exist in this block
            if TJPosition == -1 and TjPosition == -1:
                break

            #Process TJ (array) if it comes before Tj (or if Tj doesn't exist)
            if TJPosition != -1 and (TjPosition == -1 or TJPosition < TjPosition):
                arrayStart = block.find("[", blockCursor)
                arrayEnd = block.find("]", arrayStart)

                if arrayStart != -1 and arrayEnd != -1:
                    arrayContent = block[arrayStart + 1 : arrayEnd]
                    extractedData.append({"type": "TJ", "raw": arrayContent})

                #Advance inner cursor past 'TJ'
                blockCursor = TJPosition + 2

            #Process Tj (single string)
            elif TjPosition != -1:
                #Slice up to TjPosition to find string bounds for THIS operator
                subBlock = block[blockCursor:TjPosition]

                SStart = subBlock.find("(")
                SEnd = subBlock.rfind(")")

                HStart = subBlock.find("<")
                HEnd = subBlock.rfind(">")

                if SStart != -1 and SEnd != -1 and SStart < SEnd:
                    stringContent = subBlock[SStart + 1 : SEnd]
                    extractedData.append({"type": "TjLiteral", "raw": stringContent})
                elif HStart != -1 and HEnd != -1 and HStart < HEnd:
                    hexContent = subBlock[HStart + 1 : HEnd]
                    extractedData.append({"type": "TjHex", "raw": hexContent})

                #Advance inner cursor past 'Tj'
                blockCursor = TjPosition + 2

        #Moved cursor update OUTSIDE the inner loop so the outer loop can find the next BT
        cursor = ETPosition + 2

    #Now extracted data is a list of dictionaries with TJ type, TjLiteral, TjHex
    #Now I need to scan each iteam and save all the TJ and TjHex inn a clean list.

    allPageHexCodes = []
    for item in extractedData:
        if item["type"] == "TJ": 
            rawArray = item["raw"] #example vale of rawArray will be '<1D0B>-4<0A>'
            
            index = 0

            while index < len(rawArray):
                if rawArray[index] == "<":
                    closeIndex = rawArray.find(">", index)
                    if closeIndex != -1:
                        hexCode = rawArray[index + 1: closeIndex]
                        allPageHexCodes.append(hexCode)
                        index = closeIndex
                index += 1
        elif item["type"] == "TjHex":
            allPageHexCodes.append(item["raw"]) #for TjHex, everything is already in the correct form

    #Now the next step is to map hex codes to standard letters like 'A' etc.
    #I need to find the page's /Resources /Font dictionary 
    #Find /ToUnicode table 
    #parse the table into a dictionary in the format { "1D0B": "A", "0A": "e", ... } etc
    #To get the resources, I am adding code to the function which is already getting content

    print(fontscMap)

PDF.close()     