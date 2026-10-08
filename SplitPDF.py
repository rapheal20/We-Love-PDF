#This feature will take a pdf as input and split it into pages based on the users requirments and export as separate files 

import os
from helperfunctions import * 
import re

PDFPath = "Inputs/file-example_PDF_500_kB.pdf"

PDF = open(PDFPath, "rb")

PDFSize = os.path.getsize(PDFPath) - 1

PDFVersion = PDFVersion(PDFPath)

XrefTable, XrefTableAddress = XrefTable(PDFPath)

RootObjectID = RootObjectID(PDFPath)

RootObjectLocation = XrefTable[RootObjectID]

PDF.seek(RootObjectLocation)
buffer = PDF.read()

catalogIndex = buffer.find(b"/Type/Catalog/Pages ")

index = 0
catalogObjectID = "" 
while chr(buffer[catalogIndex+20+index]) not in delimiterList:
    if catalogIndex+20+index > len(buffer):
        break
    catalogObjectID += chr(buffer[catalogIndex+20+index])
    index += 1

catalogObjectID = int(catalogObjectID)

catalogObjectLocation = XrefTable[catalogObjectID]

PDF.seek(catalogObjectLocation)
buffer = PDF.read(1024)

countIndex = buffer.find(b"/Count ")

index = 0
numberOfPages = "" 
while chr(buffer[countIndex+index+7]) not in delimiterList:
    if countIndex+index+7 > len(buffer):
        break
    numberOfPages += chr(buffer[countIndex+index+7])
    index += 1

pagesData = []

#This is the stuff I need to store for each page.
'''
pageEntry = {"pageIndex": 0, #index
             "objectID": (0, 0), #[ID, Generation]
             "inheritedAttributes": {"MediaBox": [0, 0, 0, 0], "Rotate": 0 }, #Just extract
             "directReferences": {"contents": [0], "resources": 6}, #Objet ID for /Contents streams, Object ID for /Resources 
             "dependencyIds": [0, 0, 0, 0] #list of all child Object IDs
             }
'''
             
def pageParser(currentLocation):    
    pagesIDGenList = []

    PDF.seek(currentLocation)
    buffer = PDF.read(1024)
    
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

        pageLocation = XrefTable[pageID]
        PDF.seek(pageLocation)
        buffer = PDF.read(1024)

        contentIndex = buffer.find(b"/Contents")
        subkidsIndex = buffer.find(b"/Kids")

        if contentIndex != -1:
            #MediaBox Extraction
            MediaBoxList = []
            MediaBoxIndex = buffer.find(b"/MediaBox")

            if MediaBoxIndex !=-1:
                startBracket = buffer.find(b"[", MediaBoxIndex)
                endBracket = buffer.find(b"]", startBracket)

                MediaBoxByteList = buffer[startBracket + 1 : endBracket]
                MediaBoxByteList = MediaBoxByteList.split()

                i = 0 
                for i in range(len(MediaBoxByteList)):
                    MediaBoxList.append(int(MediaBoxByteList[i].decode('latin1')))

                if not MediaBoxList:
                    MediaBoxList = [0, 0, 612, 792] #Default mediabox

            #Rotate
            Rotate = 0 #This is the default rotate 

            #contents
            contentsPattern = re.compile(rb'/Contents\s+(\d+)')
            contents = contentsPattern.search(buffer)
            if contents:
                contentObjectID = int(contents.group(1))
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

                sortedOffsets = sorted(set(XrefTable.values()))
                sortedOffsets.append(XrefTableAddress)

                while processing:                      
                    currentID = processing.pop()

                    if currentID in visitedIDs:
                        continue

                    visitedIDs.append(currentID)
                    dependencies.append(currentID)

                    startOffset = XrefTable[currentID]
                    currentIndex = sortedOffsets.index(startOffset)
                    endOffset = sortedOffsets[currentIndex + 1]
                    length = endOffset - startOffset

                    PDF.seek(startOffset)
                    buffer = PDF.read(length)

                    parentPattern = re.compile(rb'/Parent\s+\d+\s+\d+\s+R')
                    cleanedBytes = parentPattern.sub(b'', buffer)

                    objectPattern = re.compile(rb'(\d+)\s+(\d+)\s+R')
                    objectsRawBytes = objectPattern.findall(cleanedBytes)

                    for objectIDbytes, objectGenBytes in objectsRawBytes:
                        refID = int(objectIDbytes)
                        if refID != currentID and refID not in visitedIDs:
                            processing.append(refID)

                return dependencies

            dependencies = dependencyCollecter(pageID)

            pageEntry = {"pageIndex": len(pagesData), #index
             "objectID": [pageID, pageGen], #[ID, Generation]
             "inheritedAttributes": {"MediaBox": MediaBoxList, "Rotate": Rotate}, #Just extract
             "directReferences": {"contents": contentObjectID, "resources": resourcesObjectID}, #Objet ID for /Contents streams, Object ID for /Resources 
             "dependencyIds": dependencies #list of all child Object IDs
            }
            
            pagesData.append(pageEntry)

        elif subkidsIndex != -1:
            pageParser(pageLocation)

pageParser(catalogObjectLocation) #This will make the list pagesData which will have all data required for each page

#print(pagesData)

#Now I will get the user split page input
#extract the target pages data frm pagesData
#Map old source IDS to new IDs eg 14 to 1
#Rewrite all indirect references in the file and track the new byte offsets
#lastly build the new xreftable and trailer
#These steps will be done for both of the division

PDF.close() 