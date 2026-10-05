'''
This function read all the pdf files given and merges them in the order selected.
The function will take the pdfs from inputs folder and a dict which will have file name as key and sequence number as value.
Then it will READ the pdfs in the order and WRITE to a new file
'''
import re

pdf1 = "Inputs\\file-example_PDF_1MB.pdf"
# pdf1 = "Inputs\\file-example_PDF_500_kB.pdf"

#cannot open PDF in "r" mode because of different types of data, so we use "rb" this opens in binary


with open(pdf1, "rb") as file:
    pdf1Data = file.read()


# with open(pdf2, "rb") as file:
#     pdf2Data = file.read()


#pdfData now holds the bytes of the pdf, these are the objects
pdf1String = pdf1Data.decode("latin1") #this converts the raw binary into string charaters but it maintains the character ratio so the calculated offset will be correct
# pdf2String = pdf2Data.decode("latin1")











# # print(pdf1String)







with open("pdfData2.txt" , "w", encoding="latin1") as file:
    file.write(pdf1String)
# #finding the object ids
objectFindString = r"(\d+)\s(\d+)\sobj" #the paranthesis divide it into groups so tha twe can later access the id directly
# with () we can use the .group command on it 
# .group(0) gives the whole match 
# .group(1) gives the first bracket 
# .group(2) gives the second bracket

# + sign here signifies or more digits so this allows for multiple digit ids
PDF1_Dict_Offset = []


# here we use .finditer instead of .findall as .finditer waits for one of the ouputs to worked on and then moves on to the next so memery efficint

objectIDsPdf1 = re.finditer(objectFindString, pdf1String)
for match in objectIDsPdf1:
    PDF1_Dict_Offset.append({int(match.group(1)) : match.start()})
# # .start() gives the byte offset which can also be taken from span[0]
startIndex = list(PDF1_Dict_Offset[0].values())[0]

# print(startIndex)
# print(pdf1String[startIndex:1000])


# <</Type/Pages this is the unique tag of /Parent, so it finds the location of that from the file 
# next it finds its starting offset 
# then iterates through the Offset dictionary and finds the offset just bigger then it, once it finds it, that index is saved as i - 1
# this way the acutal starting index of the /Parent is founf
# then it searches for endobj, as .search finds the first value so this way when starting from the offset the end of /Parent is found
# that is added into the offset adn this way the whole parent object can be selected


ParentObj = re.search("<</Type/Pages",pdf1String)
ParentOffset = ParentObj.start()

for i in range (len(PDF1_Dict_Offset)):
    offset = list(PDF1_Dict_Offset[i].values())[0]
    # print(offset)
    if offset > ParentOffset:
        ParentID = i-1
        break

ParentOffsetStart = list(PDF1_Dict_Offset[ParentID].values())[0]

ParentEndObj = re.search("endobj",pdf1String[ParentOffsetStart:])
ParentObjEnding = ParentEndObj.end() + ParentOffsetStart

ParentObject = pdf1String[ParentOffsetStart:ParentObjEnding]

KidsArrayStart = re.search("/Kids",ParentObject).end()
PDF1_kids = []
KidsFindString = r"(\d+)\s(\d+)\sR"
KidsPdf1 = re.finditer(KidsFindString, ParentObject[KidsArrayStart:])
for kid in KidsPdf1:
    PDF1_kids.append(kid.group(0))

print(PDF1_kids)


# <</Type/Catalog/Pages

CatalogObj = re.search("<</Type/Catalog/Pages",pdf1String)
CatalogOffset = CatalogObj.start()

for i in range (len(PDF1_Dict_Offset)):
    offset = list(PDF1_Dict_Offset[i].values())[0]
    # print(offset)
    if offset > CatalogOffset:
        CatalogID = i-1
        break

CatalogOffsetStart = list(PDF1_Dict_Offset[CatalogID].values())[0]

CatalogEndObj = re.search("endobj",pdf1String[CatalogOffsetStart:])
CatalogObjEnding = CatalogEndObj.end() + CatalogOffsetStart

xrefIndex = re.search("xref",pdf1String).start()
# print(CatalogObjEnding+1, xrefIndex)

newBody = ""
if CatalogOffsetStart > ParentOffsetStart:
    newBody += pdf1String[startIndex:ParentOffsetStart-1]
    newBody += pdf1String[ParentObjEnding+1:CatalogOffsetStart-1]
    newBody += pdf1String[CatalogObjEnding+1:xrefIndex-1]


with open("pdf2DataClean2.txt" , "w", encoding="latin1") as file:
    file.write(newBody)

# print(pdf1String[CatalogObjEnding-2:xrefIndex-1])

# ParentObject = pdf1String[ParentOffsetStart:ParentObjEnding]




# Pdf1_highestID = max(PDF1_Dict_Offset)

# PDF2_Dict_NewIDs = {}
# # we store the new id of the 2nd PDF as keys and their new ids as values

# objectIDsPdf2 = re.finditer(objectFindString, pdf2String)
# for match in objectIDsPdf2:
#     PDF2_Dict_NewIDs[int(match.group(1))] = int(match.group(1))+Pdf1_highestID

# print(PDF2_Dict_NewIDs)
    # print(int(match.group(1))+Pdf1_highestID)





# print(max(PDF_Dict_Offset))