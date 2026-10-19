import re


pdf3 = "Inputs\\emaar.pdf"

with open(pdf3, "rb") as file:
    PDF_Data_RB = file.read()

PDF_Data = PDF_Data_RB.decode('latin1')

#finds the root of the PDF and extracts the ID of the Catalog
trailerFindString = r"/\s*Root\s+(\d+)\s+(\d+)\s+R"
Catalog = re.search(trailerFindString, PDF_Data, flags=re.IGNORECASE)
CatalogID = (Catalog.group(1))

#finds the Catalog object and from it extracts the parent ID 
ParentRefOffset = (re.search(fr"{CatalogID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
ParentFindStr = r"\s*/\s*Pages\s*(\d+)\s*0\s*R"
ParentObj = re.search(ParentFindStr, PDF_Data[ParentRefOffset:], flags=re.IGNORECASE)
ParentID = (ParentObj.group(1))

# searches up the parent id and finds the parent object
MainParentOffset = (re.search(fr"{ParentID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
MainParentEnd = (re.search("]", PDF_Data[MainParentOffset:], flags=re.IGNORECASE)).end() + MainParentOffset
ParentBody = PDF_Data[MainParentOffset:MainParentEnd]

#  searches for the kids in the parent obj and appends in the list
KidsFindString = r"\s*(\d+)\s*0\s*R"
Kids = re.finditer(KidsFindString, ParentBody, flags=re.IGNORECASE)
Kids_List = []
for kid in Kids:
    Kids_List.append(int(kid.group(1)))

# finds the total number of pages
PageCountString = r"\s*/\s*Count\s*(\d+)"
PageCount = (re.search(PageCountString, ParentBody, flags=re.IGNORECASE)).group(1)

# if the extracted kids donot match with the count, then if means PDF has subParents, so then it goes to each subparent and and extracts its kids
if PageCount != len(Kids_List): 
    KidPages = []
    for kidID in Kids_List:
        SubParents = re.finditer(fr"{kidID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)   
        for  SubParent in SubParents:
            SubParentOffset = SubParent.start()
            #uses ] instead of endobj to ensure only the kids are picked and not any other references
            SubParentEnd = (re.search("]", PDF_Data[SubParentOffset:], flags=re.IGNORECASE)).end() + SubParentOffset
            SubParentBody = PDF_Data[SubParentOffset:SubParentEnd]
            Kids = re.finditer(KidsFindString, SubParentBody, flags=re.IGNORECASE)
            for kid in Kids:
                KidPages.append(int(kid.group(1)))

    # replaces the subParents with the new pages list
    Kids_List = KidPages

# print(Kids_List)


# print(PageCount)
# print(Kids_List)

#extracting content from each page

'''
PDF_Pages = {
    215 : {
        'ObjectID' : 215,
        'Body' : ... , 
        'ContentRefs' : []
        'ResourcesRefs' : []
        }
    }
'''

PDF_Pages = {}
objectEndString = r"\bendobj"
for Kid_ID in Kids_List:
    # print(Kids_List)
    # print(Kid1)
    StartOffset = (re.search(fr"{Kid_ID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
    EndOffset = (re.search(objectEndString, PDF_Data[StartOffset:], flags=re.IGNORECASE)).end() + StartOffset
    PDF_Pages[Kid_ID] = {
        'ObjectID' : Kid_ID,
        "Body" : PDF_Data[StartOffset: EndOffset]
    }

# print(PDF_Pages)

PDF_Pages_List = list(PDF_Pages.values())
for KidObj in PDF_Pages_List:
    #Content Ref
    Content_Ref_List = []
    ObjBody = (KidObj['Body'])

    ContentStartStr = r"\s*/\s*Contents\s*["
    ContentStart = (re.search(r"\s*/\s*Contents\s*[", ObjBody, flags=re.IGNORECASE))
    ContentEnd = (re.search("]", KidObj['Body'][ContentStart:], flags=re.IGNORECASE)).start() + ContentStart
    ContentSelected = KidObj['Body'][ContentStart:ContentEnd]
    ContentRefs = re.finditer(KidsFindString, ContentSelected, flags=re.IGNORECASE)
    for Ref in ContentRefs:
        Content_Ref_List.append(int(Ref.group(1)))

    print(Content_Ref_List)

    break

