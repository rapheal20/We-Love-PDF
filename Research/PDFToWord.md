## Notes on PDFToWord function
Coded by Anael
This function will take a pdf and convert it into an editable word file. The word file will have text for the text and pictures for other graphics like graphs logos.

# How it works
The docs converter works by extracting all the text, layout and structural elements from the PDF and rebuilding them in a word document format. 

# Steps 
1. Do the basic stuff like getting the Xreftable using helper functions 
2. We will now locate each page's /contents object ID and go to the location of each of the content objects. 
3. Now we will read the content streams that is inbetween stream and endstream
4. Decompress each stream if it has a /filter /flateDecode entry 
5. In each of the stream, I will get the text blocks (in between BT and ET). Also track TJ (array of text strings and spacing adjustments) and Tj operators (text string). Also track positioning operators like TD and Td (move text position), T* (move to the start of the next line)
6. Find the font dictionary in the /Resources. Same with ToUnicode CMap (if there) as this will translate raw character codes into actual unicode characters.
7. Structure the extracted text by using the x and y coordinates and grouph paragraph 
8. Create the docx file that has its own structure (will mention later)

Till step 2/3, the code can somewhat be repeated from the SplitPDF function. 


# Fonts/CMap table:
I have gotten all the details including the text content as hex. It needs to be translated into actual character using the CMap table. To get the table. I will get /Resources dict which has the /fonts dict where all the fonts are mapped like /F1. Then ill read the Cmap table and parse. Some of this code has already been written by me in the ReadPDF.py 

I might use python docx. It is used to read, create and update word files. This is cuz a docs file is actually a zip with a lot of xml files and stuff. I think trying to make mysef would be too hard. 

# Images 
Images are also inside the resources for each page. I need to find the /XObject dict for each page. There it will have a /Subtype /Image object. Then I can use my read and decompress stream funct to get the raw bytes of the image. 
If the image has /DCTDecode its a jpeg file 
if the image is /FlateDecode its raw pixel data which we can convert using PIL. (This is a library)
Then getting all the pics I can insert them into the doc with dc.add_picture()
Xobject is this: /XObject<</Im13 13 0 R>>. lm13 is the local resource name. 13 is the object ID. 
Going to the Image offset will give us the image: 
b'13 0 obj\n<</Type/XObject/Subtype/Image/Width 2160 /Height 1441 /BitsPerComponent 8 /ColorSpace/DeviceRGB/Filter/DCTDecode/Length 373393>>\nstream\n\xff\xd8\xff\xe0\x00\x10JFIF...'


# Regular expression symbols
1. Ordinary Characters stay the same eg a z 5
2. Special Symbols:
    - . (dot): matches any single character except a newline
    - ^ (caret): matches start of a string
    - $ (dollar): matches end of a string
    - | (pipe): Acts as an OR operator
3. Repetions:
    - *: 0 or more times
    - +: one or more times
    - ?: 0 or one time (optional)
    - {n, m}: between n and m times
4. character classes:
    - [aeiou]: matches any single vowel
    - [^aeiou]: matches anything except a vowel
    - \d: matches any digit 
    - \w: matches any character (letter, numbers, underscore)
    - \s: matches any whitescape (spaces, tabs, newlines) 

