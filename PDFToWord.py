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
                contentBuffer = PDF.read(4096)

                #Step 3 onwards, implementation is unique for the work
                streamPattern = re.compile(rb'stream\r?\n(.*?)\s*endstream', re.DOTALL)

                streamData = streamPattern.search(contentBuffer)
                streamData = streamData.group(1)

                try:
                    decompressedStreamData = zlib.decompress(streamData)
                except:
                    decompressedStreamData = streamData

                #Parsing all text operators (BT TJ Tj ET)
                textBlockPattern = re.compile(rb'\bBT\b(.*?)\bET\b', re.DOTALL)
                tjPattern = re.compile(rb'\((.*?)\)\s*Tj|<([0-9A-Fa-f]+)>\s*Tj')
                tjArrayPattern = re.compile(rb'\[(.*?)\]\s*TJ', re.DOTALL) #Also called TJ

                textBlocks = textBlockPattern.findall(decompressedStreamData)
                
                print(textBlocks)

            elif subkidsIndex != -1:
                pageParser(pageLocation)


    pageParser(pagesObjectLocation)

PDFToWord("Inputs/file-example_PDF_500_kB.pdf")
