import re
import zlib
from io import BytesIO



# pdf3 = "Inputs\\emaar.pdf"
pdf3 = "Inputs\\file-example_PDF_1MB.pdf"

with open(pdf3, "rb") as file:
    PDF_Data_RB = file.read()

PDF_Data = PDF_Data_RB.decode('latin1')

#finds the root of the PDF and extracts the ID of the Catalog
trailerFindString = r"/\s*Root\s+(\d+)\s+(\d+)\s+R"
Catalog = re.search(trailerFindString, PDF_Data, flags=re.IGNORECASE)
CatalogID = (Catalog.group(1))
print(CatalogID)

#finds the Catalog object and from it extracts the parent ID 
ParentRefOffset = (re.search(fr"{CatalogID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
ParentFindStr = r"\s*/\s*Pages\s*(\d+)\s*0\s*R"
ParentObj = re.search(ParentFindStr, PDF_Data[ParentRefOffset:], flags=re.IGNORECASE)
ParentID = (ParentObj.group(1))
print(ParentID)

# searches up the parent id and finds the parent object
MainParentOffset = (re.search(fr"{ParentID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
MainParentEnd = (re.search("endobj", PDF_Data[MainParentOffset:], flags=re.IGNORECASE)).end() + MainParentOffset
ParentBody = PDF_Data[MainParentOffset:MainParentEnd]

# print(Pare)
#  searches for the kids in the parent obj and appends in the list
KidsFindString = r"\b(\d+)\s*0\s*R"
KidStart = (re.search(r"/\s*Kids", ParentBody, flags=re.IGNORECASE)).start()
KidEnd = (re.search("]", ParentBody[KidStart:], flags=re.IGNORECASE)).end() + KidStart

Kids = re.finditer(KidsFindString, ParentBody[KidStart:KidEnd], flags=re.IGNORECASE)
Kids_List = []
for kid in Kids:
    Kids_List.append(int(kid.group(1)))

# finds the total number of pages
PageCountString = r"/\s*Count\s*(\d+)"
PageCount = (re.search(PageCountString, PDF_Data[MainParentOffset:], flags=re.IGNORECASE)).group(1)

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
print(Kids_List)

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
    print(KidObject['ObjectID'])
    print(ObjBody)

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
    print(ContentObj["ObjectID"])
    MediaBox = re.search(r"\s*/\s*MediaBox\W(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\W", ContentObj["Body"], flags=re.IGNORECASE)
    # print(MediaBox)
    MediaHeight = float(MediaBox.group(4)) - float(MediaBox.group(2))
    MediaWidth = float(MediaBox.group(3)) - float(MediaBox.group(1))

    print(MediaHeight, MediaWidth)
    for ContentID in ContentList:
        ContentStart = (re.search(fr"\b{ContentID}\s*0\s*obj", PDF_Data, flags=re.IGNORECASE)).start()
        ContentEnd = (re.search(objectEndString, PDF_Data[ContentStart:], flags=re.IGNORECASE)).end() + ContentStart
        ContentBody = PDF_Data[ContentStart:ContentEnd]
        FilterFind = re.search(r"\s*/\s*Filter\s*", ContentBody, flags=re.IGNORECASE)
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

                '''
                Need a transition logic
                
                - COnverting PostScript Vector into SVG

                CHANGES:
                m to M (moveto)
                l to L (lineto)
                c to C (curveto)
                h to Z (closepath)
                f to <path> (fill)

                TRACK GRAPHIC STATE WRAPPER
                - Stream starts with g and ends with Q blocks
                - these are opening and closing brackets
                - these need to be replaced with <g>
                
                ASEMBLE SVG XML
                - get width and height from mediabox
                - close SVG root tag
                '''

                svg_elements = []
                # list of elements of the new svg

                #makes the svg header using the width and height
                svg_elements.append(f'<svg width="{MediaWidth}" height="{MediaHeight}" xmlns="http://www.w3.org/2000/svg">')

                # sets default fill to black
                current_fill = "#000000"
                # removes the whitespaces at end and breaks the stream into lines
                StreamLines = ((StringStream.strip()).split("\n"))

                # goes through each line and strips whitespaces
                for line in StreamLines:
                    line = line.strip()

                i = 0
                while i < len(StreamLines):
                    line = StreamLines[i]
                    #finds the colours
                    if "scn" in line or "rg" in line:
                        parts = line.split()
                        # breaks on spaces, if colour system scn then converts nto rgb
                        # pdfs use normalized floats while svg uses 8 bit rgb or hex

                        if len(parts) >= 4 and parts[-1] == "scn":
                            r = int(float(parts[-4]) * 255)
                            g = int(float(parts[-3]) * 255)
                            b = int(float(parts[-2]) * 255)
                            current_fill = f"#{r:02x}{g:02x}{b:02x}"
                            #make the current fill like #000000
                            #: seperates text from formatting
                            #02 sets the minimum lenght to 2
                            #x converts into hexadecimal


                    if line.startswith('q'):
                        #start of a new group of instructions
                        block_lines = []
                        i += 1
                        while i < len(StreamLines) and StreamLines[i] != "Q": #ensures not end of file and not end of group
                            # appends the lines of that group
                            block_lines.append(StreamLines[i])
                            i += 1

                        translateX, translateY = 0.0, 0.0 #default x and y
                        path_cmd = []
                        mapping_commands = [(' m', ' M'), (' l', ' L'), (' c', ' C'), (' v', ' V'), (' y', ' Y'), (' h', ' Z'), (' f', '')]
                        path_Commands = ['m', 'l', 'c', 'v', 'y', 'h','f']
                        
                        for b_line in block_lines:
                            if b_line.endswith('cm'):
                                parts = b_line.strip()
                                if len(parts) >= 6:
                                    translateX = float(parts[4])
                                    translateY = float(parts[5])
                            
                            elif any(b_line.endswith(op) for op in path_Commands):
                                mapped_line = b_line
                                for op, svg_op in mapping_commands:
                                    mapped_line = mapped_line.replace(op, svg_op)
                                path_cmd.append(mapped_line)
                        if path_cmd:
                            d_string = " ".join(path_cmd)
                            #cleanup multiple spaces
                            d_string = re.sub(r"\s+", " ", d_string).strip()

                            svg_elements.append((f'  <g transform="translate({translateX}, {translateY})">'))
                            svg_elements.append(f'    <path d="{d_string}" fill="{current_fill}" />')
                            svg_elements.append(f'  </g>')
                    i += 1

                svg_elements.append("</svg>")
                svg_output =  "\n".join(svg_elements)





                # print(StreamLines)
                
                with open("Outputs\\test.svg" , "w") as file:
                    file.write(svg_output)
                


                

            
    
    break





    
    
    # print(ContentList)
    # break



