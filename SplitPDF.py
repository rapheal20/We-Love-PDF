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

numberOfPages = int(numberOfPages)

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

            pageEntry = {"pageIndex": len(pagesData) + 1, #index
             "objectID": [pageID, pageGen], #[ID, Generation]
             "inheritedAttributes": {"MediaBox": MediaBoxList, "Rotate": Rotate}, #Just extract
             "directReferences": {"contents": contentObjectID, "resources": resourcesObjectID}, #Objet ID for /Contents streams, Object ID for /Resources 
             "dependencyIDs": dependencies #list of all child Object IDs
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

#user input of number number. The splitPage will go into the second part.
splitPage = 3 
#Index starts at 1
part1Index = splitPage - 1
part2Index = numberOfPages 

part1Pages = pagesData[:part1Index]
part2Pages = pagesData[part1Index:part2Index]

#I will now get the objects needed for each part. I amd doing for part 1
requiredObjectIDS = set() #using datatype set so the list doesn't have repeated values 
pageObjectIDs = []

#These two are the starting 2 objects. After that the objects will be named from 3
catalogID = 1
pagesID = 2
nextID = 3

#Track mapped IDs: maps original page object IDs to new renumbered IDs
idMap = {}
pageRefs = []
allDependencies = set()
targetPageIDS = []

for page in part1Pages:
    pageID = page["objectID"][0]
    targetPageIDS.append(pageID)
    idMap[pageID] = nextID
    pageRefs.append(f"{nextID} 0 R")
    allDependencies.update(page["dependencyIDs"])

    nextID += 1

dependencyIDsToMap = []

#This code is excluding the pages themselves from the dependency list
for dependencyID in allDependencies:
    if dependencyID not in part1Pages:
        dependencyIDsToMap.append(dependencyID)

for pageID in dependencyIDsToMap:
    if pageID not in idMap:
        idMap[pageID] = nextID
        nextID += 1

newXrefTable = {}

sortedOffsets = sorted(set(newXrefTable.values()))

#Join all kis with a space
kidsArrayStr = " ".join(pageRefs)
pageCount = len(part1Pages)

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

with open("Outputs//WeLovePDF_Split.pdf", "wb") as outputPDF:
    #standard header
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
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

    #This function updates the objectIDs inside object headers and refs
    def replaceRef(match):
        refID = int(match.group(1))
        generationNumber = match.group(2)
        if refID in idMap:
            return f"{idMap[refID]} {generationNumber.decode('latin1')} R".encode('latin1')
        return match.group(0)

    #processing all objects now 
    allOldIDsToWrite = targetPageIDS + dependencyIDsToMap

PDF.close()  