#This function will take a scanned document/pdf as input and run best possible ocr on it and return it as a searchable pdf 
#For OCR, I am gonna use pytesseract which is a python wrapper for Googe's Tesseract OCR engine
#Rest of the implementation is from other funcs like powerpoint

import os
import io
import tempfile
from PIL import Image
import pytesseract
from CommonFunctionsForDocs import parse_pdf_to_spans
from helperfunctions import *

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def OCRPDFFunc(PDFPath):
    try:
        extractedElements, firstBox = parse_pdf_to_spans(PDFPath)

        extractedText = ""
        imageCount = 0

        for element in extractedElements:
            if element.get('type') == 'image':
                imageBytes = element.get('data')
                if imageBytes:
                    imageCount += 1
                    img = Image.open(io.BytesIO(imageBytes))
                
                    pageText = pytesseract.image_to_string(img)
                    extractedText += f"Image {imageCount} \n" + pageText + "\n\n"

        if not extractedText.strip():
            extractedText = "No extractable image layers found for OCR."

        TEMP_DIR = tempfile.gettempdir() 

        PDFName = os.path.basename(PDFPath).split(".")[0]
        output_filename = f"{PDFName}-text.txt"
        output_path = os.path.join(TEMP_DIR, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
                f.write(extractedText)

        return [output_path]
    
    except Exception as e:
        raise e
    
#OCRPDFFunc("Inputs/scanned document example 2.pdf")