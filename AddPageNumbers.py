from helperfunctions import *
import tempfile

pdf1 = "Inputs\\file-example_PDF_500_kB.pdf"

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
    # print(Pdf1_highestID)
    fontObjID = int(Pdf1_highestID) +1
    fontObjStr = f"\n{fontObjID} 0 obj\n<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>\nendobj\n"

    
    NewObj = {}
    pageNo = 0
    streamID = fontObjID
    for pageID in (PDF_Pages):
        pageNo += 1
        textContentStream = f"BT /PageNumFont 10 Tf 350 30 Td (Page {pageNo})"
        compressedStream = zlib.compress(textContentStream.encode("latin1"))

        streamID += 1
        streamObjStr = (
            f"\n{streamID} 0 obj\n"
            f"<</Length {len(compressedStream)} /Filter /FlateDecode>>\n"
            f"stream\n"
            f"{compressedStream}"
            f"\nendobj\n"
        )

        NewObj[pageID]= {"ID" : streamID, "content" : streamObjStr}

    PDF1_Objs = ObjectExtraction(PDF1String, XrefTable)

    NewHeader = Make_Header(PDF1String)


    editedRes = {}

    # print(PDF1_Objs)

    NEW_PDF_STR = NewHeader + "\n\n"
    for ObjData in (PDF1_Objs):
        OBJ_ID = ObjData["OriginalID"]
        if OBJ_ID in PDF_Pages:
            AlreadyMultiple = False
            content = ObjData["Content"]
            resources = (re.search(r"/\s*Resources (\d+) 0 R", content, flags=re.IGNORECASE))
            resourcesID = resources.group(1)
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
                    # print(newFontObj)

            singleContent = re.search(r"/Contents (\d+) 0 R", content, flags=re.IGNORECASE)
            if singleContent:
                contentStart = int(singleContent.start())
                contentEnd = int(singleContent.end())
                NewContent = content[:contentStart]
                NewContent += f"/Contents [{singleContent.group(1)} 0 R, {NewObj[OBJ_ID]["ID"]} 0 R]"
                NewContent += content[contentEnd:] + "endobj\n\n"
            # print(content)
            # print(NewContent)
            # break
            NEW_PDF_STR += NewContent + "\nendobj\n"

        else:
            if ObjData["OriginalID"] in editedRes.keys():
                NEW_PDF_STR += editedRes[ObjData["OriginalID"]] + "endobj\n\n"
                # print("Added")
            else:
                NEW_PDF_STR += ObjData["Content"] + "endobj\n\n"
                print(ObjData["Content"][:100])
                break

    for PageNumObj in NewObj.values():
        NEW_PDF_STR += PageNumObj["content"] + "\n"




    NewXref, ObjNo = Make_Xref(NEW_PDF_STR)

    NEW_PDF_STR += NewXref

    byteOffset = NEW_PDF_STR.rindex("xref")
    trailerObj = f"\ntrailer\n<<\n/Size {ObjNo +1}\n/Root {RootID} 0 R\n>>\nstartxref\n{byteOffset}\n%%EOF"
    # NewTrailer = 

    NEW_PDF_STR += trailerObj


    encodedPDF = NEW_PDF_STR.encode("latin1")
    
    
    # TEMP_DIR = tempfile.gettempdir()
    # PDFName = os.path.basename(pdf1).split(".")[0]
    # output_path = os.path.join(TEMP_DIR, f"{PDFName}-AddedPageNum.pdf")

    with open("test.pdf" , "wb") as file:
        file.write(encodedPDF)
    
    print("done")



    # with open("data.txt", "w", encoding="latin1") as file:
    #     file.write(NEW_PDF_STR)






            # if not resources:
            #     AlreadyMultiple = True

            # if not AlreadyMultiple:
            #     newRes = f"/Resources << /Font << /PageNumFont {fontObjID} 0 R >> >>"
            # startoffset = resources.end()
            # NewContent = (content[:startoffset+1]
            #               + f"PageNumFont {fontObjID} 0 R"
            #               + content[startoffset:])

            # print(NewContent)

            
        
    

    # print(NewObj)




        




    # print(PDF_Pages)





(AddPageNumbers(pdf1))