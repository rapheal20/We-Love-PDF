#This feature will take a pdf as input and split it into pages based on the users requirments and export as separate files 

import os
from helperfunctions import * 

PDFPath = "Inputs/file-example_PDF_500_kB.pdf"

PDF = open(PDFPath, "rb")

PDFVersion = PDFVersion(PDFPath)

XrefTable = XrefTable(PDFPath)

RootObjectID = RootObjectID(PDFPath)

RootObjectLocation = XrefTable[RootObjectID]

PDF.seek(RootObjectLocation)

buffer = PDF.read()

print(buffer)

PDF.close()