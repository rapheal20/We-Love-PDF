import re
# import pillow
import zlib
from io import BytesIO
from PIL import Image

'''
MAIN DATA STRUCTURE
Objects_List = [
    {"ObjectID" : 3,
    "Body" : ".....",
    "References" : [3,4],
    "StartOffset" : 3454,
    "EndOffset" : 3245465}


]

'''



pdf3 = "Inputs\\emaar.pdf"

with open(pdf3, "rb") as file:
    PDF_Data_RB = file.read()

PDF_Data = PDF_Data_RB.decode("latin1")

objectFindString = r"\b(\d+)\s+(\d+)\s+obj" 
objectEndString = r"\bendobj"

refFindString = r"\s*(\d+)\s+(\d+)\s+R" 

Objects_List = {}
Objects = re.finditer(objectFindString, PDF_Data, flags=re.IGNORECASE)
for object in Objects:
    startOffset = object.start()
    ObjectEnd = re.search(objectEndString, PDF_Data[startOffset:], flags=re.IGNORECASE)
    endOffset = ObjectEnd.end() + startOffset
    ObjectData = (PDF_Data[startOffset:endOffset])
    ObjectID = object.group(1)

    referenceList = []
    references = re.finditer(refFindString, ObjectData, flags=re.IGNORECASE)
    if references:
        for ref in references:
            referenceList.append(ref.group(1))


    Objects_List[ObjectID] = {
        "ObjectID" : ObjectID,
        "Body" : str(ObjectData),
        "References" : referenceList,
        "StartOffset" : startOffset,
        "EndOffset" : endOffset,
        # "Visited" : False
    }

# /Root 234 0 R

# r"\b(\d+)\s+(\d+)\s+R"
#\s* represents no or more spaces
trailerFindString = r"/\s*Root\s+(\d+)\s+(\d+)\s+R"
TrailerObj = re.search(trailerFindString, PDF_Data, flags=re.IGNORECASE)

RootID = TrailerObj.group(1)

# print(RootID)
#breath for search algorithm for finding out if all the objects are conencted or not
# makes a set of visited, anything object other then that is a stray and can be removed
visited = set() #to ensure no duplicates
queue = [RootID]

while queue:
    current_id = queue.pop(0)
    if current_id not in visited and current_id in Objects_List:
        visited.add(current_id)
        #check if it is already visited or ot and if the id exists in Object_List
        #if not visited and exists then adds into visited set

        child_refs = Objects_List[current_id].get("References", [])
        # gets the references of the current object

        for ref_id in child_refs:
            if ref_id not in visited:
                queue.append(ref_id)
        #checks if each of those refs exist in visited, if they dont then it appends it to queue
        #Working behind it, ensure if some id is visited then it is not checked again


# print(len(Objects_List))
# print(len(visited))

NewObjLists = []
newIDConst = 1
for id in visited:
    NewItem = Objects_List[id]
    NewItem["NewID"] = newIDConst
    newIDConst +=1
    NewObjLists.append(NewItem)

# print(len(NewObjLists))

ToRemove = []
for purgeObj in NewObjLists:
    body = purgeObj["Body"]
    metaFindStr = r"\s*/\s*Type\s*/\s*Metadata"
    metaData = re.search(metaFindStr, body, flags=re.IGNORECASE)
    if metaData:
        ToRemove.append(purgeObj["ObjectID"])

# /Metadata 83 0 R
MetaRemovedList = []
for obj in NewObjLists:
    objID = obj["ObjectID"]
    if objID not in ToRemove:
        MetaRemovedList.append(obj)

# print(len(MetaRemovedList))
for obj in MetaRemovedList:
    body = obj["Body"]
    for MetaID in ToRemove:
        metaRefStr = rf"\s*/\s*Metadata\s*{MetaID}\s+0\s+R"
        body = re.sub(metaRefStr, "", body, flags=re.IGNORECASE)
    obj["Body"] = body


#images


# /Subtype/Image
bigBody = ""
for imgObj in MetaRemovedList:
    body = imgObj["Body"]
    imgFindStr = r"\s*/\s*Subtype\s*/\s*Image\s*"
    imgData = re.search(imgFindStr, body, flags=re.IGNORECASE)
    if imgData:
        imgBytesOffset = (re.search(r"\s*stream\s*", body, flags=re.IGNORECASE)).end()
        imgBytesEnd = (re.search(r"\s*endstream\s*", body, flags=re.IGNORECASE)).start()
        imgBytes = (body[imgBytesOffset:imgBytesEnd])
        imgBytes = imgBytes.encode('latin1')  
        # print(imgBytes)
        # break

        #Compressor
        compressorDCT = re.search(r"\s*/\s*DCTDecode\s*", body, flags=re.IGNORECASE)
        if compressorDCT:
            # print(imgObj["ObjectID"])
            # print("DCT")
            img = Image.open(BytesIO(imgBytes))
            #converts into image which pillow(PIL) can use
            # img.show()

            outputBuffer = BytesIO() #opens an empty space in RAW
            img.save(outputBuffer, format="JPEG", quality=75, optimize=True) #writes in that RAM container instead of harddrive
            #decreased quality

            newStream = outputBuffer.getvalue()
            #converts back into the latin1 format

            lenght = len(newStream) #used for the lenght in decoded

            newbody = (body[:imgBytesOffset-1] + "\n") #appends the header of the object
            newbody += str(newStream) #appends the new stream
            newbody += ("\n" + body[imgBytesEnd+1:]) #appends the end of object

            lenghtTag = r"\s*/\s*Length\s+\d+\s*"
            newbody = re.sub(lenghtTag, f"/Length {lenght}", newbody, flags=re.IGNORECASE)
            # replaces the lenght of object

            imgObj["Body"] = newbody
        
        else:
            compressorFlat = re.search(r"\s*/\s*FlateDecode\s*", body, flags=re.IGNORECASE)
            if compressorFlat:
                decompressedBytes = zlib.decompress(imgBytes)
                print(imgObj["ObjectID"])


                print("FLT")



        








# NewBody = ""
# for newBodyObj in MetaRemovedList:
#     NewBody += newBodyObj["Body"]
#     NewBody += "\n\n"



# #Making a mapping dict what has originalID as key and NewID as value
# mapping_Dict = {}
# for obj in NewObjLists:
#     mapping_Dict[str(obj["ObjectID"])] = str(obj["NewID"])

# def Obj_Declaration(match):
#     oldID = match.group(1)
#     newID = mapping_Dict.get(oldID, oldID)
#     return f'{newID} 0 obj'

# def Obj_Reference(match):
#     oldID = match.group(1)
#     newID = mapping_Dict.get(oldID, oldID)
#     return f'{newID} 0 R'

# NewBody = re.sub(r'\b(\d+)\s+0\s+obj\b', Obj_Declaration, NewBody, flags=re.IGNORECASE)
# NewBody = re.sub(r'\b(\d+)\s+0\s+R\b', Obj_Reference, NewBody, flags=re.IGNORECASE)


# with open("Outputs\\test.txt" , "w", encoding="latin1") as file:
#     file.write(NewBody)

