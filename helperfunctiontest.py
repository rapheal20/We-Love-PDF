#I got this file made by Gemini to make sure the code I am writting is correctly mapping stuff. 

from pypdf import PdfReader

reader = PdfReader("Inputs/file-example_PDF_1MB.pdf")

# Print the trailer dictionary containing /Root
print("Trailer dictionary:", reader.trailer)

# Get the Root Catalog object and its indirect reference ID
if "/Root" in reader.trailer:
    root_obj = reader.trailer["/Root"]
    # IndirectObject has an 'idnum' attribute for the object number
    print("Root Object ID:", root_obj.indirect_reference.idnum)