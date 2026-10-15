# Notes on the SplitPDF function
The SplitPDF function takes in the PDF path and the page at which the PDF should be split and generates the two separate parts in the Outputs folder. 

I have already written the function, but I will make sure to write the readme beforehand for the next function. 

The working of the SplitPDF is:
1. Gets the PDF version, XrefTable, Root Object details, and Catalog Object details. 
2. Find the total number of pages
3. Parses all the pages using the pageParser function to extract each pages attributes like MediaBox, contents, resources. pageParser also collects all object dependencies (all the object used in the page) using DFS search
4. Split the pages details into parts based on the splitPage parameter 
5. For each part, maps the original object IDs to new renumbered IDs, then generate the default Objects (/Catalog, /Pages) including their kids
6. For all the objects in the original PDF, it updates their headers and references with the new renumberd IDs
7. Creates the new Xreftable in byte form, trailer in byte form, header in byte form
8. Everything in 6 and 7 is then written to the new export file

Coded by Anael