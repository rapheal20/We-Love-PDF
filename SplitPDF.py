#This feature will take a pdf as input and split it into pages based on the users requirments and export as separate files 

import os
from helperfunctions import * 
import re
import zlib

def SplitPDF(PDFPath, splitPage):
    try:
        PDF = open(PDFPath, "rb")

        PDFSize = os.path.getsize(PDFPath) - 1
        PDFVersion = PDFVersionFunc(PDFPath)

        xrefResult = XrefTableFunc(PDFPath)

        if isinstance(xrefResult, tuple):
            AllXrefTable, XrefTableAddress = xrefResult
        else:
            AllXrefTable = xrefResult

            firstEntry = next(iter(AllXrefTable.values())) if AllXrefTable else 0
            firstOffset = firstEntry.get('offset', 0) if isinstance(firstEntry, dict) else firstEntry
            XrefTableAddress = [firstOffset] if AllXrefTable else [0]

        if isinstance(XrefTableAddress, list) and XrefTableAddress:
            XrefTableAddress = XrefTableAddress[-1]

        XrefTable = AllXrefTable

        PDF.seek(0)
        if re.search(rb'/Encrypt\s+\d+\s+\d+\s+R|/Encrypt\s*<<', PDF.read()):
            raise ValueError("This PDF is encrypted. Remove the encryption first.")

        validOffsets = []
        for entry in XrefTable.values():
            if entry.get('type') == "n": #only objects that really sit in the file
                validOffsets.append(entry['offset'])

        sortedOffsets = sorted(set(validOffsets))
        sortedOffsets.append(XrefTableAddress)

        objStmCache = {} #so every object stream is only decompressed once

        RootObjectID = RootObjectIDFunc(PDFPath)
        catalogObjectID = RootObjectID #Root and catalog are the same object
        
        buffer = GetObjectBytes(PDF, XrefTable, catalogObjectID, objStmCache)

        pagesRefMatch = re.search(rb'/Pages\s+(\d+)\s+(\d+)\s+R', buffer)
        numberOfPages = 0

        if pagesRefMatch:
            pagesObjectID = int(pagesRefMatch.group(1))
            pagesBuffer = GetObjectBytes(PDF, XrefTable, pagesObjectID, objStmCache)
            countMatch = re.search(rb'/Count\s+(\d+)', pagesBuffer)

            if countMatch:
                numberOfPages = int(countMatch.group(1))

        #print("Number of pages:", numberOfPages) #temporary test line
        
            countMatch = re.search(rb'/Count\s+(\d+)', pagesBuffer)
            
            if countMatch:
                numberOfPages = int(countMatch.group(1))

        pagesData = []

        #This is the stuff I need to store for each page.
        '''
        pageEntry = {"pageIndex": 0, #index
                    "objectID": (0, 0), #[ID, Generation]
                    "inheritedAttributes": {"MediaBox": [0, 0, 0, 0], "Rotate": 0 }, #Just extract
                    "directReferences": {"contents": [0], "resources": 6}, #Objet ID for /Contents streams, Object ID for /Resources 
                    "dependencyIDs": [0, 0, 0, 0] #list of all child Object IDs
                    }
        '''

        #This is the last part of the code but written as a separate function for ease
        def ExportPDFPart(partPages, outputFilename):
            if not partPages:
                return

            #These two are the starting 2 objects. After that the objects will be named from 3
            catalogID = 1
            pagesID = 2
            nextID = 3

            #Track mapped IDs: maps original page object IDs to new renumbered IDs
            idMap = {}
            pageRefs = []
            allDependencies = set()
            targetPageIDS = []

            for page in partPages:
                pageID = page["objectID"][0]
                targetPageIDS.append(pageID)
                idMap[pageID] = nextID
                pageRefs.append(f"{nextID} 0 R")
                allDependencies.update(page["dependencyIDs"])
                nextID += 1

            dependencyIDsToMap = []

            #This code is excluding the pages themselves from the dependency list
            for dependencyID in allDependencies:
                if dependencyID not in targetPageIDS:
                    dependencyIDsToMap.append(dependencyID)

            for pageID in dependencyIDsToMap:
                if pageID not in idMap:
                    idMap[pageID] = nextID
                    nextID += 1

            newXrefTable = {}

            #Join all kids with a space
            kidsArrayStr = " ".join(pageRefs)
            pageCount = len(partPages)

            #Generating /Catalog Object
            catalogBytes = (
                f"{catalogID} 0 obj\n" 
                f"<<\n" 
                f"  /Type /Catalog\n"
                f"  /Pages {pagesID} 0 R\n"
                f">>\n"
                f"endobj\n"
                ).encode("latin1")

            #Generating the /Pages Root object 
            pagesBytes = (
                f"{pagesID} 0 obj\n"
                f"<<\n"
                f"  /Type /Pages\n"
                f"  /Count {pageCount}\n"
                f"  /Kids [ {kidsArrayStr} ]\n"
                f">>\n"
                f"endobj\n"
                ).encode("latin1")

            #This function updates the objectIDs inside object headers and refs
            def replaceRefs(match):
                refID = int(match.group(1))
                genNum = match.group(2).decode('latin1')
                
                if refID in idMap:
                    return f"{idMap[refID]} {genNum} R".encode('latin1')
                return match.group(0)

            with open(outputFilename, "wb") as outputPDF:
                #standard header
                header = f"%PDF-{PDFVersion}\n%\xe2\xe3\xcf\xd3\n".encode('utf-8')
                outputPDF.write(header)

                #writing /catalog which is object 1
                newXrefTable[1] = outputPDF.tell()
                outputPDF.write(catalogBytes)

                #writing /pages root which is object 2
                newXrefTable[2] = outputPDF.tell()
                outputPDF.write(pagesBytes)

                #These are patternf for object extraction and ref replacements
                objectRefPattern = re.compile(rb'(\d+)\s+(\d+)\s+R')
                parentPattern = re.compile(rb'/Parent\s+\d+\s+\d+\s+R')

                #processing all objects now 
                allOldIDsToWrite = targetPageIDS + dependencyIDsToMap

                for oldID in allOldIDsToWrite:
                    newID = idMap[oldID]

                    objectBuffer = GetObjectBytes(PDF, XrefTable, oldID, objStmCache)

                    if not objectBuffer:
                        #the object is missing or free. I write an empty object so the numbering stays complete
                        objectBuffer = f"{newID} 0 obj\nnull\nendobj\n".encode('latin1')
                    else:
                        #Split into the dictionary part and the stream part. Only the dictionary part can be changed
                        streamMatch = re.search(rb'>>\s*stream', objectBuffer)
                        if streamMatch:
                            splitAt = streamMatch.start() + 2
                        else:
                            splitAt = len(objectBuffer)

                        dictionaryPart = objectBuffer[:splitAt]
                        streamPart = objectBuffer[splitAt:]

                        #changing into the new ID header
                        dictionaryPart = re.sub(rb'^\d+\s+\d+\s+obj', f"{newID} 0 obj".encode('latin1'), dictionaryPart)

                        #changing ref
                        dictionaryPart = objectRefPattern.sub(replaceRefs, dictionaryPart)
                        dictionaryPart = parentPattern.sub(f"/Parent {pagesID} 0 R".encode('latin1'), dictionaryPart)

                        objectBuffer = dictionaryPart + streamPart
                    
                    #write objects
                    newXrefTable[newID] = outputPDF.tell()
                    outputPDF.write(objectBuffer)

                xrefOffset = outputPDF.tell()
                outputPDF.write(b"xref\n")
                totalObjects = len(newXrefTable) + 1
                outputPDF.write(f"0 {totalObjects}\n".encode("latin1"))
                outputPDF.write((b"0000000000 65535 f \n"))

                for i in range(1, totalObjects):
                    offset = newXrefTable[i]
                    outputPDF.write(f"{offset:010d} 00000 n \n".encode("latin1"))

                trailerBytes = (
                    f"trailer\n"
                    f"<<\n"
                    f"  /Size {totalObjects}\n"
                    f"  /Root {catalogID} 0 R\n"
                    f">>\n"
                    f"startxref\n"
                    f"{xrefOffset}\n"
                    f"%%EOF\n"
                    ).encode("latin1")

                outputPDF.write(trailerBytes)

        def pageParser(currentObjectID):    
            pagesIDGenList = []

            buffer = GetObjectBytes(PDF, XrefTable, currentObjectID, objStmCache)
            
            kidsIndex = buffer.find(b"/Kids")

            if kidsIndex == -1:
                return 

            startBracket = buffer.find(b"[", kidsIndex)
            endBracket = buffer.find(b"]", startBracket)

            kidsList = buffer[startBracket + 1 : endBracket].split()

            for i in range(len(kidsList)):
                if kidsList[i] == b"R":
                    objectID = int(kidsList[i-2].decode('latin1'))
                    objectGen = int(kidsList[i-1].decode('latin1'))
                    pagesIDGenList.append([objectID, objectGen])

            for pages in pagesIDGenList:
                pageID = pages[0]
                pageGen = pages[1]

                buffer = GetObjectBytes(PDF, XrefTable, pageID, objStmCache)
                if not buffer:
                    continue

                contentIndex = buffer.find(b"/Contents")
                subkidsIndex = buffer.find(b"/Kids")

                if contentIndex != -1:
                    #MediaBox Extraction
                    MediaBoxList = []
                    MediaBoxIndex = buffer.find(b"/MediaBox")

                    if MediaBoxIndex !=-1:
                        startBracket = buffer.find(b"[", MediaBoxIndex)
                        endBracket = buffer.find(b"]", startBracket)

                        MediaBoxByteList = buffer[startBracket + 1 : endBracket].split()

                        for value in MediaBoxByteList:
                            MediaBoxList.append(int(float(value.decode('latin1'))))

                        if not MediaBoxList or len(MediaBoxList) != 4:
                            MediaBoxList = [0, 0, 612, 792]

                    #Rotate
                    Rotate = 0 #This is the default rotate 

                    #contents
                    contentsMatch = re.search(rb'/Contents\s+(\d+)\s+\d+\s+R', buffer)

                    if not contentsMatch:
                        contentsMatch = re.search(rb'/Contents\s+(\d+)', buffer)

                    if contentsMatch:
                        contentObjectID = int(contentsMatch.group(1))
                    else: 
                        contentObjectID = None

                    #resources
                    resourcesPattern = re.compile(rb'/Resources\s+(\d+)')
                    resources = resourcesPattern.search(buffer)
                    if resources:
                        resourcesObjectID = int(resources.group(1))
                    else:
                        resourcesObjectID = None

                    #dependencyIDs: For this I would need to implement a recursive depth first search algorithm 
                    #I will start by adding the pages object ID to the queue
                    #if there are ids in queue 
                    #I will go to one objects id and repeat the process while also popping it out 

                    def dependencyCollecter(pageID):
                        pageID = int(pageID)
                        visitedIDs = []
                        dependencies = []
                        processing = [pageID]

                        while processing:                      
                            currentID = processing.pop()

                            if currentID in visitedIDs:
                                continue

                            visitedIDs.append(currentID)
                            dependencies.append(currentID)

                            buffer = GetObjectBytes(PDF, XrefTable, currentID, objStmCache)

                            streamMatch = re.search(rb'>>\s*stream', buffer)
                            if streamMatch:
                                buffer = buffer[:streamMatch.start() + 2]
                            
                            parentPattern = re.compile(rb'/Parent\s+\d+\s+\d+\s+R')
                            cleanedBytes = parentPattern.sub(b'', buffer)

                            objectPattern = re.compile(rb'(\d+)\s+(\d+)\s+R')
                            objectsRawBytes = objectPattern.findall(cleanedBytes)

                            for objectIDbytes, _ in objectsRawBytes:
                                refID = int(objectIDbytes)
                                if refID != currentID and refID not in visitedIDs:
                                    processing.append(refID)

                        return dependencies

                    dependencies = dependencyCollecter(pageID)

                    pageEntry = {
                    "pageIndex": len(pagesData) + 1, #index
                    "objectID": [pageID, pageGen], #[ID, Generation]
                    "inheritedAttributes": {"MediaBox": MediaBoxList, "Rotate": Rotate}, #Just extract
                    "directReferences": {"contents": contentObjectID, "resources": resourcesObjectID}, #Objet ID for /Contents streams, Object ID for /Resources 
                    "dependencyIDs": dependencies #list of all child Object IDs
                    }
                    
                    pagesData.append(pageEntry)

                elif subkidsIndex != -1:
                    pageParser(pageID)

        catBuffer = GetObjectBytes(PDF, XrefTable, catalogObjectID, objStmCache)

        pagesMatch = re.search(rb'/Pages\s+(\d+)\s+\d+\s+R', catBuffer)

        if pagesMatch:
            pagesObjID = int(pagesMatch.group(1))
            pageParser(pagesObjID)

        #print("Pages found:", len(pagesData))

        if not pagesData:
            raise ValueError("No pages were found. The file may be damaged or not supported.")

        numberOfPages = len(pagesData) #trust the pages I really found, not the /Count number

        if splitPage < 2 or splitPage > numberOfPages:
            raise ValueError(f"splitPage must be between 2 and {numberOfPages}")

        #Now I will get the user split page input
        #extract the target pages data frm pagesData
        #Map old source IDS to new IDs eg 14 to 1
        #Rewrite all indirect references in the file and track the new byte offsets
        #lastly build the new xreftable and trailer
        #These steps will be done for both of the division

        #user input of number number. The splitPage will go into the second part.
        #splitPage = 3 means split at the 3rd page so it will go in the second part
        #I will add more spliting when making the UI
        #Index starts at 1
        part1Index = splitPage - 1
        part2Index = numberOfPages

        part1Pages = pagesData[:part1Index]
        part2Pages = pagesData[part1Index:part2Index]

        #I will now get the objects needed for each part. I amd doing for part 1
        #requiredObjectIDS = set() #using datatype set so the list doesn't have repeated values 
        #pageObjectIDs = []

        PDFName = os.path.basename(PDFPath).split(".")[0]

        ExportPDFPart(part1Pages, f"Outputs/{PDFName}_Part1.pdf")
        ExportPDFPart(part2Pages, f"Outputs/{PDFName}_Part2.pdf")

        PDF.close()
    except:
        print("Error")  
        

SplitPDF("Inputs/sample-local-pdf.pdf", 2)