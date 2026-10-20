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

    bufferSize = min(4096, PDFSize)

    PDF.seek(PDFSize - bufferSize)
    buffer = PDF.read()

    startXref = re.search(rb'startxref\s*(\d+)', buffer)

    XrefTableAddress = int(startXref.group(1))
    PDF.seek(XrefTableAddress)

    rawXrefData = PDF.read(PDFSize - XrefTableAddress)

    XrefTable = {}

    #Two type for xreftable: modern (/Type/XRef) or traditional
    if b"/Type/XRef" in rawXrefData or b"/Type /XRef" in rawXrefData:
        pass

    lines = rawXrefData.decode('latin1').splitlines()

    currentID = 0
    count = 0
    parsingEntries = False
    entryIndex = 0

    for line in lines:
        line = line.strip()
        if not line or line.lower() == 'trailer':
            if line.lower() == 'trailer':
                break
            continue

        if line.lower() == 'xref':
            parsingEntries = True
            continue

        if parsingEntries:
            headerMatch = re.match(r'^(\d+)\s+(\d+)$', line)
            if headerMatch:
                currentID = int(headerMatch.group(1))
                count = int(headerMatch.group(2))
                entryIndex = 0
                continue

            entryMatch = re.match(r'^(\d+)\s+(\d+)\s+([fn])$', line)
            if entryMatch and entryIndex < count:
                offset = int(entryMatch.group(1))
                status = entryMatch.group(3)
                
                if status == 'n':
                    XrefTable[currentID] = offset
                
                currentID += 1
                entryIndex += 1

    PDF.close()

    print(XrefTable)

    return XrefTable, XrefTableAddress

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

