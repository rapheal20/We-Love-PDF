'''
This function read all the pdf files given and merges them in the order selected.
The function will take the pdfs from inputs folder and a dict which will have file name as key and sequence number as value.
Then it will READ the pdfs in the order and WRITE to a new file

Universal List Format For Each PDF
e.g

    PDF_Data = [
        {"OriginalID" : 2,
        "NewID" : 12,
        "Content" : 2345}
    ]

BASIC DESIGN CHOICES
- cannot open PDF in "r" mode because of different types of data, so we use "rb" this opens in binary
- here we use .finditer instead of .findall as .finditer waits for one of the ouputs to worked on and then moves on to the next so memery efficint

PDF Version 1.7:
Whats New:
- Object streams = /Type /ObjStm - these are many small objects packed into 1
- Cross-refernce streams = /Type /XRef = the xref table is stored as a compressed binary stream
'''
import re
from helperfunctions import *


pdf3 = "Inputs\\file-example_PDF_1MB.pdf"
pdf4 = "Inputs\\file-example_PDF_500_kB.pdf"
# pdf3 = "Inputs\\emaar1.pdf"
# pdf4 = "Inputs\\emaar.pdf"

def MergePDFFunc(*pdfs):
    try:
        def FindParentsandKids(PDF, XrefTable, RootID, PDF_Data, DecompressedObjs):
            IDS_to_Remove = [RootID]
            ParentFindStr = r"\s*/\s*Pages\s*(\d+)\s*0\s*R"
            ParentID = int((re.search(ParentFindStr, GetObjectBytes(PDF, XrefTable, RootID, DecompressedObjs).decode('latin1'), flags=re.IGNORECASE)).group(1))
            IDS_to_Remove.append(ParentID)
            try:
                ParentBody = GetObjectBytes(PDF, XrefTable, ParentID, DecompressedObjs)
                ParentBody = ParentBody.decode('latin1')
                KidStart = (re.search(r"/\s*Kids", ParentBody, flags=re.IGNORECASE)).start()
            except:
                ParentBodyStart = (re.search(fr"\b{ParentID}\s+0\s+obj", PDF_Data, flags=re.IGNORECASE)).start()
                ParentBodyEnd = (re.search(objectEndString, PDF_Data[ParentBodyStart:], flags=re.IGNORECASE)).end() + ParentBodyStart  
                ParentBody = PDF_Data[ParentBodyStart:ParentBodyEnd]
                KidStart = (re.search(r"/\s*Kids", ParentBody, flags=re.IGNORECASE)).start()

            #  searches for the kids in the parent obj and appends in the list
            KidsFindString = r"(\d+)\s*0\s*R"
            
            KidEnd = (re.search("]", ParentBody[KidStart:], flags=re.IGNORECASE)).end() + KidStart
            Kids = re.finditer(KidsFindString, ParentBody[KidStart:KidEnd], flags=re.IGNORECASE)

            Kids_List = []
            for kid in Kids:
                Kids_List.append(int(kid.group(1)))

            # finds the total number of pages
            PageCountString = r"/\s*Count\s*(\d+)"
            PageCount = (re.search(PageCountString, ParentBody, flags=re.IGNORECASE)).group(1)

            # if the extracted kids donot match with the count, then if means PDF has subParents, so then it goes to each subparent and and extracts its kids
            if int(PageCount) != (len(Kids_List)): 
                def ExpandKids(KidIDs):
                    KidPages = []
                    for kidID in KidIDs:
                        KidObj = GetObjectBytes(PDF, XrefTable, kidID, DecompressedObjs)
                        KidObj = KidObj.decode('latin1')

                        KidMatch = re.search(r"/\s*Kids", KidObj, flags=re.IGNORECASE)
                        if KidMatch is None:            # not a sub-parent, it's a page itself
                            KidPages.append(kidID)
                            continue
                        IDS_to_Remove.append(kidID)

                        KidStart = KidMatch.start()
                        KidEnd = (re.search("]", KidObj[KidStart:], flags=re.IGNORECASE)).end() + KidStart                       
                        SubKids = re.finditer(KidsFindString, KidObj[KidStart:KidEnd], flags=re.IGNORECASE)
                        # a sub-parent can hold more sub-parents, so it calls itself
                        KidPages += ExpandKids([int(SubKid.group(1)) for SubKid in SubKids])
                    return KidPages
                KidPages = ExpandKids(Kids_List)
                
                # replaces the subParents with the new pages list
                Kids_List = KidPages
            return Kids_List, IDS_to_Remove, ParentID

        STREAM_RE = re.compile(r"[>\s]stream(?:\r\n|\n|\r)", re.ASCII)
        SHIFT_RE = re.compile(r"\b(\d+)(\s+\d+\s+(?:R|obj)\b)", re.ASCII)

        def SplitStream(objStr):
            m = STREAM_RE.search(objStr)
            if m:
                return objStr[:m.start() + 1], objStr[m.start() + 1:]
            return objStr, ""

        def ShiftIDs(text, offset):
            if offset == 0:
                return text
            return SHIFT_RE.sub(lambda m: f"{int(m.group(1)) + offset}{m.group(2)}", text)

        # Function for Changing the Parent of each OBJ (every /Parent pointing to a removed Pages node)
        def ParentIDChange(PDFstr, OldParentIDs, NewParentID):
            return re.sub(r"/Parent\s+(\d+)\s+0\s+R", lambda m: f"/Parent {NewParentID} 0 R" if int(m.group(1)) in OldParentIDs else m.group(0), PDFstr, flags=re.ASCII)
        #makes the new parent object
        def Make_Parent(newKids, NewParentID):
            #forms the new kids string
            kidsStr = "/Kids[ "
            # iterates through the new kids and corrects the format
            for i in newKids:
                kidsStr += f"{i} 0 R " 
            # the rest of the formatting for the parent
            kidsStr += "]"
            newParent = f'\n{NewParentID} 0 obj\n<</Type/Pages\n' 
            newParent += f'{kidsStr}\n'  
            newParent += f'/Count {len(newKids)}>>\nendobj\n'

            return newParent

        bodies = []         # (body string, removed Pages ids after shifting) for each pdf
        allKids = []        # page ids of all pdfs in order
        idOffset = 0        # running total of the highest IDs of the previous pdfs
        firstString = None

        for path in pdfs:
            with open(path, "rb") as PDF:
                pdfString = PDF.read().decode("latin1")
                if firstString is None:
                    firstString = pdfString

                xref, add = XrefTableFunc(path)
                if isinstance(xref, tuple):
                    XrefTable, add = xref
                else:
                    XrefTable = xref

                # repairs the xref table (linearized pdfs): adds the objects it missed, fixes offsets which do not point to their object
                for found in re.finditer(r"\b(\d+)\s+\d+\s+obj\b", pdfString):
                    foundID = int(found.group(1))
                    entry = XrefTable.get(foundID)
                    if entry is None:
                        XrefTable[foundID] = {"type": "n", "offset": found.start()}
                    elif entry.get("type") == "n" and entry.get("offset", 0) > 0:
                        atOffset = re.match(r"\s*(\d+)\s+\d+\s+obj\b", pdfString[entry["offset"]:entry["offset"] + 30])
                        if atOffset is None or int(atOffset.group(1)) != foundID:
                            entry["offset"] = found.start()

                DecompressedObjs = {}
                Root = RootObjectIDFunc(path)
                Pages, RemoveIDS, Parent = FindParentsandKids(PDF, XrefTable, Root, pdfString, DecompressedObjs)
                highestID = max(XrefTable.keys()) if XrefTable else 0

                parts = []
                for objID, objData in XrefTable.items():
                    if objData.get("type") in ("n", "compressedInsideStream") and objData.get("offset") > 0 and objID not in RemoveIDS:
                        NewObj = GetObjectBytes(PDF, XrefTable, objID, DecompressedObjs)
                        NewObj = NewObj.decode('latin1').rstrip()
                        if NewObj.endswith("endobj"):       # objects out of object streams already carry one
                            NewObj = NewObj[:-6]
                        if re.search(r"/Type\s*/XRef|/Type\s*/ObjStm|/Linearized", NewObj[:400]):      # old linearization / xref stream objects are useless now
                            continue
                        head, tail = SplitStream(NewObj)
                        parts.append(("\n" + head, tail + " \nendobj\n"))

            objs = [(ShiftIDs(h, idOffset), t) for h, t in parts]
            allKids += [int(k) + idOffset for k in Pages]
            bodies.append((objs, {i + idOffset for i in RemoveIDS}))
            idOffset += highestID

        '''###### MAKING & INITIALIZING THE NEW PARENT & CATALOG OBJECT ######'''
        NewParentID = idOffset + 1
        parentObj = Make_Parent(allKids, NewParentID)
        combinedBodies = "".join(ParentIDChange(h, p, NewParentID) + t for objs, p in bodies for h, t in objs)        #making new catalog
        catalogObj = f'\n{NewParentID+1} 0 obj\n<</Type/Catalog/Pages {NewParentID} 0 R\n>>\nendobj'      

        #making new header
        headerObj = Make_Header(firstString)

        #forms a string of the new header, all pdfs, parent and catalog object
        CombinePDFStr = headerObj + combinedBodies + parentObj + catalogObj

        #making xref
        xreftable, ObjNumber = Make_Xref(objectFindString, CombinePDFStr)

        CombinePDFStr += xreftable

        #making trailer
        byteOffset = CombinePDFStr.rindex("xref")
        trailerObj = f"\ntrailer\n<<\n/Size {ObjNumber +1}\n/Root {NewParentID+1} 0 R\n>>\nstartxref\n{byteOffset}\n%%EOF"

        CombinePDFStr += trailerObj

        #encoding it back into latin1
        encodedPDF = CombinePDFStr.encode("latin1")

        PDFName = os.path.basename(pdfs[0]).split(".")[0]
        with open(f"AppOutputs\\{PDFName}-Merged.pdf" , "wb") as file:
            file.write(encodedPDF)

        return f"AppOutputs\\{PDFName}-Merged.pdf"
    except Exception as e:
        print(e)
        raise