'''
This function read all the pdf files given and merges them in the order selected.
The function will take the pdfs from inputs folder and a dict which will have file name as key and sequence number as value.
Then it will READ the pdfs in the order and WRITE to a new file
'''
import pypdf as pd

pdf1 = "Inputs\\file-example_PDF_1MB.pdf"
pdf2 = "Inputs\\file-example_PDF_500_kB.pdf"



# reader1 = pd.PdfReader(pdf1)
# reader2 = pd.PdfReader(pdf2)
# numberOfPages1 = len(reader1.pages)
# numberOfPages2 = len(reader2.pages)

# outputPDF = pd.PdfWriter()

# for i in range(numberOfPages1):
#     page = reader1.pages[i]
#     outputPDF.add_page(page)

# for j in range(numberOfPages2):
#     page = reader2.pages[j]
#     outputPDF.add_page(page)


# with open("newPDF.pdf", "wb") as output:
#     pd._writer.write(outputPDF)


with open(pdf2, "r") as file:
    content = file.read()
    print(content)