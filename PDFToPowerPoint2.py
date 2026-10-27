#This function converts a PDF file to a .docs 
#Coded by Anael


import os 
import base64
import io
from helperfunctions import *
import unicodedata
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from CommonFunctionsForDocs import *

# from docx import Document 
# from docx.shared import Pt, RGBColor; import unicodedata; from docx.opc.constants import RELATIONSHIP_TYPE as RT; from docx.oxml import OxmlElement; from docx.oxml.ns import qn
# from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image


'''
Using the PDFToWord Function to do the conversion
'''

# pdf1 = "Inputs\\emaar1.pdf"
pdf1 = "Inputs\\Dickinson_Sample_Slides.pdf"

def PDFToPowerPoint(PDFPath):

    extractedElements, firstBox = parse_pdf_to_spans(PDFPath)

    def addPPTXRun(para, span,text):
        #run is a python-pptx function that represents a portion of text that has same formattin etc
        #para is also a feature of python-pptx, represents one paragraph

        run = para.add_run() #creates new text run inside the PP para
        run.text = text # assigns the text to the run
        family, bold, italic = fontStyle(span.get('font'))
        #assigns the pdf text properties to the run
        run.font.name = family
        run.font.sizr = Pt(max(8, span.get('size', 11)))
        run.font.bold = bold
        run.font.italic = italic
        if span.get('color') and span['color'] != (0,0,0) and min(span['color']) < 240:
            run.font.color.rgb = RGBColor(*span['color'])
        if span.get('under') or span.get('link'):
            run.font.underline = True 
        else:
            run.font.underline = None

        if span.get('link'):
            run.hyperlink.address = span['link']


    def PPTXBuilder(spans, firstBox, PDFPath):
        #============Initializing the PPTX============ 
        prs = Presentation()
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(7.5)

        #Dimensions in points
        slideWidth_PTS = 720
        slideHeight_PTS = 540
    
        if firstBox:
            pdf_W = firstBox[2] - firstBox[0]
            pdf_H = firstBox[3] - firstBox[1]
            if pdf_W > 0:
                scale_X = slideWidth_PTS / pdf_W
            else:
                scale_X = 0

            if pdf_H > 0:
                scale_Y = slideHeight_PTS / pdf_H
            else:
                scale_Y = 0
        else:
            scale_X = 1
            scale_Y = 1

        slide = None
        tf = None


        for span in spans:
            if span.get('type') == 'pageStart' or span.get('page'):
                #Adds a new blank slide
                slide = prs.slides.add_slide(prs.slide_layouts[6])
                tf = None
                continue

            if slide is None:
                continue

            if span.get('type') == 'image':
                try:
                    img_X = min(max(0, span.get('x', 0) * scale_X), slideWidth_PTS - 100)
                    img_Y = min(max(0, slideWidth_PTS - span.get('Y', 0) * scale_Y), slideHeight_PTS - 100)
                    # subtracting from height beacuse PDF has 0 as bottom left corner and Powerpoint has it at top left corner
                    img_W = min(span.get('w', 100)*scale_X , 400)

                    slide.shapes.add_picture(
                        io.BytesIO(span['data']),
                        left=Pt(img_X),
                        top=Pt(img_Y),
                        width=Pt(img_W)
                    )
                except Exception:
                    #skips that image
                    pass
                continue

            text = span.get('text', '').strip()
            if not text:
                #skips any blank values
                continue

            if tf is None:
                txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(8.4), Inches(5.8))
                tf.word_wrap = True
                para = tf.paragraph[0]
            else:
                para = tf.add_paragraph()

            addPPTXRun(para, span, text)


        PDFName = os.path.basename(PDFPath).split(".")[0]
        
        outputPath = f"Outputs/{PDFName}.pptx"

        os.makedirs(os.path.dirname(outputPath) or ".", exist_ok=True)
        prs.save(outputPath)
        print("done")

    PPTXBuilder(extractedElements, firstBox, PDFPath)

PDFToPowerPoint(pdf1)