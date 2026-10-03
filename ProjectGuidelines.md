## Project Guidelines 
One of the biggest issue we will face will inputting and outputing the files. Due to this, I have created an input and an output folder which all functions will use. Other than that, we will implement each functions page separetely depending on the specifics. 

Before starting any of the features, we need to recreate pypdf. We will do this in the helper function divinding into separate functions like read and write etc. 

# pypdf
We will recreate the pypdf library in someway or other. This is overview for that. 

PDF structure: 
A PDF is a text based binary document whhc is built as an Object Graph. It has 4 main sections:
    1. Header: Indicates PDF version
    2. Body: Indirect Objects identified by number (Object 1, Object 2, Object 3)
    3. XReF Table: A cross reference table which shows where each object is in the file (Object 1 is at character position 433)
    4. Trailer: Points to the xRef table. The reader starts at the trailer to find the xRef table. 

The PDF uses this table type structure so that it doesn't has to load all pages if we go to page 250 directly. A PDF is read by first opening the file, jumping to the trailer, reading the Xreftable and opening all the Objects required. 

We need 3 Components to recreate pypdf:
1. Object data model: Converts pdf types into python class representation. Examples would be:
PdfObject: base class
numberObject: numbers
TextStringObject: string wrapped in () or <>
IndirectObject: a pointer 10 0 R referencing object R, ID 10, generation 0 (Generations are a version counter which increase if we delete an ID and replace it with smthg else)

2. The parser: Find trailer at the end of the file (%%EOF) to find startxref. Then read byte offsets (character count) for every indirect object. Get an object only if it is referenced instead of loading the whole table. Decompress the objects to get original (its name is flatedecode) 

3. The serializer and manipulator: Clone the dictionary then merge objects from multiple xref tables while renaming the ids to prevent collision. Convert python objects back into the binary string formats. 