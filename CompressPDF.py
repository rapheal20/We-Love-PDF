import re
import zlib
import os
from io import BytesIO
from PIL import Image
from helperfunctions import *


'''
MAIN DATA STRUCTURE
Objects_List = [
    {"ObjectID" : 3,
    "Body" : ".....",
    "References" : [3,4]
    }
]

'''



# pdf3 = "Inputs\\emaar.pdf"
# pdf3 = "Inputs\\file-example_PDF_1MB.pdf"
pdf3 = "Inputs\\emaar2.pdf"

def PDFCompressFunc(pdf_file):   
    try:
        #opens file, when using with no need to close it
        with open(pdf_file, "rb") as file:
            PDF_Data_RB = file.read()

        PDF_Data = PDF_Data_RB.decode("latin1")
        # converts it into byte like format

        # takes the string of the pdf
        # extracts all the objects from it, along with its references
        # returns the dict
        def PDF_Dict_Maker(PDF_Data):
            Objects_List = {}
            XrefTable = XrefTableFunc(pdf_file)[0]
            objStmCache = {}
            for objNum in XrefTable:
                with open(pdf_file, "rb") as pdfRB:
                    ObjectData = GetObjectBytes(pdfRB, XrefTable, objNum, objStmCache).decode("latin1")
                if not ObjectData:
                    continue
                if not ObjectData.rstrip().endswith("endobj"):
                    ObjectData += "\nendobj"
                ObjectID = str(objNum)

                referenceList = []
                references = re.finditer(refFindString, ObjectData, flags=re.IGNORECASE)
                if references:
                    for ref in references:
                        referenceList.append(ref.group(1))


                Objects_List[ObjectID] = {
                    "ObjectID" : ObjectID,
                    "Body" : str(ObjectData),
                    "References" : referenceList,
                }

            return Objects_List

        Objects_Dict = PDF_Dict_Maker(PDF_Data)

        RootID = str(RootObjectIDFunc(pdf_file))

        '''Breath For Search'''
        #breath for search algorithm for finding out if all the objects are conencted or not
        # makes a set of visited, anything object other then that is a stray and can be removed
        visited = set() #to ensure no duplicates
        queue = [RootID]

        while queue:
            current_id = queue.pop(0)
            if current_id not in visited and current_id in Objects_Dict:
                visited.add(current_id)
                #check if it is already visited or ot and if the id exists in Object_List
                #if not visited and exists then adds into visited set

                child_refs = Objects_Dict[current_id].get("References", [])
                # gets the references of the current object

                for ref_id in child_refs:
                    if ref_id not in visited:
                        queue.append(ref_id)
                #checks if each of those refs exist in visited, if they dont then it appends it to queue
                #Working behind it, ensure if some id is visited then it is not checked again

        # iterates through the visited set, and appends the objects into a list if they are visited
        # removes the strays
        NewObjLists = []
        for id in visited:
            NewItem = Objects_Dict[id]
            NewObjLists.append(NewItem)

        # goes through the new cleaned up list, and finds all the objects that are meta data
        ToRemove = []
        for purgeObj in NewObjLists:
            body = purgeObj["Body"]
            metaFindStr = r"\s*/\s*Type\s*/\s*Metadata"
            metaData = re.search(metaFindStr, body, flags=re.IGNORECASE)
            if metaData:
                ToRemove.append(purgeObj["ObjectID"])

        # goes through the newobjlist and removes all the metadata objects in the list ToRemove
        MetaRemovedList = []
        for obj in NewObjLists:
            objID = obj["ObjectID"]
            if objID not in ToRemove:
                MetaRemovedList.append(obj)

        #goes through the final obj list and removes all the refernces of metadata
        for obj in MetaRemovedList:
            body = obj["Body"]
            for MetaID in ToRemove:
                metaRefStr = rf"\s*/\s*Metadata\s*{MetaID}\s+0\s+R"
                body = re.sub(metaRefStr, "", body, flags=re.IGNORECASE)
            obj["Body"] = body


        #images
        for imgObj in MetaRemovedList:
            try:
                body = imgObj["Body"]
                imgData = re.search(imgFindStr, body, flags=re.IGNORECASE)
                # searches for img object in the body of each object
                # if an object has an img object then compresses
                if imgData:
                    imgBytesOffset = (re.search(r"stream(\r\n|\n|\r)", body)).end()
                    imgBytesEnd = body.rfind("endstream")
                    imgBytesEnd -= 2 if body[imgBytesEnd-2:imgBytesEnd] == "\r\n" else 1
                    imgBytes = (body[imgBytesOffset:imgBytesEnd])
                    # converts the str into byte stream
                    imgBytes = imgBytes.encode('latin1')  

                    '''Compressor'''
                    # Works only on DCT or Flate filter,
                    # finds if the filter is DCT
                    # DCT are already jpeg bytes, so no need to uncompress or what not
                    # directly converted into an image and then quality is decreased
                    compressorDCT = re.search(r"\s*/\s*DCTDecode\s*", body, flags=re.IGNORECASE)
                    if compressorDCT:
                        img = Image.open(BytesIO(imgBytes))
                        #converts into image which pillow(PIL) can use

                        outputBuffer = BytesIO() #opens an empty space in RAW
                        img.save(outputBuffer, format="JPEG", quality=75, optimize=True) #writes in that RAM container instead of harddrive
                        #decreased quality to 75%

                        newStream = outputBuffer.getvalue()
                        if len(newStream) >= len(imgBytes): continue
                        #converts back into the latin1 format

                        streamLenght = len(newStream) #used for the lenght in decoded
                        decodedStream = newStream.decode('latin1') #converts stream back into latin1, using str blocks the codes
                        newbody = (body[:imgBytesOffset-1] + "\n") #appends the header of the object
                        newbody += decodedStream #appends the new stream
                        newbody += ("\n" + body[imgBytesEnd+1:]) #appends the end of object

                        lenghtTag = r"\s*/\s*Length\s+\d+\s*"
                        newbody = re.sub(lenghtTag, f"/Length {streamLenght}", newbody, count=1, flags=re.IGNORECASE) # replaces the lenght of object

                        imgObj["Body"] = newbody #replaces the old body with the new body
                
                    else:
                        # checks if the compressor is Flate
                        # Flate is a compressed form of stream
                        # so first we need to decompress using zlib
                        # then make the new img and then the stream
                        # in doing so we also need to provide the width, height coloursystem of the image
                        compressorFlat = re.search(r"/Filter\s*\[?\s*/FlateDecode\s*\]?\s*(?=[/>])", body, flags=re.IGNORECASE)
                        if compressorFlat and "/Predictor" not in body:
                            decompressedBytes = zlib.decompress(imgBytes) #decompresses the image bytes to what .io can understand

                            widthFind = r"\s*/\s*Width\s*(\d+)\s*" #re string to find the width of the image
                            heightFind = r"\s*/\s*Height\s*(\d+)\s*" #re string to find the height of the image
                            colourFind = r"/ColorSpace\s*/Device([a-z]+)\s*" ##re string to find the colour system of the image

                            imgWidth = int((re.search(widthFind, body, flags=re.IGNORECASE)).group(1))
                            imgHeight = int((re.search(heightFind, body, flags=re.IGNORECASE)).group(1))
                            imgColor = (re.search(colourFind, body, flags=re.IGNORECASE))

                            # in some cases the colour is a reference, in such cases we skip the compression
                            if imgColor and re.search(r"/BitsPerComponent\s+8\b", body) and len(decompressedBytes) == imgWidth * imgHeight * {"GRAY": 1, "RGB": 3}.get(imgColor.group(1).upper(), 0):
                                colorSpace = imgColor.group(1)
                                if colorSpace.upper() == "GRAY":
                                    img = Image.frombytes("L", (imgWidth, imgHeight), decompressedBytes)
                                else:
                                    img = Image.frombytes(colorSpace, (imgWidth, imgHeight), decompressedBytes)
                                outputBuffer = BytesIO() #opens an empty space in RAW
                                img.save(outputBuffer, format="JPEG", quality=75, optimize=True) #writes in that RAM container instead of harddrive
                                #decreased quality

                                newStream = outputBuffer.getvalue()
                                if len(newStream) >= len(imgBytes): continue
                                #converts back into the latin1 format

                                streamLenght = len(newStream) #used for the lenght in decoded
                                encodedStream = newStream.decode('latin1')
                            
                                newbody = (body[:imgBytesOffset-1] + "\n") #appends the header of the object
                                newbody += encodedStream #appends the new stream
                                newbody += ("\n" + body[imgBytesEnd+1:]) #appends the end of object

                                lenghtTag = r"\s*/\s*Length\s+\d+\s*"
                                newbody = re.sub(lenghtTag, f"/Length {streamLenght}", newbody, count=1, flags=re.IGNORECASE) # replaces the lenght of object
                            
                                # removes DecodeParms and BitsPerComponent as an img file dosnt need them
                                # after the compression we use DCT filter
                                newbody = re.sub(r"\s*/\s*DecodeParms\s*\.", "", newbody, flags=re.IGNORECASE)
                                newbody = re.sub(r"\s*/\s*FlateDecode\s*","/DCTDecode" , newbody, flags=re.IGNORECASE)
                            
                                imgObj["Body"] = newbody
                            else:
                                continue
            except Exception as e:
                print(f"skipped image object {imgObj['ObjectID']}: {e}")  # leave this image untouched

        # gives each object a new id, to remove the blanks from removing alot of objects
        FinalObjLists = []
        newIDConst = 1
        for NewItem in MetaRemovedList:
            NewItem["NewID"] = newIDConst
            newIDConst +=1
            FinalObjLists.append(NewItem)

        #iterates throught the final array of the objects and concatinates them into a string
        NewBody = ""
        for newBodyObj in MetaRemovedList:
            NewBody += newBodyObj["Body"]
            NewBody += "\n\n"

        #calls a helper function to remap those new ids just given
        NewBody = PDF_ID_Remap(FinalObjLists, NewBody, "ObjectID")
        # calls a helper function to make a new header object
        headerObj = Make_Header(PDF_Data)

        # seaches for the new id of the catalog obj
        catalogIDOffset = re.search(catalogFindString, NewBody, flags=re.IGNORECASE)
        catalogIDList = list(re.finditer(objectFindString, (NewBody[:catalogIDOffset.start()]), flags=re.IGNORECASE))
        catalogID = catalogIDList[-1].group(1)

        # concatinates the new header obj and the new body
        CombinePDFStr = headerObj + "\n\n" + NewBody + "\n\n"

        # calls helper function to form the new xref table for the pdf
        xreftable, ObjNumber = Make_Xref(objectFindString, CombinePDFStr)
        CombinePDFStr += xreftable #concatinates the new xref table

        byteOffset = CombinePDFStr.rfind("xref") #finds the byte offset of the new xref table
        trailerObj = f"\ntrailer\n<<\n/Size {ObjNumber +1}\n/Root {catalogID} 0 R\n>>\nstartxref\n{byteOffset}\n%%EOF"
        #creates the new trailer for the pdf

        CombinePDFStr += "\n\n" + trailerObj #concatinates the new trailer

        encodedPDF = CombinePDFStr.encode("latin1") # encodes the pdf string back to latin1

        PDFName = os.path.basename(pdf_file).split(".")[0]
        with open(f"AppOutputs\\{PDFName}-Compressed.pdf" , "wb") as file:
            file.write(encodedPDF)

        return [f"AppOutputs\\{PDFName}-Compressed.pdf"]
    except Exception as e:
        print(e)


#PDF_Compress(pdf3)
#PDFCompressFunc("Inputs/emaar2.pdf")