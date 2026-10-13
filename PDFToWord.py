#This function converts a PDF file to a .docs 
#Coded by Anael

import os 
import re 
import zlib
from helperfunctions import *

def PDFToWord(PDFPath):
    PDF = open(PDFPath, "rb")

    PDFSize = os.path.getsize(PDFPath)

    PDFVersion = PDFVersionFunc(PDFPath)

    XrefTable, XrefTableAddress = XrefTableFunc(PDFPath)

    RootObjectID = RootObjectIDFunc(PDFPath)

    RootObjectLocation = XrefTable[RootObjectID]

    PDF.seek(RootObjectLocation)
    buffer = PDF.read()

    CatalogObjectID = RootObjectID

    catalogObjectLocation = XrefTable[CatalogObjectID]

    PDF.seek(catalogObjectLocation)
    buffer = PDF.read(1024)

    pagesRefMatch = re.search(rb'/Pages\s+(\d+)\s+(\d+)\s+R', buffer)

    if pagesRefMatch:
        pagesObjectID = int(pagesRefMatch.group(1))
        pagesObjectLocation = XrefTable[pagesObjectID]

        PDF.seek(pagesObjectLocation)
        pagesBuffer = PDF.read(1024)

        countMatch = re.search(rb'/Count\s+(\d+)', pagesBuffer)
        
        if countMatch:
            numberOfPages = int(countMatch.group(1))
        else:
            numberOfPages = 0
    else:
        numberOfPages = 0

    def pageParser(currentLocation):
        pagesIDGenList = []

        PDF.seek(currentLocation)
        buffer = PDF.read(2048)
        
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
                contentsPattern = re.compile(rb'/Contents\s+(\d+)')
                contents = contentsPattern.search(buffer)
            
                contentObjectID = int(contents.group(1))
            
                contentObjectLocation = XrefTable[contentObjectID]

                PDF.seek(contentObjectLocation)

                #get exact length of object: It sorts the Xreftable by the byte offsets in ascending order. Then find the next object and subtract.
                sortedOffsets = sorted(set(XrefTable.values()))
                sortedOffsets.append(XrefTableAddress)
                currentIndex = sortedOffsets.index(contentObjectLocation)
                endOffset = sortedOffsets[currentIndex + 1]
                objectLength = endOffset - contentObjectLocation

                contentBuffer = PDF.read(objectLength)

                #Step 3 onwards, implementation is unique for the work
                streamPattern = re.compile(rb'stream\r?\n(.*?)\s*endstream', re.DOTALL)

                streamData = streamPattern.search(contentBuffer)
                streamData = streamData.group(1)

                try:
                    decompressedStreamData = zlib.decompress(streamData)
                except:
                    decompressedStreamData = streamData

                print(decompressedStreamData)
                #Parsing all text operators (BT TJ Tj ET)
                '''
                BT = start text
                ET = end text 
                Tf = fonts 
                Td TD = next line 
                Tj = text string
                TJ = text from array 
                '''
                textBlockPattern = re.compile(rb'\bBT\b(.*?)\bET\b', re.DOTALL)
                TDPattern = re.compile(rb'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(Td|TD)')

                textBlocks = textBlockPattern.findall(decompressedStreamData)

                extractedElements = []

                for block in textBlocks:
                    TDcommands = re.findall(rb'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(Td|TD)', block)
                    for cmd in TDcommands:
                        xCoordinate = float(cmd[0])
                        yCoordinate = float(cmd[1])
                        extractedElements.append({"type": "position", "dx": xCoordinate, "dy": yCoordinate})

                    newlineCommands = re.findall(rb'\bT\*\b', block)
                    for _  in newlineCommands:
                        extractedElements.append({"type": "newline"})

                    TjCommands = re.findall(rb'\((.*?)\)\s*(Tj|\'|\")', block, re.DOTALL)
                    for cmd in TjCommands:
                        textBytes = cmd[0]
                        textContent = textBytes.decode("latin1")
                        extractedElements.append({"type": "text", "content": textContent})
                        
                    TJArrayCommands = re.findall(rb'\[(.*?)\]\s*TJ', block, re.DOTALL)
                    for cmd in TJArrayCommands:
                        innerStrings = re.findall(rb'\((.*?)\)', cmd, re.DOTALL)
                        for s in innerStrings:
                            textContent = s.decode('latin1')
                            extractedElements.append({"type": "text", "content": textContent})

            elif subkidsIndex != -1:
                pageParser(pageLocation)


    pageParser(pagesObjectLocation)

PDFToWord("Inputs/file-example_PDF_500_kB.pdf")
