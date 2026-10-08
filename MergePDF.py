'''
This function read all the pdf files given and merges them in the order selected.
The function will take the pdfs from inputs folder and a dict which will have file name as key and sequence number as value.
Then it will READ the pdfs in the order and WRITE to a new file
'''
import re
from helperfunctions import XrefTable
pdf2 = "Inputs\\file-example_PDF_1MB.pdf"
pdf1 = "Inputs\\file-example_PDF_500_kB.pdf"

#cannot open PDF in "r" mode because of different types of data, so we use "rb" this opens in binary


with open(pdf1, "rb") as file:
    pdf1Data = file.read()


with open(pdf2, "rb") as file:
    pdf2Data = file.read()


#pdfData now holds the bytes of the pdf, these are the objects
pdf1String = pdf1Data.decode("latin1") #this converts the raw binary into string charaters but it maintains the character ratio so the calculated offset will be correct
pdf2String = pdf2Data.decode("latin1")



'''
Universal List Format For Each PDF
e.g

    PDF_Data = [
        {"OriginalID" : 2,
        "NewID" : 12,
        "Offset" : 2345}
    ]

NewID is only in the PDF 2 data

'''

#Header Make

HeaderStr = r"%PDF-(\d+\.\d+)" 
headermatch = re.search(HeaderStr, pdf1String)
# print(headermatch)
if headermatch:
    version = headermatch.group(0)
PDFheader = version + "\n%âãÏÓ\n"


# #finding the object ids
objectFindString = r"\b(\d+)\s(\d+)\sobj" 

#the paranthesis divide it into groups so tha twe can later access the id directly
# with () we can use the .group command on it 
# .group(0) gives the whole match 
# .group(1) gives the first bracket 
# .group(2) gives the second bracket
# + sign here signifies or more digits so this allows for multiple digit ids

# .start() gives the byte offset which can also be taken from span[0]
PDF1_Data = []


# here we use .finditer instead of .findall as .finditer waits for one of the ouputs to worked on and then moves on to the next so memery efficint
objectIDsPdf1 = re.finditer(objectFindString, pdf1String)


for match in objectIDsPdf1:
    PDF1_Data.append(
        {"OriginalID" : int(match.group(1)),
        "Offset" : match.start()}
        )

#the following function removes the /Parent and /Catalog from a PDF file
def PDF_Clean(pdfData, pdfOffsetList):
    #Remove Header
    startIndex = pdfOffsetList[0]["Offset"]

    #Remove /Parent
    # <</Type/Pages this is the unique tag of /Parent, so it finds the location of that from the file and its offset
    ParentTagOffset = (re.search("<</Type/Pages", pdfData)).start() #It searches for header obj and stores its byte offset

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

    CatalogTagOffset = (re.search("<</Type/Catalog/Pages",pdfData)).start()

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


Pdf1_highestID = max(
    list(dict1["OriginalID"] for dict1 in PDF1_Data)
)

PDF2_Data = []

objectIDsPdf2 = re.finditer(objectFindString, pdf2String)
for match in objectIDsPdf2:
    PDF2_Data.append(
        {"OriginalID" : int(match.group(1)),
         "NewID" : int(match.group(1))+Pdf1_highestID,
        "Offset" : match.start()}
        )

PDF1_Extract = PDF_Clean(pdf1String, PDF1_Data)
PDF2_Extract = PDF_Clean(pdf2String, PDF2_Data)

'''
FORMING NEW /PARENT OBJECT
'''

NewParentID = max(
    list(dict1["NewID"] for dict1 in PDF2_Data)
) + 1

newKids = PDF1_Extract["PDF_Kids"]
for kid in PDF2_Extract["PDF_Kids"]:
    newKids.append(int(kid) + Pdf1_highestID)
# print(PDF2_Extract["PDF_Kids"])

kidsStr = "/Kids[ "
for i in newKids:
   kidsStr += f"{i} 0 R " 
kidsStr += "]"
newParent = f'\n{NewParentID} 0 obj\n<</Type/Pages\n' 
newParent += f'{kidsStr}\n'  
newParent += f'/Count {len(newKids)}>>\nendobj\n'
# print(newParent)




PDF1_Final_Edit = ParentIDChange(PDF1_Extract, NewParentID)     #Changing PDF1 Parent
PDF2Str = ParentIDChange(PDF2_Extract, NewParentID)     #Changing PDF2 Parent

#Forming New Catalog
newCatalog = f'\n{NewParentID+1} 0 obj\n<</Type/Catalog/Pages {NewParentID} 0 R\n>>\nendobj' 

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

PDF2Str = re.sub(r'\b(\d+)\s+0\s+obj\b', Obj_Declaration, PDF2Str, flags=re.IGNORECASE)
PDF2Str = re.sub(r'\b(\d+)\s+0\s+R\b', Obj_Reference, PDF2Str, flags=re.IGNORECASE)

# with open("pdf2Datareplace.txt" , "w", encoding="latin1") as file:
#     file.write(PDF2Str)

FinalPDFStr = PDFheader + PDF1_Final_Edit + PDF2Str + newParent + newCatalog

# print(FinalPDFStr)
xrefDict = {}
xrefTableMatch = re.finditer(objectFindString, FinalPDFStr, flags=re.IGNORECASE)
for match in xrefTableMatch:
    xrefDict[int(match.group(1))] = match.start()



numberOfObj = max(xrefDict.keys())
print(numberOfObj)
# print(xrefDict)
xrefStr = f"\n\nxref\n0 {numberOfObj+1}\n0000000000 65535 f\n"
# numberOfObj +1
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



# print(xrefStr)

#Trailer
concludedFile = FinalPDFStr + xrefStr
byteOffset = (re.search("xref", concludedFile, flags=re.IGNORECASE)).start()

trailer = f"\ntrailer\n<<\n/Size {numberOfObj +1}\n/Root {NewParentID+1} 0 R\n>>\nstartxref\n{byteOffset}\n%%EOF"
# print(trailer)


finalPDF = concludedFile + trailer

# with open("pdffinal.txt" , "w", encoding="latin1") as file:
#     file.write(finalPDF)


encodedPDF = finalPDF.encode("latin1")
with open("pdfffff333.pdf" , "wb") as file:
    file.write(encodedPDF)

# xref1, xref2 = (XrefTable("pdf333.pdf"))

# print(xref1, xref2)


