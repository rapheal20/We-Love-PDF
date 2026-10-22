## Convert PDF to PowerPoint


- A powerpoint is just ZIP archive under the hood
- so if we change the extension of pptx to .zip and extract it we get text files with XML, XML is very similar to HTML
- The Folder will include the following:
    - A mster list file: acts as the table of content, stores slides in correct order
    - Indivisual slide files: seperate text files for every slide
        tell what shapes,colours and words go where
    - relationship files: simple map files that tell powerpoint how everything conects together

# Working

1. read pdf`s content stream and find
    - text strings
    - coordinates
    - embedded images

2. write the XML text files

3. Bundle them into ZIP using zipfile

4. save it as a .pptx extension

# Conversion

- To build a slide we need 3 pieces of data
    1. text string
    2. x coordinates
    3. y coordinates

- Fix the coordinates:
    - PDF start at botton left corner
    - Powerpoints start at top left corner
    - for thsi powerpintY = PageHeight - PDFY

- Convert units into EMUs
    - PDF measure in points
    - Powerpoirnts work in EMUs
    so take PDF coordinates and multiply then by 12700(Scale Factor)

- Inject Data into XML Template
    FORMAT:
    [XML Template Shell]
        [Position Block]
            [Text Box Body]

- For images:
    - we extract the image stream from PDF and save it as .jpg directly in the ZIP
    - For linking the Image to the slide:
    - we create a relationship file for slide1.xml
    

Need a transition logic

- COnverting PostScript Vector into SVG

CHANGES:
m to M (moveto)
l to L (lineto)
c to C (curveto)
h to Z (closepath)
f to <path> (fill)

TRACK GRAPHIC STATE WRAPPER
- Stream starts with g and ends with Q blocks
- these are opening and closing brackets
- these need to be replaced with <g>

ASEMBLE SVG XML
- get width and height from mediabox
- close SVG root tag