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

pdf1 = "Inputs\\emaar1.pdf"

def PDFToWord(PDFPath):

    extractedElements, firstBox = parse_pdf_to_spans(PDFPath)

    print(extractedElements)
    # #Turns a PDF BaseFont like "ABCDEF+DejaVuSans-Bold" into (Word font name, bold, italic)
    # def fontStyle(base):
    #     if not base:
    #         return "Calibri", False, False
    #     base = re.sub(r"^[A-Z]{6}\+", "", base)
    #     low = base.lower()
    #     bold = any(k in low for k in ("bold", "black", "heavy"))
    #     italic = "italic" in low or "oblique" in low
    #     family = re.split(r"[-,]", base)[0]
    #     fl = family.lower()
    #     if any(k in fl for k in ("helvetica", "arial", "liberationsans")):
    #         family = "Arial"
    #     elif any(k in fl for k in ("times", "liberationserif")):
    #         family = "Times New Roman"
    #     elif any(k in fl for k in ("courier", "liberationmono")):
    #         family = "Courier New"
    #     elif fl.startswith("allandnone"):
    #         family = "Times New Roman"                                   #obfuscated name, not a real font: the body is Times-like
    #     else:
    #         family = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", family)   # DejaVuSans -> DejaVu Sans
    #     return family, bold, italic

    # #replay the PDF text operators so every piece of text knows its x, y, size and style
    # spans = []
    # x = y = adv = tc = 0.0
    # scale = 1.0          #font scale coming from the text matrix (many PDFs use "1 Tf" + a scaled Tm)
    # leading = 0.0
    # size = 11.0
    # base = None
    # moved = False
    # ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    # pageBox = firstBox = None
    # hidden, rise, color, pageLinks, pageRules, pageOpen = False, 0.0, (0, 0, 0), [], [], []
    # currentPageSpans = []
    # BULLETS = {'\u2022', '\u25aa', '\u25cf', '\u25e6', '\u2023', '\uf0b7'}
    # estW = lambda text, size: size * sum(0.28 if c == ' ' else 0.25 if c in "ilj.,;:'!|tfI()[]" else 0.8 if c in 'mwMW' else 0.67 if c.isupper() else 0.55 if c.isdigit() else 0.5 for c in text)
    # def groupLines(group):
    #     lines = []
    #     for s in sorted(group, key=lambda s: -s['y']):
    #         if lines and 'size' in s and 'size' in lines[-1][0] and abs(lines[-1][0]['y'] - s['y']) < (1.0 if min(s['size'], lines[-1][0]['size']) < 0.85 * max(s['size'], lines[-1][0]['size']) else 0.6) * max(s['size'], lines[-1][0]['size']): lines[-1].append(s)   #a smaller span (exponent, index) stays on its line
    #         else: lines.append([s])
    #     return [sorted(l, key=lambda s: s.get('ex', s['x'])) for l in lines]
    # def cellsOf(line):
    #     cells = []
    #     for s in line:
    #         p = cells[-1][-1] if cells else None
    #         if p and 'text' in s and 'text' in p and s['ex'] - p['ex'] - p['wid'] < 2 * s['size']: cells[-1].append(s)
    #         else: cells.append([s])
    #     return cells
    # def tableRuns(lines):
    #     rows = [cellsOf([s for s in l if s.get('text', 'x').strip()]) for l in lines]
    #     ok = [len(r) >= 2 and all('text' in c[0] for c in r) and r[0][0]['text'].strip() not in BULLETS and not r[0][0]['symbol'] and all(len(''.join(s['text'] for s in c)) <= 50 for c in r) for r in rows]
    #     runs, i = [], 0
    #     while i < len(rows):
    #         j = i
    #         if ok[i]:
    #             cols = [c[0]['x'] for c in rows[i]]
    #             while j + 1 < len(rows) and ok[j + 1] and lines[j][0]['y'] - lines[j + 1][0]['y'] < 3 * lines[j][0]['size'] and all(any(abs(c[0]['x'] - x) < 8 for x in cols) for c in rows[j + 1]): j += 1
    #         if j > i: runs.append((i, j, cols))
    #         i = j + 1
    #     return runs, rows

    # def flushPage():
    #     if not pageOpen: return
    #     pageOpen.clear()
    #     marker = {'page': True, 'colX': None}
    #     spans.append(marker)
    #     for a, b, c in pageRules:      #a fraction bar: the text just above and below it becomes one inline "top/bottom"
    #         near = [q for q in currentPageSpans if 'text' in q and q['text'].strip() and a - 3 <= q['ex'] + q['wid'] / 2 <= b + 3]
    #         top, bot = [q for q in near if 0 < q['y'] - c < 1.3 * q['size']], [q for q in near if 0 < c - q['y'] < 1.3 * q['size']]
    #         if top and bot and max(q['y'] for q in top) - min(q['y'] for q in bot) < 1.1 * top[0]['size'] and b - a < 1.6 * max(sum(q['wid'] for q in g) for g in (top, bot)) + 4:
    #             n, d = [''.join(q['text'].strip() for q in sorted(g, key=lambda q: q['ex'])) for g in (top, bot)]
    #             wrap = lambda t: t if re.fullmatch(r'[\w.]+', t) else f'({t})'
    #             currentPageSpans[:] = [q for q in currentPageSpans if q not in top + bot] + [dict(top[0], text=wrap(n) + '/' + wrap(d), x=min(q['ex'] for q in top + bot), ex=min(q['ex'] for q in top + bot), y=c - 0.3 * top[0]['size'], wid=b - a, under=False, moved=True)]
    #     for q in [q for q in currentPageSpans if q.get('text') == '()']:      #a tall bracket pair is one string: put ")" after the text it encloses
    #         end = q['ex'] + q['wid'] / 2
    #         for p in sorted((p for p in currentPageSpans if 'text' in p and p is not q and p['ex'] > q['ex'] and abs(p['y'] - q['y']) < 1.2 * q['size'] and p['size'] >= 0.85 * q['size']), key=lambda p: p['ex']):
    #             if p['ex'] - end >= 0.5 * q['size'] or p['text'].lstrip()[:1] in '.;': break
    #             end = max(end, p['ex'] + p['wid']) if p['text'].strip() else end
    #         currentPageSpans[:] = [p for p in currentPageSpans if p is not q] + [dict(q, text='(', wid=q['wid'] / 2), dict(q, text=')', x=end, ex=end, wid=q['wid'] / 2)]
    #     lines = groupLines(currentPageSpans)
    #     W = pageBox[2] - pageBox[0] if pageBox else 0
    #     xs = [round(s['x'] / 3) * 3 for l in lines for s in l if len(s.get('text', '').strip()) >= 25]
    #     near = [x for x in xs if W and abs(x - pageBox[0] - W / 2) < 0.15 * W]
    #     c = max(set(near), key=near.count) if near else 0
    #     if near.count(c) >= 5 and near.count(c) >= 0.25 * len(xs) and sum(x < c - 0.2 * W for x in xs) >= 5: marker['colX'] = c
    #     colX = marker['colX']
    #     runs, rows = tableRuns(lines) if colX is None else ([], [])
    #     inTable = {k: r for r in runs for k in range(r[0], r[1] + 1)}
    #     left, right = [], []
    #     for k, l in enumerate(lines):
    #         if k in inTable:
    #             if k == inTable[k][0]: left.append((l[0]['y'], {'table': (inTable[k][2], rows[inTable[k][0]:inTable[k][1] + 1])}, 1e9))
    #         else:
    #             a, b = [s for s in l if colX is None or s['x'] < colX - 3], [s for s in l if colX is not None and s['x'] >= colX - 3]
    #             if a: left.append((l[0]['y'], a, a[0].get('size', 1e9)))
    #             if b: right.append((b[0]['y'], b, b[0].get('size', 1e9)))
    #     gaps = sorted((a - b) / z for seq in (left, right) for (a, _, _), (b, _, z) in zip(seq, seq[1:]) if 0.5 < (a - b) / z < 3)
    #     marker['pitch'] = gaps[len(gaps) // 2] if gaps else 0
    #     for _, item, _ in left + right: spans.extend(item) if isinstance(item, list) else spans.append(item)
    #     currentPageSpans.clear()

    # for element in extractedElements:

    #     t = element.get('type')

    #     if t == 'pageStart':
    #         flushPage()
    #         pageBox = element.get('box')
    #         pageOpen.append(1); firstBox = firstBox or pageBox; hidden, rise, color, pageLinks = False, 0.0, (0, 0, 0), element.get('links', [])
    #         pageRules = [r for r in element.get('rules', []) if not pageBox or r[1] - r[0] < 0.7 * (pageBox[2] - pageBox[0])]

    #     elif t == 'image':
    #         currentPageSpans.append(element)

    #     elif t == 'blockStart':
    #         ctm = element.get('ctm', ctm)
    #         color = element.get('color', color)
    #         x = y = adv = tc = 0.0
    #         scale = 1.0
    #         moved = True

    #     elif t == 'font':
    #         size = abs(element.get('size', 11))
    #         base = element.get('base')

    #     elif t == 'matrix':
    #         scale = element['d'] if element['d'] else 1.0      #keeps its sign so flipped PDFs (Chrome, Cairo) still read top to bottom
    #         x, y, adv = element['x'], element['y'], 0.0
    #         moved = True

    #     elif t == 'position':
    #         x += element['dx'] * abs(scale)
    #         y += element['dy'] * scale; adv = 0.0
    #         if element['operator'] == 'TD':
    #             leading = -element['dy']
    #         moved = True

    #     elif t == 'leading':
    #         leading = element['value']

    #     elif t == 'charSpace': tc = element['value']
    #     elif t == 'color': color = element['rgb']
    #     elif t == 'renderingMode': hidden = element['mode'] == 3
    #     elif t == 'rise': rise = element['value']
    #     elif t == 'newline':
    #         y -= leading * scale; adv = 0.0
    #         moved = True

    #     elif t == 'text':
    #         txt = element.get('content', '')
    #         txt = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff\ufffe\uffff]', '', txt)   #also drops characters Word's XML can't store

    #         if txt == '' or hidden or re.fullmatch(r'[\s.]{15,}', txt):
    #             continue
    #         if re.fullmatch(r'\*\s*\d+\s*\*', txt.strip()) or (len(txt.strip()) >= 10 and len(set(txt.strip())) <= 5 and '.' not in txt):
    #             continue                               #barcode labels (*123*, bTTTTuTTh) are not content

    #         family, bold, italic = fontStyle(base)
    #         effSize = round(size * abs(scale) * abs(ctm[3]), 1)
    #         if effSize < 4:
    #             effSize = 11

    #         absX = ctm[0] * x + ctm[4]
    #         absY = ctm[3] * y + ctm[5]

    #         cropMargin = 0
    #         wd, ex = element['w'] * effSize + tc * len(txt) * abs(scale * ctm[0]) if element.get('w') else estW(txt, effSize), absX + ctm[0] * adv
    #         link = next((u for (x0, y0, x1, y1), u in pageLinks if x0 - 2 <= ex + wd / 2 <= x1 + 2 and y0 - 2 <= absY <= y1 + 2), None)
    #         under = len(txt.strip()) > 2 and any(a - 2 <= ex + wd / 2 <= b + 2 and 0 < absY - c <= 0.22 * effSize + 0.5 for a, b, c in pageRules)

    #         if pageBox:
    #             left, bottom, right, top = pageBox
    #             if absX < left - 5 or absX > right + 5 or absY < bottom - 5 or absY > top + 5:
    #                 continue                           #outside the page, so never visible
    #             if absX < left + cropMargin or absX > right - cropMargin:
    #                 continue                           #optional side-margin crop (stamps, margin notes), set with cropMargin
    #             #a lone 1-3 digit number in the header/footer strip is a page number, so drop it (numbers in the body are kept)
    #             if absY < bottom + 0.05 * (top - bottom) or absY > top - 0.05 * (top - bottom) or (re.match(r'^\d{1,3}$', txt.strip()) and (absY < bottom + 0.08 * (top - bottom) or absY > top - 0.08 * (top - bottom))):
    #                 continue
            
    #         currentPageSpans.append({'text': txt, 'x': ctm[0] * x + ctm[4], 'y': ctm[3] * y + ctm[5], 'size': effSize, 'font': family,
    #                       'bold': bold, 'italic': italic, 'moved': moved, 'ex': ex, 'wid': wd, 'rise': rise * abs(scale) * abs(ctm[3]), 'color': color, 'link': link, 'under': under,
    #                       'symbol': bool(base and re.search(r'dingbat|symbol', base, re.I))})
    #         moved = False
    #         adv += wd / (ctm[0] or 1)

    # flushPage()

    # leftMargin = min([s['x'] for s in spans if 'text' in s and s['text'].strip()], default=0)

    # rightEdge = firstBox[2] - (leftMargin - firstBox[0]) - 0.03 * (firstBox[2] - firstBox[0]) if firstBox else 1e9
    
    # #============Initializing the PPTX============ (Changed Sections)
    # prs = Presentation()
    # prs.slide_width = Inches(10)
    # prs.slide_height = Inches(7.5)
    
    # if firstBox: prs.slide_width, prs.slide_height = Pt(firstBox[2] - firstBox[0]), Pt(firstBox[3] - firstBox[1])
    # def addRun(para, s):
    #     run = para.add_run()
    #     run.text = text
    #     run.font.name, run.font.size, run.bold, run.italic = 'Arial' if pageNum == 1 and s['font'] == 'Times New Roman' else s['font'], Pt(s['size']), s['bold'] or None, s['italic'] or None
    #     if abs(s['rise']) > 0.2 * s['size']: run.font.superscript, run.font.subscript = s['rise'] > 0, s['rise'] < 0
    #     if s['color'] != (0, 0, 0) and min(s['color']) < 240: run.font.color.rgb = RGBColor(*s['color'])
    #     run.font.underline = True if s['under'] or s['link'] else None
    #     if s['link']:
    #         run.hyperlink.address = s['link']        
            
    # pitch, colX = 0, None
    # para = None
    # lastY = lastSize = lastEnd = None
    # seenPage, pageNum = False, 0



    # tf = None
    # for s in spans:
    #     if s.get('page'):
    #         seenPage, pageNum = True, pageNum +1
    #         #Adds a new blank slide
    #         slide = prs.slides.add_slide(prs.slide_layouts[6])
    #         # reset paragraph and text frames
    #         para = None
    #         tf = None
    #         continue

    #     if 'table' in s:
    #         cols, rows = s['table']
    #         table_shape = slide.shapes.add_table(
    #             rows=len(rows),
    #             cols=len(cols),
    #             left=Pt(0),
    #             top=Pt(0),
    #             width=prs.slide_width,
    #             height=Pt(100)
    #         )

    #         tbl = table_shape.table
    #         para = None
    #         tf = None
    #         for r, row in enumerate(rows):
    #             for cell in row:
    #                 cell_obj = tbl.cell(r, min(range(len(cols)), key=lambda k: abs(cols[k] - cell[0]['x'])))
    #                 p = cell_obj.text_frame.paragraphs[0]
    #                 for c in cell:
    #                     if p.text and c['moved'] and not p.text.endswith(' ') and not c['text'].startswith(' '):
    #                         p.add_run().text = ' '
    #                     addRun(p, c)
    #         continue

    #     if s.get('type') == 'image':
    #         try:
    #             # pptx requires left, top position. Width/Height optional (Pt(min(s['w'], 450)))
    #             slide.shapes.add_picture(
    #                 io.BytesIO(s['data']), 
    #                 left=Pt(s.get('x', 0)), 
    #                 top=Pt(s.get('y', 0)), 
    #                 width=Pt(min(s['w'], 450))
    #             )
    #         except Exception:
    #             pass  # an image PowerPoint can't take is skipped, not fatal
    #         para = None
    #         tf = None
    #         continue

    #     text = s['text']
    #     stripped = text.strip()

    #     # Helper: Ensure we have a active textbox/text_frame on the current slide for loose text
    #     if tf is None:
    #         # Create a full-slide text frame overlay for absolute positioning of text spans
    #         txBox = slide.shapes.add_textbox(Pt(0), Pt(0), prs.slide_width, prs.slide_height)
    #         tf = txBox.text_frame
    #         tf.word_wrap = True

    #     # A bullet glyph on its own starts a list item
    #     if stripped in BULLETS or (len(stripped) == 1 and s['symbol'] and not stripped.isprintable()):
    #         para = tf.add_paragraph() if len(tf.paragraphs[0].text) > 0 else tf.paragraphs[0]
    #         para.level = 0  # Applies bullet formatting level in PowerPoint
    #         lastY, lastSize = s['y'], s['size']
    #         continue

    #     # Whitespace-only pieces are just gaps: add one space unless the text already ends with one
    #     if not stripped:
    #         if para is not None and para.text and not para.text.endswith(' '):
    #             para.add_run().text = ' '
    #         continue

    #     newPara = False
    #     script = para is not None and s['size'] < 0.85 * lastSize and -0.3 * lastSize < s['ex'] - (lastEnd or 0) < 0.6 * lastSize and 0.15 * lastSize < abs(s['y'] - lastY) < 1.1 * lastSize
    #     if script: 
    #         s = dict(s, size=lastSize, rise=s['y'] - lastY)
    #     elif para is None:
    #         newPara = True
    #     else:
    #         gap = abs(s['y'] - lastY)
    #         if gap < 0.5 * s['size']:
    #             pass  # same line
    #         elif abs(s['size'] - lastSize) > 1 or gap > (min(1.7, 1.3 * pitch) * s['size'] if pitch > 0.8 else 1.7 * s['size']):
    #             newPara = True  # heading/size change or a paragraph-sized gap

    #     if newPara:
    #         # Use initial empty paragraph if not used yet, else append new paragraph
    #         para = tf.paragraphs[0] if (len(tf.paragraphs) == 1 and not tf.paragraphs[0].text) else tf.add_paragraph()
            
    #         # Position-based alignment check
    #         if s['x'] - (colX if colX and s['x'] >= colX - 3 else leftMargin) > 80:
    #             para.alignment = PP_ALIGN.RIGHT if s['x'] + 0.5 * len(text) * s['size'] > rightEdge else PP_ALIGN.CENTER
    #     elif s['moved'] and not script and para.text and not para.text.endswith(' ') and not text.startswith(' ') and (abs(s['y'] - lastY) > 0.5 * s['size'] or s['ex'] - lastEnd > 0.2 * s['size']):
    #         para.add_run().text = ' '

    #     addRun(para, s)

    #     lastY, lastSize = (lastY, lastSize) if script else (s['y'], s['size'])
    #     lastEnd = s['ex'] + s['wid']





    # PDFName = os.path.basename(PDFPath).split(".")[0]
    
    # outputPath = f"Outputs/{PDFName}.pptx"

    # os.makedirs(os.path.dirname(outputPath) or ".", exist_ok=True)
    # prs.save(outputPath)
    # print("done")

PDFToWord(pdf1)