import re
import zlib
from io import BytesIO



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
        SubParents = re.finditer(fr"\b{kidID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)   
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

#extracting content from each page

def Reference_Find(KidObject, RefType):
    #RefType 1 for /Contents
    #RefType 2 for /Resources

    if RefType == 1:
        ContentStartStr = r"\s*/\s*Contents\s*"
    elif RefType == 0:
        ContentStartStr = r"\s*/\s*Resources\s*"

    Ref_List = []
    ObjBody = (KidObject['Body'])

    Start = (re.search(ContentStartStr, ObjBody, flags=re.IGNORECASE)).end()
    End = (re.search(r"/", ObjBody[Start:], flags=re.IGNORECASE)).start() + Start
    Selected = KidObject['Body'][Start:End]
    ContentRefs = re.finditer(KidsFindString, Selected, flags=re.IGNORECASE)
    for Ref in ContentRefs:
        Ref_List.append(int(Ref.group(1)))
    return Ref_List




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
    StartOffset = (re.search(fr"\b{Kid_ID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
    EndOffset = (re.search(objectEndString, PDF_Data[StartOffset:], flags=re.IGNORECASE)).end() + StartOffset
    PDF_Pages[Kid_ID] = {
        'ObjectID' : Kid_ID,
        "Body" : PDF_Data[StartOffset: EndOffset]
    }

PDF_Pages_List = list(PDF_Pages.values())
for KidObj in PDF_Pages_List:
    
    # Content Ref
    Content_Ref_List = Reference_Find(KidObj, 1)
    PDF_Pages[KidObj['ObjectID']]["Content"] = Content_Ref_List

for ContentObj in PDF_Pages_List:
    ContentList = ContentObj['Content']
    for ContentID in ContentList:
        ContentStart = (re.search(fr"\b{ContentID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
        ContentEnd = (re.search(objectEndString, PDF_Data[ContentStart:], flags=re.IGNORECASE)).end() + ContentStart
        ContentBody = PDF_Data[ContentStart:ContentEnd]
        FilterFind = re.search(r"\s*/\s*Filter\s*", ContentBody, flags=re.IGNORECASE)

        # /Filter/FlateDecode
        #checks if there is a filter or not
        if FilterFind:
            FlateDecodeFilter = re.search(r"\s*/\s*FlateDecode\s*", ContentBody, flags=re.IGNORECASE)
            if FlateDecodeFilter:
                # finds the start of stream
                StreamStart = (re.search(r"\s*stream\s*", ContentBody, flags=re.IGNORECASE)).end()
                #find the end of stream
                StreamEnd = (re.search(r"\s*endstream\s*", ContentBody, flags=re.IGNORECASE)).start()
                # Slices and selects just the stream
                StreamSelect = ContentBody[StreamStart:StreamEnd]
                # encodes the stream from string to latin1
                StreamSelect = StreamSelect.encode('latin1')
                # decompresses the stream
                decompressedStreams = zlib.decompress(StreamSelect)
                # converts it into string
                StringStream = decompressedStreams.decode('latin1')
                # Seperates each line into a list
                StreamLines = StringStream.split("\n")



                # for line in StreamLines:

                ''''''



                break

            break
        break
    break





    
    
    # print(ContentList)
    # break



