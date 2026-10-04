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
    if chr(buffer[XrefTableEnd+2+n]) == '\n':
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
        while chr(rawTrailer[i+n+2]) !=  " ":
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

i = 0
catalogObjectID = "" 
while chr(buffer[catalogIndex+20]) != " ":
    if i > len(buffer):
        break
    catalogObjectID += chr(buffer[catalogIndex+20+i])
    i += 1

print(catalogObjectID)

PDF.close()     