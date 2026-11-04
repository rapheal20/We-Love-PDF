from helperfunctions import *
import tempfile

pdf1 = "Inputs\\file-example_PDF_500_kB.pdf"
# pdf1 = "Inputs\\file-example_PDF_1MB.pdf"
# pdf1 = "Inputs\\emaar1.pdf"

def AddPageNumbers(pdf1):
    PDF1 = open(pdf1, "rb")

    PDF1Data = PDF1.read()
    PDF1String = PDF1Data.decode("latin1")

    xref1, add = XrefTableFunc(pdf1)
    if isinstance(xref1, tuple):
        XrefTable, add = xref1
    else:
        XrefTable = xref1

    decompressedObjs = {}

    RootID = RootObjectIDFunc(pdf1)

    PDF_Pages, trash, PDF_Parent = FindParentsandKids(PDF1, XrefTable,RootID ,PDF1String, decompressedObjs)


    Pdf1_highestID = max(XrefTable.keys()) if XrefTable else 0
    fontObjID = int(Pdf1_highestID) +1
    fontObjStr = f"\n{fontObjID} 0 obj\n<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>\nendobj\n"

    PDF1_Objs = ObjectExtraction(PDF1, PDF1String, XrefTable, decompressedObjs)

    for PG_OBJ in PDF1_Objs:
        if PG_OBJ["OriginalID"] == PDF_Pages[0]:
            content = PG_OBJ["Content"]
            size = re.search(r"/\s*MediaBox\s*\[(\d+\.\d+|\d+) (\d+\.\d+|\d+) (\d+\.\d+|\d+) (\d+\.\d+|\d+)\]", content, flags=re.IGNORECASE)
            width = float(size.group(3)) - float(size.group(1))
            NumberX = width - 100

    NewObj = {}
    pageNo = 0
    streamID = fontObjID
    for pageID in (PDF_Pages):
        pageNo += 1
        textContentStream = f"BT 0 0 0 rg /PageNumFont 10 Tf {NumberX} 50 Td (Page {pageNo}) Tj ET"
        streamID += 1
        streamObjStr = (
            f"\n{streamID} 0 obj\n"
            f"<</Length {len(textContentStream)} >>\n"
            f"stream\n"
            f"{textContentStream}"
            f"\nendstream\nendobj\n"
        )
        NewObj[pageID]= {"ID" : streamID, "content" : streamObjStr}

    NewHeader = Make_Header(PDF1String)
    editedRes = {}

    NEW_PDF_STR = NewHeader + "\n\n"
    for ObjData in (PDF1_Objs):
        OBJ_ID = ObjData["OriginalID"]
        if OBJ_ID in PDF_Pages:
            content = ObjData["Content"]
            singleResources = (re.search(r"/\s*Resources (\d+) 0 R", content, flags=re.IGNORECASE))
            if singleResources:
                resourcesID = singleResources.group(1)
                if resourcesID not in editedRes.keys():
                    editedRes[resourcesID] = content
                    resObjOffset = XrefTable[int(resourcesID)]["offset"]
                    resObjEnd = re.search(objectEndString, PDF1String[resObjOffset:], flags=re.IGNORECASE).end() + resObjOffset
                    resObj = PDF1String[resObjOffset:resObjEnd]
                    singleFont = re.search(r"/Font\s*(\d+) 0 R", resObj, flags=re.IGNORECASE)
                    if singleFont:
                        fontID = singleFont.group(1)
                        fontObjStart = XrefTable[int(fontID)]["offset"]
                        fontObjEnd = re.search(objectEndString, PDF1String[fontObjStart:], flags=re.IGNORECASE).end() + fontObjStart
                        fontObj = PDF1String[fontObjStart:fontObjEnd]

                        fontend = (re.search(">>", fontObj, flags=re.IGNORECASE)).start()
                        newFontObj = fontObj[:fontend]
                        newFontObj += f" /PageNumFont {fontObjID} 0 R "
                        newFontObj += fontObj[fontend:]
                        editedRes[int(fontID)] = newFontObj
            else:
                multipleResources = (re.search(r"/\s*Resources\s*<<", content, flags=re.IGNORECASE))
                if multipleResources:
                    fontFinder = re.search(r"/Font\s*<<",content, flags=re.IGNORECASE)
                    if fontFinder:
                        newObj = content[:fontFinder.end()]
                        newObj += f" /PageNumFont {fontObjID} 0 R "
                        newObj += content[fontFinder.end():]
                    else:
                        newObj = content[:multipleResources.end()]
                        newObj += f"/Font << /PageNumFont {fontObjID} 0 R >>"
                        newObj += content[multipleResources.end():]
                    content = newObj

            singleContent = re.search(r"/Contents (\d+) 0 R", content, flags=re.IGNORECASE)
            if singleContent:
                contentStart = int(singleContent.start())
                contentEnd = int(singleContent.end())
                NewContent = content[:contentStart]
                NewContent += f"/Contents [{singleContent.group(1)} 0 R {NewObj[OBJ_ID]["ID"]} 0 R]"
                NewContent += content[contentEnd:]  + "\n\n"
            else:
                multipleContent = re.search(r"/Contents\s*\[", content, flags=re.IGNORECASE)
                if multipleContent:
                    ContentEnd = (re.search("]", content[multipleContent.start():])).start() + multipleContent.start()
                    NewContent = content[:ContentEnd]
                    NewContent += f" {NewObj[OBJ_ID]["ID"]} 0 R "
                    NewContent += content[ContentEnd:]
                else:
                    NewContent = content
            NEW_PDF_STR += NewContent
        else:
            if ObjData["OriginalID"] in editedRes.keys():
                NEW_PDF_STR += editedRes[ObjData["OriginalID"]] + "\n\n"
            else:
                NEW_PDF_STR += ObjData["Content"] + "\n\n"


    NEW_PDF_STR += fontObjStr
    for PageNumObj in NewObj.values():
        NEW_PDF_STR += PageNumObj["content"] + "\n"

    NewXref, ObjNo = Make_Xref(NEW_PDF_STR)
    NEW_PDF_STR += NewXref

    byteOffset = NEW_PDF_STR.rindex("xref")
    trailerObj = f"\ntrailer\n<<\n/Size {ObjNo +1}\n/Root {RootID} 0 R\n>>\nstartxref\n{byteOffset}\n%%EOF"

    NEW_PDF_STR += trailerObj
    encodedPDF = NEW_PDF_STR.encode("latin1")
    
    
    TEMP_DIR = tempfile.gettempdir()
    PDFName = os.path.basename(pdf1).split(".")[0]
    output_path = os.path.join(TEMP_DIR, f"{PDFName}-AddedPageNum.pdf")
    with open(output_path , "wb") as file:
        file.write(encodedPDF)
    
    print("done")

(AddPageNumbers(pdf1))