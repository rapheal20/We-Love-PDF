'''
This function read all the pdf files given and merges them in the order selected.
The function will take the pdfs from inputs folder and a dict which will have file name as key and sequence number as value.
Then it will READ the pdfs in the order and WRITE to a new file
'''
import re

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




# with open("pdfData2.txt" , "w", encoding="latin1") as file:
#     file.write(pdf1String)


# #finding the object ids
objectFindString = r"(\d+)\s(\d+)\sobj" 

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



# <</Type/Pages this is the unique tag of /Parent, so it finds the location of that from the file 
# next it finds its starting offset 
# then iterates through the Offset dictionary and finds the offset just bigger then it, once it finds it, that index is saved as i - 1
# this way the acutal starting index of the /Parent is founf
# then it searches for endobj, as .search finds the first value so this way when starting from the offset the end of /Parent is found
# that is added into the offset adn this way the whole parent object can be selected
#returns



#the following function removes the /Parent and /Catalog from a PDF file
def PDF_Clean(pdfData, pdfOffsetList):
    #Remove Header
    startIndex = pdfOffsetList[0]["Offset"]

    #Remove /Parent
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

    for i in range (len(pdfOffsetList)):
        offset = pdfOffsetList[i]["Offset"]
        if offset > CatalogTagOffset:
            CatalogID = i-1
            break

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


# print(PDF_Clean(pdf1String))

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



# print(PDF2_Data)
'''
FORMING NEW /PARENT OBJECT
'''

NewParentID = max(
    list(dict1["NewID"] for dict1 in PDF2_Data)
) + 1
# print(NewParentID)
# print(PDF1_Extract["PDF_Kids"])
# print(PDF2_Extract["PDF_Kids"])
newKids = PDF1_Extract["PDF_Kids"]
for kid in PDF2_Extract["PDF_Kids"]:
    newKids.append(int(kid) + Pdf1_highestID)

kidsStr = "/Kids[ "
for i in newKids:
   kidsStr += f"{i} 0 R " 
kidsStr += "]"
newParent = f'{NewParentID} 0 Obj\n<</Type/Pages\n' 
newParent += f'{kidsStr}\n'  
newParent += f'/Count {len(newKids)}>>\nendobj'

# Changing the Pointing of OBJs to new parent
oldParentStr = (f"/Parent {PDF1_Extract['ParentID']} 0 R")
newParentStr = (f"/Parent {NewParentID} 0 R")
body_edits =  str(PDF1_Extract["Cleaned_Data"])
PDF1_Final_Edit = body_edits.replace(oldParentStr, newParentStr)
# print(newBody)


#Forming New Catalog
newCatalog = f'{NewParentID+1} 0 Obj\n<</Type/Catalog/Pages {NewParentID+1} 0 R\n>>\nendobj' 
# print(newCatalog)

#PDF2 obj id change
PDF2Str = str(PDF2_Extract["Cleaned_Data"])
lengthOfData = len(PDF2_Data)
#looping in reverse to avaoid renumbering of the changed ids
for index in range (lengthOfData-1, -1, -1):

    oldObjIds = rf'\b{PDF2_Data[index]["OriginalID"]}\s+0\s+obj\b'
    newObjIds = f'{PDF2_Data[index]["NewID"]} 0 obj'

    oldRefIds = rf'\b{PDF2_Data[index]["OriginalID"]}\s+0\s+R\b'
    newRefIds = f'{PDF2_Data[index]["NewID"]} 0 R'
    PDF2Str = re.sub(
        oldObjIds, 
        newObjIds, 
        PDF2Str, 
        flags=re.IGNORECASE
        )

    PDF2Str = re.sub(
        oldRefIds, 
        newRefIds, 
        PDF2Str, 
        flags=re.IGNORECASE
        )


# print(PDF2_Edited)

oldParentStr2 = (f"/Parent {PDF2_Extract['ParentID']} 0 R")
# newParentStr = (f"/Parent {NewParentID} 0 R")
# body2_edits =  str(PDF2_Extract["Cleaned_Data"])
PDF2_Final_Edit = PDF2Str.replace(oldParentStr2, newParentStr)


    
# with open("pdf2Datareplace.txt" , "w", encoding="latin1") as file:
#     file.write(PDF2Str)
FinalPDFStr = PDF1_Final_Edit + PDF2_Final_Edit + newParent + newCatalog

with open("pdfmerge.txt" , "w", encoding="latin1") as file:
    file.write(FinalPDFStr)