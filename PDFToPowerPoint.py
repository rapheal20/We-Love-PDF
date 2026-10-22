import re
import zlib
from io import BytesIO



pdf3 = "Inputs\\emaar1.pdf"
# pdf3 = "Inputs\\file-example_PDF_1MB.pdf"

with open(pdf3, "rb") as file:
    PDF_Data_RB = file.read()

PDF_Data = PDF_Data_RB.decode('latin1')

#finds the root of the PDF and extracts the ID of the Catalog
trailerFindString = r"/\s*Root\s+(\d+)\s+(\d+)\s+R"
Catalog = re.search(trailerFindString, PDF_Data, flags=re.IGNORECASE)
CatalogID = (Catalog.group(1))
# print(CatalogID)

#finds the Catalog object and from it extracts the parent ID 
ParentRefOffset = (re.search(fr"{CatalogID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
ParentFindStr = r"\s*/\s*Pages\s*(\d+)\s*0\s*R"
ParentObj = re.search(ParentFindStr, PDF_Data[ParentRefOffset:], flags=re.IGNORECASE)
ParentID = (ParentObj.group(1))
# print(ParentID)

# searches up the parent id and finds the parent object
MainParentOffset = (re.search(fr"{ParentID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
MainParentEnd = (re.search("endobj", PDF_Data[MainParentOffset:], flags=re.IGNORECASE)).end() + MainParentOffset
ParentBody = PDF_Data[MainParentOffset:MainParentEnd]
# print(ParentBody)

# print(Pare)
#  searches for the kids in the parent obj and appends in the list
KidsFindString = r"(\d+)\s*0\s*R"
KidStart = (re.search(r"/\s*Kids", ParentBody, flags=re.IGNORECASE)).start()
KidEnd = (re.search("]", ParentBody[KidStart:], flags=re.IGNORECASE)).end() + KidStart

Kids = re.finditer(KidsFindString, ParentBody[KidStart:KidEnd], flags=re.IGNORECASE)
Kids_List = []
for kid in Kids:
    Kids_List.append(int(kid.group(1)))
# print(len(Kids_List))

# finds the total number of pages
PageCountString = r"/\s*Count\s*(\d+)"
PageCount = (re.search(PageCountString, PDF_Data[MainParentOffset:], flags=re.IGNORECASE)).group(1)
# print(PageCount)
# if the extracted kids donot match with the count, then if means PDF has subParents, so then it goes to each subparent and and extracts its kids
if int(PageCount) != (len(Kids_List)): 
    # print("IN")
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
# print(Kids_List)

#extracting content from each page

def Content_Find(KidObject):
    ContentStartStr = r"/\s*Contents\s*"
    Ref_List = []
    ObjBody = (KidObject['Body'])


    Start = (re.search(ContentStartStr, ObjBody, flags=re.IGNORECASE)).end()
    End = (re.search(r"]|>|/", ObjBody[Start:], flags=re.IGNORECASE)).start() + Start
    Selected = ObjBody[Start:End]
    # print(Selected)
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
    Content_Ref_List = Content_Find(KidObj)
    PDF_Pages[KidObj['ObjectID']]["Content"] = Content_Ref_List


    ResFindStr = r"/\s*Resources\s*"
    ObjBody = KidObj["Body"]
    ResStart = (re.search(ResFindStr, ObjBody, flags=re.IGNORECASE)).end() #finds the starting offset of Resources
    ResEnd = (re.search(r">>>>", ObjBody[ResStart:], flags=re.IGNORECASE)).start() + ResStart #finds the ending offset of Resources
    ResSelected = ObjBody[ResStart:ResEnd]
    ResSelectedList = ResSelected.split("/")
    # print(ResSelectedList)

    '''
    Resources = {
        "CS0" : {
            "ObjectID" : 216,
            "Body" : ...,
            "Type" : Colourspace
        }
    }
    '''


    Resources = {}
    for i in range(len(ResSelectedList)):
        item = re.search(r"(\w+)\s*(\d+)\s*0\s*R", ResSelectedList[i], flags=re.IGNORECASE)
        if item:
            # item = re.search(r"(\w+)\s*(\d+)\s*0\s*R", ResSelectedList[i-1], flags=re.IGNORECASE)
            itemL = str(item.group(1)).lower()
            # print(itemL)
            if itemL.startswith("cs"):
                
                ResStartOffset = (re.search(fr"\b{int(item.group(2))}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
                ResEndOffset = (re.search(objectEndString, PDF_Data[ResStartOffset:], flags=re.IGNORECASE)).end() + ResStartOffset
                # Resources[item.group(1)] = {"ObjectID" : item.group(2), }
                # Resources[]["Body"] = PDF_Data[ResStartOffset: ResEndOffset]
                ResBody = PDF_Data[ResStartOffset: ResEndOffset]
                # print(ResBody)

                ICCBased = re.search(r"/\s*ICCBased", ResBody, flags=re.IGNORECASE)
                if ICCBased:
                    print("ICC")
                    ICCDefID = re.search(r"\s*(\d+)\s*0\s*R", ResBody, flags=re.IGNORECASE)
                    ICCID = int(ICCDefID.group(1))
                    ICCDefOffset = (re.search(fr"\b{ICCID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
                    ICCDefEnd = ((re.search(objectEndString, PDF_Data[ICCDefOffset:], flags=re.IGNORECASE)).end()) + ICCDefOffset
                    ICCObj = PDF_Data[ICCDefOffset:ICCDefEnd]

                    # finds the start of stream
                    StreamStart = (re.search(r"\s*stream\s*", ICCObj, flags=re.IGNORECASE)).end()
                    #find the end of stream
                    StreamEnd = (re.search(r"\s*endstream\s*", ICCObj, flags=re.IGNORECASE)).start()
                    ICCStream = ICCObj[StreamStart:StreamEnd]


                    FlateDecodeFilter = re.search(r"\s*/\s*FlateDecode\s*", ICCObj, flags=re.IGNORECASE)
                    if FlateDecodeFilter:
                        StreamSelect = ICCStream.encode('latin1')
                    try:
                        decompressedStreams = zlib.decompress(StreamSelect)
                    except:
                        # most pdfs have metadata in their header, this allows zlib to parse anyway
                        decompressedStreams = zlib.decompress(StreamSelect, wbits=-zlib.MAX_WBITS)

                    print(decompressedStreams)
                

    


    # for ResourceID in (Resources.keys()):
    #     ObjID = Resources[ResourceID]["ObjectID"]
        
        

    # print(Resources)
    # ResRefs = re.finditer(KidsFindString, Selected, flags=re.IGNORECASE)
    # for Ref in ContentRefs:
    #     Ref_List.append(int(Ref.group(1)))
    # return Ref_List
    break
# /Resources<<
# /ColorSpace<</CS0 216 0 R>>
# /ExtGState<</GS0 218 0 R/GS1 217 0 R>>
# /XObject<</Fm0 226 0 R>>
# >>



# for ContentObj in PDF_Pages_List:
#     ContentList = ContentObj['Content']
#     print(ContentObj["ObjectID"])
#     # print(ContentObj["Body"])
#     MediaBox = re.search(r"/\s*MediaBox\W(\d+\.\d+|\d+)\s+(\d+\.\d+|\d+)\s+(\d+\.\d+|\d+)\s+(\d+\.\d+|\d+)\W", ContentObj["Body"], flags=re.IGNORECASE)
#     # print(MediaBox)
#     MediaHeight = float(MediaBox.group(4)) - float(MediaBox.group(2))
#     MediaWidth = float(MediaBox.group(3)) - float(MediaBox.group(1))

#     print(MediaHeight, MediaWidth)
#     for ContentID in ContentList:
#         print(ContentID)
#         ContentStart = (re.search(fr"\b{ContentID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
#         ContentEnd = (re.search(objectEndString, PDF_Data[ContentStart:], flags=re.IGNORECASE)).end() + ContentStart
#         ContentBody = PDF_Data[ContentStart:ContentEnd]
#         # print(ContentBody)
#         FilterFind = re.search(r"\s*/\s*Filter\s*", ContentBody, flags=re.IGNORECASE)
#         #checks if there is a filter or not
#         if FilterFind:
#             FlateDecodeFilter = re.search(r"\s*/\s*FlateDecode\s*", ContentBody, flags=re.IGNORECASE)
#             if FlateDecodeFilter:
#                 # rb_Content = PDF_Data_RB[ContentStart:ContentEnd]

#                 # finds the start of stream
#                 StreamStart = (re.search(r"\s*stream\s*", ContentBody, flags=re.IGNORECASE)).end()
#                 #find the end of stream
#                 StreamEnd = (re.search(r"\s*endstream\s*", ContentBody, flags=re.IGNORECASE)).start()
#                 # Slices and selects just the stream
#                 StreamSelect = ContentBody[StreamStart:StreamStart+2716]
#                 # print((StreamSelect))
#                 # StreamSelect = StreamSelect.strip()
#                 # encodes the stream from string to latin1
#                 StreamSelect = StreamSelect.encode('latin1')
                
#                 # print(StreamSelect[:500])
#                 # decompresses the stream
#                 # break
#                 try:
#                     decompressedStreams = zlib.decompress(StreamSelect)
#                 except:
#                     # most pdfs have metadata in their header, this allows zlib to parse anyway
#                     decompressedStreams = zlib.decompress(StreamSelect, wbits=-zlib.MAX_WBITS)
                
#                 # converts it into string
#                 StringStream = decompressedStreams.decode('latin1')
#                 # print(StringStream)

#                 svg_elements = []
#                 svg_elements.append(f'<svg width="{MediaWidth}" height="{MediaHeight}" xmlns="http://www.w3.org/2000/svg">')
#                 current_fill = "#000000"
#                 StreamTokens = StringStream.split()
#                 # print(StreamTokens)

#                 # goes through each line and strips whitespaces
#                 # for line in StreamLines:
#                 #     line = line.strip()

#                 i = 0
#                 while i < len(StreamTokens):
#                     token = StreamTokens[i]
#                     #finds the colours
#                     if token == "scn" or token == "rg":
#                         # parts = line.split()
#                         # breaks on spaces, if colour system scn then converts nto rgb
#                         # pdfs use normalized floats while svg uses 8 bit rgb or hex

#                         if token == "rg" and i >= 3:
#                             r = int(float(StreamTokens[i-3]) * 255)
#                             g = int(float(StreamTokens[i-2]) * 255)
#                             b = int(float(StreamTokens[i-1]) * 255)
#                             current_fill = f"#{r:02x}{g:02x}{b:02x}"
#                             #make the current fill like #000000
#                             #: seperates text from formatting
#                             #02 sets the minimum lenght to 2
#                             #x converts into hexadecimal


#                     if token == 'q':
#                         #start of a new group of instructions
#                         block_tokens = []
#                         i += 1
#                         while i < len(StreamTokens) and StreamTokens[i] != "Q": #ensures not end of file and not end of group
#                             # appends the lines of that group
#                             block_tokens.append(StreamTokens[i])
#                             i += 1

#                         translateX, translateY = 0.0, 0.0 #default x and y
#                         path_data = []
#                         stack = []

#                         j = 0
#                         while j < len(block_tokens):
#                             t = block_tokens[j]

#                             if not t.isalpha() and t != "W" and t != 'n':
#                                 stack.append(t)
#                                 j += 1

#                             else:
#                                 op = t


#                                 if t == 'cm' and len(stack) >= 6:
#                                     translateX = float(stack[-2])
#                                     translateY = float(stack[-1])
#                                     stack = stack[:6]
#                                     # j += 1

#                                 elif op == 're' and len(stack) >= 4:
#                                     rx, ry, rw, rh = stack[-4:]
#                                     svg_elements.append(f'  <g transform="translate({translateX}, {translateY})">')
#                                     svg_elements.append(f'    <rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="{current_fill}" />')
#                                     svg_elements.append(f'  </g>')
#                                     stack = stack[:-4]
                                
#                                 elif t in ['m', 'l', 'c', 'v', 'y', 'h']:
                                    
#                                     if op != 'h':
#                                         svg_op = op.upper()
#                                     else:
#                                         svg_op = "Z"

#                                     if op == 'h':
#                                         # h takes no arguments
#                                         path_data.append(svg_op)
#                                     else:
#                                         coords = " ".join(stack)
#                                         path_data.append(f"{svg_op} {coords}")
#                                         stack = []

#                                 elif op in ['f', 'F', 'S', 'B']:
#                                     if path_data:
#                                         d_string = " ".join(path_data)
#                                         #cleanup multiple spaces
#                                         d_string = re.sub(r"\s+", " ", d_string).strip()

#                                         svg_elements.append((f'  <g transform="translate({translateX}, {translateY})">'))
#                                         svg_elements.append(f'    <path d="{d_string}" fill="{current_fill}" />')
#                                         svg_elements.append(f'  </g>')
#                                         path_data = []
#                                 else:
#                                     stack = []

#                                 j+=1
                  
#                     i += 1   
#                 svg_elements.append("</svg>")
#                 svg_output =  "\n".join(svg_elements)

#                 with open(f"Outputs\\test{ContentID}.svg" , "w") as file:
#                     file.write(svg_output)
                     


                

            
#         # break
#     break






    
    
#     # print(ContentList)
#     # break



