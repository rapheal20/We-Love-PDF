'''
This function read all the pdf files given and merges them in the order selected.
The function will take the pdfs from inputs folder and a dict which will have file name as key and sequence number as value.
Then it will READ the pdfs in the order and WRITE to a new file

Universal List Format For Each PDF
e.g

    PDF_Data = [
        {"OriginalID" : 2,
        "NewID" : 12,
        "Offset" : 2345}
    ]

NewID is only in the PDF 2 data

BASIC DESIGN CHOICES
- cannot open PDF in "r" mode because of different types of data, so we use "rb" this opens in binary
- here we use .finditer instead of .findall as .finditer waits for one of the ouputs to worked on and then moves on to the next so memery efficint
'''
import re


pdf2 = "Inputs\\file-example_PDF_1MB.pdf"
pdf1 = "Inputs\\file-example_PDF_500_kB.pdf"



def Merge_PDF(pdf1, pdf2):
    #rb mode is for read only in binary mode
    #opening file 1
    with open(pdf1, "rb") as file:
        pdf1Data = file.read()
    #opening file 2
    with open(pdf2, "rb") as file:
        pdf2Data = file.read()
    #pdfData now holds the bytes of the pdf, these are the objects
    #this converts the raw binary into string charaters but it maintains the character ratio so the calculated offset will be correct
    pdf1String = pdf1Data.decode("latin1") 
    pdf2String = pdf2Data.decode("latin1")
    #finding the object ids
    objectFindString = r"\b(\d+)\s(\d+)\sobj" 
    '''
    the paranthesis divide it into groups so tha twe can later access the id directly
    with () we can use the .group command on it 
    .group(0) gives the whole match 
    .group(1) gives the first bracket 
    .group(2) gives the second bracket
    + sign here signifies or more digits so this allows for multiple digit ids
    .start() gives the byte offset which can also be taken from span[0]
    '''
    
    '''###### OBJECT EXTRACTION FOR PDF 1 ######'''
    #main list for PDF1
    PDF1_Data = [] 
    objectIDsPdf1 = re.finditer(objectFindString, pdf1String)
    #Finds the orginalIDs and Offsets and appends into the main List
    for match in objectIDsPdf1:
        PDF1_Data.append(
            {"OriginalID" : int(match.group(1)),
            "Offset" : match.start()}
            )

    #Finds the highest object ID of PDF 1
    Pdf1_highestID = max(list(dict1["OriginalID"] for dict1 in PDF1_Data))

    '''###### OBJECT EXTRACTION FOR PDF 2 ######'''
    #main list for PDF2
    PDF2_Data = []
    objectIDsPdf2 = re.finditer(objectFindString, pdf2String)
    #Finds the orginalIDs and Offsets and appends into the main List
    for match in objectIDsPdf2:
        PDF2_Data.append(
            {"OriginalID" : int(match.group(1)),
            "NewID" : int(match.group(1))+Pdf1_highestID,
            "Offset" : match.start()}
            )
    #this addes the Highest ID of PDF 1 into all the object ids of PDF 2 to avoid any repetition


    '''###### CLEANING THE PDF FILES (REMOVES /PARENT & /CATALOG) ######'''
    PDF1_Extract = PDF_Clean(pdf1String, PDF1_Data)
    PDF2_Extract = PDF_Clean(pdf2String, PDF2_Data)

    '''###### MAKING & INITIALIZING THE NEW PARENT & CATALOG OBJECT ######'''
    parentObj , ParentID = Make_Parent(PDF1_Extract, PDF2_Extract, PDF2_Data, Pdf1_highestID)
    PDF1_Final = ParentIDChange(PDF1_Extract, ParentID)     #Changing PDF1 Parent
    PDF2_Final = ParentIDChange(PDF2_Extract, ParentID)     #Changing PDF2 Parent
    #making new catalog
    catalogObj = f'\n{ParentID+1} 0 obj\n<</Type/Catalog/Pages {ParentID} 0 R\n>>\nendobj' 

    #remapping th eids of PDF2 to the new ids
    PDF2_Final = PDF_ID_Remap(PDF2_Data, PDF2_Final)

    #making new header
    headerObj = Make_Header(pdf1String)

    #forms a string of the new header, pd1, pdf2, parent and catalog object
    CombinePDFStr = headerObj + PDF1_Final + PDF2_Final + parentObj + catalogObj

    #making xref table
    xreftable, ObjNumber = Make_Xref(objectFindString, CombinePDFStr)

    #merging Combined PDF with xref
    CombinePDFStr += xreftable

    #making trailer
    byteOffset = (re.search("xref", CombinePDFStr, flags=re.IGNORECASE)).start()
    trailerObj = f"\ntrailer\n<<\n/Size {ObjNumber +1}\n/Root {ParentID+1} 0 R\n>>\nstartxref\n{byteOffset}\n%%EOF"

    #Final string file
    CombinePDFStr += trailerObj

    #encoding it back into latin1
    encodedPDF = CombinePDFStr.encode("latin1")
    with open("Outputs\\WeLovePDF_Merged.pdf" , "wb") as file:
        file.write(encodedPDF)


 
# Makes new header object
def Make_Header(pdfString):
    # this function takes a pdf decoded in latin1
    HeaderStr = r"%PDF-(\d+\.\d+)" 
    headermatch = re.search(HeaderStr, pdfString)
    version = headermatch.group(0)
    #these series of characters are added to tell that the pdf to read character like \n for new line
    PDFheader = version + "\n%âãÏÓ\n"
    return PDFheader

#the following function removes the /Parent and /Catalog from a PDF file
def PDF_Clean(pdfData, pdfOffsetList):
    #Remove Header
    startIndex = pdfOffsetList[0]["Offset"]

    #Remove /Parent
    # <</Type/Pages this is the unique tag of /Parent, so it finds the location of that from the file and its offset
    ParentTagOffset = (re.search(r"<<\s*/Type\s*/Pages", pdfData)).start() #It searches for header obj and stores its byte offset

    for i in range (len(pdfOffsetList)):
        offset = pdfOffsetList[i]["Offset"]
        if offset > ParentTagOffset:
            ParentID = i-1
            break
        #Up until this point the code finds the Object ID from the dictionary of ids 

    Parent_Offset_Start = pdfOffsetList[ParentID]["Offset"]
    ParentObjId = pdfOffsetList[ParentID]["OriginalID"]

    #find the endobj tag of the /Parent and then adds the original offset of /Parent as the end is from the start of the ParentOffset
    # for it to be right for the whole file it is added
    Parent_Offset_End = (re.search("endobj",pdfData[Parent_Offset_Start:])).end() + Parent_Offset_Start

    #just selects the /Parent Object
    ParentObject = pdfData[Parent_Offset_Start:Parent_Offset_End]

    KidsArrayStart = re.search("/Kids",ParentObject).end()
    PDF_kids = []
    KidsFindString = r"(\d+)\s(\d+)\sR"
    KidsPdf1 = re.finditer(KidsFindString, ParentObject[KidsArrayStart:])
    for kid in KidsPdf1:
        PDF_kids.append(kid.group(1))

    CatalogTagOffset = (re.search(r"<<\s*/Type\s*/Catalog\s*/Pages",pdfData)).start()

    # then iterates through the Offset dictionary and finds the offset just bigger then it, once it finds it, that index is saved as i - 1
    for i in range (len(pdfOffsetList)):
        offset = pdfOffsetList[i]["Offset"]
        if offset > CatalogTagOffset:
            CatalogID = i-1
            break

    # this way the acutal starting index of the /Parent is founf
    Catalog_Offset_Start = pdfOffsetList[CatalogID]["Offset"]
    Catalog_Offset_End = (re.search("endobj",pdfData[Catalog_Offset_Start:])).end() + Catalog_Offset_Start
    xrefIndex = re.search("xref",pdfData).start()

    newBody = ""
    if Catalog_Offset_Start > Parent_Offset_Start:
        newBody += pdfData[startIndex:Parent_Offset_Start-1]
        newBody += pdfData[Parent_Offset_End+1:Catalog_Offset_Start-1]
        newBody += pdfData[Catalog_Offset_End+1:xrefIndex-1]
    elif Catalog_Offset_Start < Parent_Offset_Start:
        newBody += pdfData[startIndex:Catalog_Offset_Start-1]
        newBody += pdfData[Catalog_Offset_End+1:Parent_Offset_Start-1]
        newBody += pdfData[Parent_Offset_End+1:xrefIndex-1]

    # with open("pdf2DataClean2.txt" , "w", encoding="latin1") as file:
    #     file.write(newBody)

    return {
        "Cleaned_Data" : newBody,
        "PDF_Kids" : PDF_kids,
        "ParentID" : ParentObjId
    }

# Function for Changing the Parent of each OBJ
def ParentIDChange(PDFdata, NewParentID):
    newParentStr = (f"/Parent {NewParentID} 0 R")
    PDFStr = str(PDFdata["Cleaned_Data"])
    oldParentStr = (f"/Parent {PDFdata['ParentID']} 0 R")
    PDFStr = PDFStr.replace(oldParentStr, newParentStr)
    return PDFStr

#makes the new parent object
def Make_Parent(PDF1_Extract_Clean, PDF2_Extract_Clean, PDF2_Data, IncrementID):
    #finds the highest id of pdf2 and increments by 1 - used as the new parent id
    NewParentID = max(list(dict1["NewID"] for dict1 in PDF2_Data)) + 1

    #stores the PDF1 kids in a new list
    newKids = PDF1_Extract_Clean["PDF_Kids"]
    #iterates throught the kids of PDF 2 and appends each into the new list, increments alongside
    for kid in PDF2_Extract_Clean["PDF_Kids"]:
        newKids.append(int(kid) + IncrementID)

    #forms the new kids string
    kidsStr = "/Kids[ "
    # iterates through the new kids and corrects the format
    for i in newKids:
        kidsStr += f"{i} 0 R " 
    # the rest of the formatting for the parent
    kidsStr += "]"
    newParent = f'\n{NewParentID} 0 obj\n<</Type/Pages\n' 
    newParent += f'{kidsStr}\n'  
    newParent += f'/Count {len(newKids)}>>\nendobj\n'

    return newParent, NewParentID

#remaps the ids of PDF2 with the new incremented ids
def PDF_ID_Remap(PDF2_Data, PDF2String):
    #Making a mapping dict what has originalID as key and NewID as value
    mapping_Dict = {}
    for obj in PDF2_Data:
        mapping_Dict[str(obj["OriginalID"])] = str(obj["NewID"])

    def Obj_Declaration(match):
        oldID = match.group(1)
        newID = mapping_Dict.get(oldID, oldID)
        return f'{newID} 0 obj'

    def Obj_Reference(match):
        oldID = match.group(1)
        newID = mapping_Dict.get(oldID, oldID)
        return f'{newID} 0 R'

    PDF2String = re.sub(r'\b(\d+)\s+0\s+obj\b', Obj_Declaration, PDF2String, flags=re.IGNORECASE)
    PDF2String = re.sub(r'\b(\d+)\s+0\s+R\b', Obj_Reference, PDF2String, flags=re.IGNORECASE)
    return PDF2String

#makes the xref table with formatting as a string
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



pdf3 = "Inputs\\DataRepresentation2k26.pdf"
pdf4 = "Inputs\\TranslatorsNew.pdf"
Merge_PDF(pdf3, pdf4)

