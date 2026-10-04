import os #file managment
import zlib #decompression

PDFPath = "Inputs/file-example_PDF_1MB.pdf"
PDF = open(PDFPath, "rb") #rb is binary read mode

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
                
                for token in resourceList:
                    if token.isdigit():
                            resourceObject = int(token.decode("latin1"))
                            break
                
                resourceObjectLocation = XrefTable[resourceObject]

                PDF.seek(resourceObjectLocation)
                secondarybuffer = PDF.read(4096)

                fontIndex = secondarybuffer.find(b"/Font") #Going to fonts

                if fontIndex != -1:
                    fontSnippet = secondarybuffer[fontIndex : fontIndex + 100]
                    fontTokens = fontSnippet.split()

                    for idx, token in enumerate(fontTokens): #enumerate 
                        if token == b"R" and idx >= 2:
                            fontObject = int(fontTokens[idx - 2].decode("latin1"))
                            fontObjectLocation = XrefTable[fontObject]

                            # Seek to actual Font Object
                            PDF.seek(fontObjectLocation)
                            secondarybuffer = PDF.read(4096)  # Read 4096 bytes for full Font Dict
                            break

            # buffer right now has a nested dictionary which is storing each font object as F1 F2 etc
            # Work for tomorrow
            
            toUnicodePosition = secondarybuffer.find(b"/ToUnicode")

            if toUnicodePosition != -1:
                lines = secondarybuffer[toUnicodePosition + 10 : toUnicodePosition + 60]

                cmapObjectID = None
                digitBytes = b""

                for byte in lines:
                    if 48 <= byte <= 57:  # ASCII 0-9
                        digitBytes += bytes([byte])
                    elif digitBytes:
                        cmapObjectID = int(digitBytes.decode("latin1"))
                        break

                if cmapObjectID is not None:
                    cmapLocation = XrefTable[cmapObjectID]
                    PDF.seek(cmapLocation)
                    cmapBuffer = PDF.read(4096)

                    sStart = cmapBuffer.find(b"stream")
                    sEnd = cmapBuffer.find(b"endstream", sStart)

                    if sStart != -1 and sEnd != -1:
                        if cmapBuffer[sStart + 6 : sStart + 8] == b"\r\n":
                            rawDataStart = sStart + 8
                        else:
                            rawDataStart = sStart + 7

                        rawBytes = cmapBuffer[rawDataStart:sEnd].strip()

                        try:
                            cmapText = zlib.decompress(rawBytes).decode("latin1", errors="ignore")
                        except Exception:
                            cmapText = zlib.decompress(rawBytes, -zlib.MAX_WBITS).decode("latin1", errors="ignore")

                        print(cmapText)
                    else:
                        print(f"Could not find stream/endstream in Object {cmapObjectID}.")
                else:
                    print("Could not parse object ID number after /ToUnicode.")
            else:
                print("No /ToUnicode reference found in this font object.")
            
            PDF.seek(objectLocation)
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

    return contentStreams #This gives us all the content 

contentStreams = pagesParse(catalogObjectLocation) #contentstreams is a list so a for loop is needed

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

PDF.close()     