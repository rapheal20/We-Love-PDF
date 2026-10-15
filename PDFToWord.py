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

                #Parsing all text operators (BT TJ Tj ET)
                '''
                BT = start text
                ET = end text 
                Tf = fonts 
                Td TD = text positions
                Tm = text Matrix for positioning
                Ts = text rise for superscripts sub scripts
                TL = line spacing
                Tr = Text rendering mode for hidden text
                Tj = text string
                TJ = text from array 
                '''
                textBlockPattern = re.compile(rb'\bBT\b(.*?)\bET\b', re.DOTALL)

                textBlocks = textBlockPattern.findall(decompressedStreamData)
                extractedElements = []

                for block in textBlocks:
                    blockElements = []

                    #Font details               
                    TfPattern = re.compile(rb'/([A-Za-z0-9\._\-]+)\s+(\d+\.?\d*)\s+Tf')
                    for match in TfPattern.finditer(block):
                        fontName, fontSize = match.groups()
                        blockElements.append((match.start(), {'type': 'font', 'name': fontName.decode('latin1'), 'size': float(fontSize)}))
 
                    #Text matrix (Tm) #(a, b, c, d, e, f)Tm . e f are the x and y cords
                    TmPattern = re.compile(rb'([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+([-\d\.eE+-]+)\s+Tm', re.DOTALL)
                    for match in TmPattern.finditer(block):
                        a, b, c, d, e, f = match.groups()
                        blockElements.append((match.start(), {'type': 'matrix', 'a': float(a), 'b': float(b), 'c': float(c), 'd': float(d), 'x': float(e), 'y': float(f)}))

                    #Text rise (Ts)
                    TsPattern = re.compile(rb'(-?\d+\.?\d*)\s+Ts')
                    for match in TsPattern.finditer(block):
                        blockElements.append((match.start(), {'type': "rise", 'value': float(match.group(1))}))

                    #Text leading (TL)
                    TLPattern = re.compile(rb'(-?\d+\.?\d*)\s+TL')
                    for match in TLPattern.finditer(block):
                        blockElements.append((match.start(), {'type': 'leading', 'value': float(match.group(1))}))

                    #Text rendering mode (Tr) #0 for normal text, 3 for invisible text 
                    TrPattern = re.compile(rb'(\d+)\s+Tr')
                    for match in TrPattern.finditer(block):
                        blockElements.append((match.start(), {'type': 'renderingMode', 'mode': float(match.group(1))}))              

                    #Text positions
                    TDPattern = re.compile(rb'(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(Td|TD)')
                    for match in TDPattern.finditer(block):
                        xOffset, yOffset, operator = match.groups()
                        blockElements.append((match.start(), {'type': 'position', 'dx': float(xOffset), 'dy': float(yOffset), 'operator': operator.decode('latin1')}))              

                    #Next line (Also known as T*)
                    TStarPattern = re.compile(rb'\bT\*\b')
                    for match in TStarPattern.finditer(block):
                        blockElements.append((match.start(), {'type': 'newline'}))

                    #Text (single text string)
                    TjPattern = re.compile(rb'(?:\((.*?)\)|<([0-9A-Fa-f\s]+)>)\s*(Tj|\'|\")', re.DOTALL)
                    for match in TjPattern.finditer(block):
                        literalString, HexString, operator = match.groups()

                        if literalString:
                            text = literalString.decode('latin1')
                            blockElements.append((match.start(), {'type': 'text', 'content': text}))
                        elif HexString:
                            text = HexString
                            blockElements.append((match.start(), {'type': 'text', 'content': text}))
                        
                    #text with arrays containing strings and numbers (Also known as TJ)
                    TJPattern = re.compile(rb'\[(.*?)\]\s*TJ', re.DOTALL)
                    for match in TJPattern.finditer(block):
                        TJs = match.group(1)

                        arrayItems = re.findall(rb'\((.*?)\)|<([0-9A-Fa-f\s]+)>|(-?\d+\.?\d*)', TJs, re.DOTALL)    
                        for each in arrayItems:
                            literal, hexItem, number = each

                            if literal: #literal text strings
                                text = literal.decode('latin1')
                                blockElements.append((match.start(), {'type': 'text', 'content': text}))
                            elif hexItem: #hex strings
                                text = hexItem
                                blockElements.append((match.start(), {'type': 'text', 'content': text}))
                            elif number: #spacing number
                                numberValue = float(number)       
                                blockElements.append((match.start(), {'type': 'spacing', 'value': float(numberValue)}))                     

                    blockElements.sort(key=lambda x: x[0]) #sorts everything in the block by the character position

                    for position, element in blockElements:
                        extractedElements.append(element)
                
                print(extractedElements)
            elif subkidsIndex != -1:
                pageParser(pageLocation)


    pageParser(pagesObjectLocation)

PDFToWord("Inputs/file-example_PDF_500_kB.pdf")

