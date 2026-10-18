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