## Notes on how to merge a PDF without usinf any extentions

# Structure Of PDF

+---------------------------------------------------+
| 1. HEADER                                         |
|    %PDF-1.7                                       |
+---------------------------------------------------+
| 2. BODY                                           |
|    1 0 obj ... endobj                             |
|    2 0 obj ... endobj                             |
|    3 0 obj ... endobj                             |
|    (All pages, text, images, fonts lived here)    |
+---------------------------------------------------+
| 3. XREF TABLE (Cross-Reference Table)             |
|    0 4                                            |
|    0000000000 65535 f                             |
|    0000000015 00000 n                             |
|    0000000230 00000 n                             |
|    (An index listing byte offsets for all objects) |
+---------------------------------------------------+
| 4. TRAILER                                        |
|    /Root 1 0 R                                    |
|    startxref 1024                                 |
|    %%EOF                                          |
+---------------------------------------------------+


1. Header - "%PDF-1.x" - this tells the reader what PDF version standard it uses
2. Body - Seires of numbered objects, each object contains the fonts, text, images etc - these are like mini relational databases
    - the starting point of the file is /Pages, thsi will list all the /Page objects
        - this stores the page references

        2 0 obj
        <<
        /Type /Pages
        /Count 3
        /Kids [3 0 R, 4 0 R, 5 0 R]   % <--- THESE ARE PAGE REFERENCES
        >>
        endobj

        here 
        /Type /Pages - declares this as a root catalog
        /Count - tels the numbe rof printable pages managed by this branch
        /Kids - this array stores the object refernces(R) now these point to indivisual pages ie /Page

    - a pdf file can have multiple /Pages but not recommeded, so the /Root catalog of the pdf points to the primary /Pages and then the hiearchy follows
    - when we are merging them we discard both the /Pages root oject adn the create one combined one
    - /Page object hold the pointers to its own resources such as:
        1. /MediaBox
        2. /Parent - points back to /Pages
        3. /Contents - points to actual content
        4. /Resources - fonts and images used on the page


3. Cross-Reference Table - xref - this is a byte offset map basically tells the PDF viewer which object is where

    - the xref table stores the refernces with the offset that where it is used in the PDF
4. Trailer - /Root - this tells the location of the xref table

- a pdf reader reads the fiel from the very bottom
- it looks for th e%%EOF at the bottom and then reads backwards to find startxref
- startxref gives the byte number where the xref table begins
- the trailer also identifies the ROot caatalog
- from the root catalog it points to the /Pages and from that it gets the /Page refernces


Object 1 is the /Catalog - thsi is the absolute entry point of the PDF
Object 2 is the /Pages - this is the root directory
Object 3 is the /Pages - this is the single page
Object 4 is the stream - this is the raw commands for operations

# PDF in detail
- /Pages is like the table of contents - this is the parent object
- /Page is an individual page 
- /Count this tells the total number of printable pages
- /Kids 

# for combining PDF
We work on the following objects:
1. keep only one of the Headers
2. Combine all the body objects - this is basically recalculating PDF2 object ids
3. Create a new root catalog and /Pages that lists all the pages
4. Calculate the new Byte offsets for the xref table


# COre Issue

so both the files have objects with numbered ids, so simply concatinating their binaries will corrupt both the file
so the solution is to count the highest id of the 1st pdf and then adding it to the ids of the 2nd pdf 
Eg

PDF1 = 1 0 obj, 2 0 obj, 3 0 obj
PDF2 = 1 0 obj, 2 0 obj, 3 0 obj

both of them have the same ids so we count the highest id of pdf1 which for example is 15 so the new ids of PDF2 becomes the following
PDF2 = 16 0 obj, 17 0 obj, 18 0 obj

# The Working:

1. read the pdf files into bytearray because we are working in python
    - bytearray stores raw number from 0 to 255 whcih represent binary data
    - we cannot open a pdf in standard text string as it will mangle the data because a pdf contains non text binary data like compressed, images etc
2. then scan throughthe raw bytes and locate the existing object marker, their formats will be "X Y obj" and "endobj"
3. parse throught the pdf1 and find its hightest object id(X) which we assume is N
4. then parse through pdf2 and update every object declaration id such that they become "X + N"
    - an object declaration in a pdf is basically where the data defined and witten for an object
5. then we update all the reference tags on pdf2 aswell
    - object reference is basically when that object is called
    - in easy words object declaration is like declaring a variable and the object refernce is like calling a variable
6. we create a unified page catalog form both pdf
    - page catalog refers to /Pages root object, thsi is the central dictionary that lists every page in the pdf in order
    - for this we give a brand new ID for the /Pages

    EG. 
        100 0 obj
        <<
        /Type /Pages
        /Count 4
        /Kids [
            3 0 R   4 0 R     % Pages from PDF A
            13 0 R  14 0 R    % Pages from PDF B (renumbered)
        ]
        >>
        endobj

        PDF1 had 2 pages and PDF2 also had 2 pages so not the /COunt is 4
        the ids in pdf2 are added with max to now the pages of PDF2 are 12 adn 14
7. nwo we update the /Parent pointer in each /Page object
    eg.
        /Parent 100 0 R

8. now we crate a new /Type /Catalog as th etop level pointer for the file, and then point it to our /Pages
    eg. 
        101 0 obj
        <<
        /Type /Catalog
        /Pages 100 0 R
        >>
        endobj

9. now all the objects are assembled and we only need to recalculate the byte offsts fo rthe xref table, these are the byte poitions of eac object from byte 0
    # Calculation
    1. the Byte 0 was where our header began
    2. so we convert each object string into byte by ASCII or UTF-8 and record the current lenght of the output array
        [Header: %PDF-1.7\n]
            --> Total bytes so far: 9
    [Obj 1: 1 0 obj ... endobj\n]
        --> Offset for Obj 1 = 9. Length = 45 bytes. Total now = 54
    [Obj 2: 2 0 obj ... endobj\n]
        --> Offset for Obj 2 = 54. Length = 60 bytes. Total now = 114


Rules for XREF table
- Exactly 20 Bytes Per Entry Line
    0000000015: 10-digit zero-padded byte offset.
    : Single space.
    00000: 5-digit generation number (always 00000 for new files).
    : Single space.
    n: Flag for in-use objects (f for free/deleted objects).
    \n or \r\n: Trailing space + newline (must make the line exactly 20 bytes total).
- Object 0 Special Entry: The first line under xref must always be 0000000000 65535 f \n representing the head of the free list.




