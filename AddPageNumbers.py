from helperfunctions import *

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

        NewObj[pageID] = streamObjStr

    PDF1_Objs = ObjectExtraction(PDF1String, XrefTable)

    NewHeader = Make_Header(PDF1String)


    editedRes = {}

    # print(PDF1_Objs)

    NEW_PDF_STR = NewHeader + "\n\n"
    for ObjData in (PDF1_Objs):
        if ObjData["OriginalID"] in PDF_Pages:
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
                    print(newFontObj)

            singleContent = re.search(r"/Contents (\d+) 0 R", content, flags=re.IGNORECASE)
            if singleContent:
                contentStart = int(singleContent.start()) - 1
                NewContent = content[:contentStart]
                NewContent += f"/Contents [{singleContent.group(1)} 0 R, {singleContent.group(1)} 0 R]"

        else:
            if ObjData["OriginalID"] in editedRes.keys():
                NEW_PDF_STR += editedRes[ObjData["OriginalID"]]
                print("Added")
            else:
                NEW_PDF_STR += ObjData["Content"]
                print("Added Same")




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