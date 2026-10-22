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

I just found out that there are actually two types of pdf. Due to this a lot of the code would have to be rewritten to accomodate the second type. 

The new pdf strucuture has flate compressed binary stream. That's why all the object streams are compressed inside other objects 

I am also trying to get the function really versatile that's why I got some bad cases from claude like encryption and added them.

The new approach for the file is:
1. I have made a new function GetObjectBytes(id). This is what everything works on. If the object is normal, it gets the object bytes. If it's compressed, it calls the other func ReadObjectSream  which reads the container, decompresses it an then it wraps in the normal format of obj end obj. So this way compressed is turned into a normal kind of object. 
2. And the rest is kind of same as the old code. 