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

OBJECT FIND STRING DETAILS
the paranthesis divide it into groups so tha twe can later access the id directly
with () we can use the .group command on it 
.group(0) gives the whole match 
.group(1) gives the first bracket 
.group(2) gives the second bracket
+ sign here signifies or more digits so this allows for multiple digit ids
.start() gives the byte offset which can also be taken from span[0]
'''
import re
from helperfunctions import *


pdf3 = "Inputs\\file-example_PDF_1MB.pdf"
pdf4 = "Inputs\\file-example_PDF_500_kB.pdf"
# pdf3 = "Inputs\\emaar1.pdf"
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

            return Kids_List, IDS_to_Remove, ParentID
      
        PDF1_Pages_List, RemoveIDS1, PDF1_Parent = FindParentsandKids(PDF1, XrefTable1, Root1, pdf1String, DecompressedObjs1)
        PDF2_Pages_List, RemoveIDS2, PDF2_Parent = FindParentsandKids(PDF2, XrefTable2, Root2, pdf2String, DecompressedObjs2)
   
        #Finds the highest object ID of PDF 1
        Pdf1_highestID = max(XrefTable1.keys()) if XrefTable1 else 0
        Pdf2_highestID = max(XrefTable2.keys()) if XrefTable1 else 0

        #this addes the Highest ID of PDF 1 into all the object ids of PDF 2 to avoid any repetition
        def ObjectExtraction(pdfDataStr, xreftab, idOffset=0):
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

        PDF1_Data = ObjectExtraction(pdf1String, XrefTable1)
        PDF2_Data = ObjectExtraction(pdf2String, XrefTable2, idOffset=Pdf1_highestID)


        '''###### CLEANING THE PDF FILES (REMOVES /PARENT & /CATALOG) ######'''
        body1Str = ""
        for obj1 in (PDF1_Data):
            if obj1["OriginalID"] not in RemoveIDS1:
                NewObj = GetObjectBytes(PDF1, XrefTable1, obj1["OriginalID"], DecompressedObjs1)
                NewObj = NewObj.decode('latin1')
                NewObj = f"\n{NewObj} \nendobj\n"
                body1Str += (NewObj)

        body2Str = ""
        for obj2 in (PDF2_Data):
            if obj2["OriginalID"] not in RemoveIDS2:
                NewObj = GetObjectBytes(PDF2, XrefTable2, obj2["OriginalID"], DecompressedObjs2)
                NewObj = NewObj.decode('latin1')
                NewObj = f"\n{NewObj} \nendobj\n"
                body2Str += (NewObj)


        # Function for Changing the Parent of each OBJ
        def ParentIDChange(PDFstr, OldParentID, NewParentID):
            newParentStr = (f"/Parent {NewParentID} 0 R")
            oldParentStr = (f"/Parent {OldParentID} 0 R")
            PDFstr = PDFstr.replace(oldParentStr, newParentStr)
            return PDFstr

        #makes the new parent object
        def Make_Parent(PDF1_Kids, PDF2_Kids, NewParentID, IncrementID):
            #stores the PDF1 kids in a new list
            newKids = PDF1_Kids
            #iterates throught the kids of PDF 2 and appends each into the new list, increments alongside
            for kid in PDF2_Kids:
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

            return newParent


        body2Str = PDF_ID_Remap(PDF2_Data ,body2Str , "OriginalID")

        '''###### MAKING & INITIALIZING THE NEW PARENT & CATALOG OBJECT ######'''
        NewParentID = Pdf1_highestID + Pdf2_highestID + 1
        parentObj = Make_Parent(PDF1_Pages_List, PDF2_Pages_List, NewParentID, Pdf1_highestID)
        PDF1_Final = ParentIDChange(body1Str, PDF1_Parent, NewParentID)     #Changing PDF1 Parent
        PDF2_Final = ParentIDChange(body2Str, PDF2_Parent, NewParentID)     #Changing PDF2 Parent
        #making new catalog
        catalogObj = f'\n{NewParentID+1} 0 obj\n<</Type/Catalog/Pages {NewParentID} 0 R\n>>\nendobj'      
        
        #making new header
        headerObj = Make_Header(pdf1String)

        #forms a string of the new header, pd1, pdf2, parent and catalog object
        CombinePDFStr = headerObj + PDF1_Final + PDF2_Final + parentObj + catalogObj

        #making xref table
        objectFindString = r"\b(\d+)\s+(\d+)\s+obj" 
        xreftable, ObjNumber = Make_Xref(objectFindString, CombinePDFStr)

        CombinePDFStr += xreftable

        #making trailer
        byteOffset = (re.search("xref", CombinePDFStr, flags=re.IGNORECASE)).start()
        trailerObj = f"\ntrailer\n<<\n/Size {ObjNumber +1}\n/Root {NewParentID+1} 0 R\n>>\nstartxref\n{byteOffset}\n%%EOF"

        CombinePDFStr += trailerObj

        #encoding it back into latin1
        encodedPDF = CombinePDFStr.encode("latin1")

        PDFName = os.path.basename(pdf1).split(".")[0]
        with open(f"Outputs\\{PDFName}-Merged.pdf" , "wb") as file:
            file.write(encodedPDF)

        PDF1.close
        PDF2.close
    # except:
    #     print("Error")


Merge_PDF(pdf3, pdf4)

