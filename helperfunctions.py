import os

delimiterList = [" ", "\n", "\r", ">", "/"]

#Returns PDF version
def PDFVersion(PDFPath):
    PDF = open(PDFPath, "rb")
    PDFVersion = PDF.readline()
    PDFVersion = PDFVersion.decode('latin1').strip()
    PDFVersion = PDFVersion.split('-')[1]

    PDF.close()

    return PDFVersion

#Returns XrefTable of the PDF
def XrefTable(PDFPath):
    PDF = open(PDFPath, "rb")
    PDFSize = os.path.getsize(PDFPath) - 1

    bufferSize = min(1024, PDFSize)

    PDF.seek(PDFSize - bufferSize)
    buffer = PDF.read()

    startXrefAddressPosition = buffer.find(b"startxref")
    EndXrefAddressPositon = startXrefAddressPosition + 10

    XrefTableAddress = ""
    
    cursor = EndXrefAddressPositon 
    while cursor < bufferSize:
        currentByte = chr(buffer[cursor])
        if currentByte in delimiterList:
            break
        XrefTableAddress += currentByte
        cursor += 1

    XrefTableAddress = int(XrefTableAddress)
    PDF.seek(XrefTableAddress)

    rawXrefTableTrailer = PDF.read()
    rawXrefTable = rawXrefTableTrailer.split(b'trailer')[0]

    XrefTable = {}

    rows = rawXrefTable.decode('latin1').splitlines()

    i = 0
    
    while i < len(rows):
        row = rows[i].strip()
        parts = row.split() #Getting each part

        if row.lower() == 'xref' or not row: #This targets row 0
            i += 1
            continue

        if row.lower() == 'trailer':
            break

        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit(): #This targets row 1
            currentID = int(parts[0])
            count = int(parts[1])

            for rowNumber in range(count): 
                i += 1 #moving to row 3 now
                
                if i >= len(rows):
                    break

                entryRow = rows[i].strip() 
                entryParts = entryRow.split()

                if len(entryParts) >= 3:
                    status = entryParts[2]
                    if status == 'n':
                        offset = int(entryParts[0])
                        XrefTable[currentID] = offset

                    currentID += 1
        i += 1

    PDF.close()

    return XrefTable

#Returns the RootObjectID of the PDF
def RootObjectID(PDFPath):
    PDF = open(PDFPath, "rb")
    PDFSize = os.path.getsize(PDFPath) - 1

    bufferSize = min(1024, PDFSize)

    PDF.seek(PDFSize - bufferSize)
    buffer = PDF.read()

    startRootObjectIDPosition = buffer.find(b"/Root")
    EndRootObjectIDPositon = startRootObjectIDPosition + 6

    RootObjectID = ""
    
    cursor = EndRootObjectIDPositon 
    while cursor < bufferSize:
        currentByte = chr(buffer[cursor])
        if currentByte in delimiterList:
            break
        RootObjectID += currentByte
        cursor += 1

    RootObjectID = int(RootObjectID)

    PDF.close()

    return RootObjectID

def PagesCollector(PDFPath):
    