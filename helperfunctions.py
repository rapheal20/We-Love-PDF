import os

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
            
            contents = buffer[contentIndex:].split(b"\n")[0] #This will get us the first line. eg b'/Contents 12 0 R'
            characters = contents.split()
            contentObjectID = int(characters[1].decode("latin1"))

            contentObjectLocation = XrefTable[contentObjectID]

            PDF.seek(contentObjectLocation)
            buffer = PDF.read(2048)

            contentStreams.append(buffer)
            
        elif kidsIndex != -1:
            #This is the sub tree node
            nestedStreams = pagesParse(objectLocation)
            contentStreams.extend(nestedStreams)

    return contentStreams #This gives us all the content 

pagesParse(catalogObjectLocation)

PDF.close()     