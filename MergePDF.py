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

PDF Version 1.7:
Whats New:
- Object streams = /Type /ObjStm - these are many small objects packed into 1
- Cross-refernce streams = /Type /XRef = the xref table is stored as a compressed binary stream









'''
import re
from helperfunctions import *


# pdf2 = "Inputs\\file-example_PDF_1MB.pdf"
pdf4 = "Inputs\\file-example_PDF_500_kB.pdf"
pdf3 = "Inputs\\emaar1.pdf"
# pdf4 = "Inputs\\emaar.pdf"

def Merge_PDF(pdf1, pdf2):
    # try:
        #rb mode is for read only in binary mode

        PDF1 = open(pdf1, "rb")
        PDF2 = open(pdf2, "rb")

        pdf1Data = PDF1.read()
        pdf2Data = PDF2.read()

        #this converts the raw binary into string charaters but it maintains the character ratio so the calculated offset will be correct
        pdf1String = pdf1Data.decode("latin1") 
        pdf2String = pdf2Data.decode("latin1")

        # calls helper function which returns the xref table
        xref1, add1 = XrefTableFunc(pdf1)
        xref2, add2 = XrefTableFunc(pdf2)

        DecompressedObjs1 = {}
        DecompressedObjs2 = {}

        if isinstance(xref1, tuple):
            XrefTable1, add = xref1
        else:
            XrefTable1 = xref1

        if isinstance(xref2, tuple):
            XrefTable2, add = xref2
        else:
            XrefTable2 = xref2

        Root1 = RootObjectIDFunc(pdf1)
        Root2 = RootObjectIDFunc(pdf2)

        def FindParentsandKids(PDF, XrefTable, RootID, PDF_Data, DecompressedObjs):
            IDS_to_Remove = [RootID]
            ParentRefOffset = XrefTable[RootID]['offset']
            ParentFindStr = r"\s*/\s*Pages\s*(\d+)\s*0\s*R"
            ParentID = int((re.search(ParentFindStr, PDF_Data[ParentRefOffset:], flags=re.IGNORECASE)).group(1))
            IDS_to_Remove.append(ParentID)
            ParentBody = GetObjectBytes(PDF, XrefTable, ParentID, DecompressedObjs)
            ParentBody = ParentBody.decode('latin1')

            # print(ParentBody)

            #  searches for the kids in the parent obj and appends in the list
            KidsFindString = r"(\d+)\s*0\s*R"
            KidStart = (re.search(r"/\s*Kids", ParentBody, flags=re.IGNORECASE)).start()
            KidEnd = (re.search("]", ParentBody[KidStart:], flags=re.IGNORECASE)).end() + KidStart

            Kids = re.finditer(KidsFindString, ParentBody[KidStart:KidEnd], flags=re.IGNORECASE)
            Kids_List = []
            for kid in Kids:
                Kids_List.append(int(kid.group(1)))

            # finds the total number of pages
            PageCountString = r"/\s*Count\s*(\d+)"
            PageCount = (re.search(PageCountString, ParentBody, flags=re.IGNORECASE)).group(1)

            # if the extracted kids donot match with the count, then if means PDF has subParents, so then it goes to each subparent and and extracts its kids
            if int(PageCount) != (len(Kids_List)): 
                KidPages = []
                for kidID in Kids_List:
                    IDS_to_Remove.append(kidID)
                    KidObj = GetObjectBytes(PDF1, XrefTable1, kidID, DecompressedObjs)
                    KidObj = KidObj.decode('latin1')

                    KidStart = (re.search(r"/\s*Kids", KidObj, flags=re.IGNORECASE)).start()
                    KidEnd = (re.search("]", KidObj[KidStart:], flags=re.IGNORECASE)).end() + KidStart                       
                    SubKids = re.finditer(KidsFindString, KidObj[KidStart:KidEnd], flags=re.IGNORECASE)
                    for SubKid in SubKids:
                        KidPages.append(int(SubKid.group(1)))

                # replaces the subParents with the new pages list
                Kids_List = KidPages

            return Kids_List, IDS_to_Remove

        #finding the object ids
        objectFindString = r"\b(\d+)\s+(\d+)\s+obj" 


        PDF1_Pages_List, RemoveIDS1 = FindParentsandKids(PDF1, XrefTable1, Root1, pdf1String, DecompressedObjs1)
        # print(RemoveIDS1)
        PDF2_Pages_List, RemoveIDS2 = FindParentsandKids(PDF2, XrefTable2, Root2, pdf2String, DecompressedObjs2)
        # print(RemoveIDS2)
        '''
        the paranthesis divide it into groups so tha twe can later access the id directly
        with () we can use the .group command on it 
        .group(0) gives the whole match 
        .group(1) gives the first bracket 
        .group(2) gives the second bracket
        + sign here signifies or more digits so this allows for multiple digit ids
        .start() gives the byte offset which can also be taken from span[0]
        '''


        #Finds the highest object ID of PDF 1
        Pdf1_highestID = max(XrefTable1.keys()) if XrefTable1 else 0

        #this addes the Highest ID of PDF 1 into all the object ids of PDF 2 to avoid any repetition
        def ObjectExtraction(pdfPath, pdfDataStr, xreftab, idOffset=0):
            ObjectList =[]
            for objID, objData in xreftab.items():
                if objData.get("type") == "n" and objData.get("offset") > 0:
                    offset = objData['offset']
                    ObjEndStr = r"\bendobj"
                    ObjEnd = (re.search(ObjEndStr, pdfDataStr[offset:], flags=re.IGNORECASE)).start() + offset
                    newID = objID + idOffset
                    ObjectList.append({
                        "OriginalID" : int(objID),
                        "NewID" : int(newID),
                        "Content" : pdfDataStr[offset:ObjEnd]
                        })
            return ObjectList

        PDF1_Data = ObjectExtraction(pdf1, pdf1String, XrefTable1, idOffset=0)
        PDF2_Data = ObjectExtraction(pdf2, pdf2String, XrefTable2, idOffset=Pdf1_highestID)

        body1Str = ""
        i = 0
        for obj1 in PDF1_Data:
            if obj1["OriginalID"] not in RemoveIDS1:
                NewObj = GetObjectBytes(PDF1, XrefTable1, obj1["OriginalID"], DecompressedObjs1)
                NewObj = NewObj.decode('latin1')
                NewObj = f"\n{NewObj} \nendobj\n"
                body1Str += (NewObj)

        # with open("Outputs\\WeLovePDF_Merged.txt" , "w", encoding='latin1') as file:
        #     file.write(body1Str)

        body2Str = ""
        for obj2 in PDF2_Data:
            if obj2["OriginalID"] not in RemoveIDS2:
                NewObj = GetObjectBytes(PDF2, XrefTable2, obj2["OriginalID"], DecompressedObjs2)
                NewObj = NewObj.decode('latin1')
                NewObj = f"\n{NewObj} \nendobj\n"
                body2Str += (NewObj)



        
        # '''###### CLEANING THE PDF FILES (REMOVES /PARENT & /CATALOG) ######'''
        # PDF1_Extract = PDF_Clean(pdf1String, PDF1_Data)
        # PDF2_Extract = PDF_Clean(pdf2String, PDF2_Data)

        # '''###### MAKING & INITIALIZING THE NEW PARENT & CATALOG OBJECT ######'''
        # parentObj , ParentID = Make_Parent(PDF1_Extract, PDF2_Extract, PDF2_Data, Pdf1_highestID)
        # PDF1_Final = ParentIDChange(PDF1_Extract, ParentID)     #Changing PDF1 Parent
        # PDF2_Final = ParentIDChange(PDF2_Extract, ParentID)     #Changing PDF2 Parent
        # #making new catalog
        # catalogObj = f'\n{ParentID+1} 0 obj\n<</Type/Catalog/Pages {ParentID} 0 R\n>>\nendobj' 

        # #remapping th eids of PDF2 to the new ids
        # PDF2_Final = PDF_ID_Remap(PDF2_Data, PDF2_Final, "OriginalID")

        

        # #making new header
        # headerObj = Make_Header(pdf1String)

        # #forms a string of the new header, pd1, pdf2, parent and catalog object
        # CombinePDFStr = headerObj + PDF1_Final + PDF2_Final + parentObj + catalogObj

        # #making xref table
        # xreftable, ObjNumber = Make_Xref(objectFindString, CombinePDFStr)

        # #merging Combined PDF with xref
        # CombinePDFStr += xreftable

        # #making trailer
        # byteOffset = (re.search("xref", CombinePDFStr, flags=re.IGNORECASE)).start()
        # trailerObj = f"\ntrailer\n<<\n/Size {ObjNumber +1}\n/Root {ParentID+1} 0 R\n>>\nstartxref\n{byteOffset}\n%%EOF"

        # #Final string file
        # CombinePDFStr += trailerObj

        # #encoding it back into latin1
        # encodedPDF = CombinePDFStr.encode("latin1")
        # with open("Outputs\\WeLovePDF_Merged.pdf" , "wb") as file:
        #     file.write(encodedPDF)
    # except:
    #     print("Error")

#the following function removes the /Parent and /Catalog from a PDF file
def PDF_Clean(pdfData, pdfOffsetList):
    # #Remove Header
    # startIndex = pdfOffsetList[0]["Offset"]

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


# pdf3 = "Inputs\\DataRepresentation2k26.pdf"
# pdf4 = "Inputs\\TranslatorsNew.pdf"
Merge_PDF(pdf3, pdf4)

