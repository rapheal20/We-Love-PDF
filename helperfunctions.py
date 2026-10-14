import os
import re

delimiterList = [" ", "\n", "\r", ">", "/"]

#Returns PDF version
def PDFVersionFunc(PDFPath):
    PDF = open(PDFPath, "rb")
    PDFVersion = PDF.readline()
    PDFVersion = PDFVersion.decode('latin1').strip()
    PDFVersion = PDFVersion.split('-')[1]

    PDF.close()

    return PDFVersion

#Returns XrefTable of the PDF
def XrefTableFunc(PDFPath):
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

    return XrefTable, XrefTableAddress

#Returns the RootObjectID of the PDF
def RootObjectIDFunc(PDFPath):
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

