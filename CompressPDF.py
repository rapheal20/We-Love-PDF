import re


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



pdf3 = "Inputs\\DataRepresentation2k26.pdf"

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
        # "Body" : str(ObjectData),
        "References" : referenceList,
        "StartOffset" : startOffset,
        "EndOffset" : endOffset,
        "Visited" : False
    }

# /Root 234 0 R

# r"\b(\d+)\s+(\d+)\s+R"
#\s* represents no or more spaces
trailerFindString = r"/\s*Root\s+(\d+)\s+(\d+)\s+R"
TrailerObj = re.search(trailerFindString, PDF_Data, flags=re.IGNORECASE)

RootID = TrailerObj.group(1)

# print(RootID)
# CompareID = RootID
# CompareRef = [RootID]
# for Obj in Objects_List:
#     for ref in CompareRef:
#         print(CompareRef)
#         if Obj["ObjectID"] == ref:
#             if not Obj["Visited"]:
#                 Obj['Visited'] = True
#                 CompareRef = Obj["References"]




# ObjRefs = Objects_List[RootID]["References"]
# for ref in ObjRefs:
#     # refCount = 0
#     if not Objects_List[ref]["Visited"]:
#         Objects_List[ref]["Visited"] = True
#         ObjRefs += Objects_List[ref]["References"]
#         ObjRefs = list(set(ObjRefs))
#         ObjRefs.remove(ref)
        # print(ObjRefs)
        # if refCount == len(ObjRefs):
            
# for j in Objects_List.values():
#     print(j["ObjectID"],j["References"], j["Visited"])


# print(PDF_Data[TrailerOffset:])


# print(Objects_List)

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

        child_refs = Objects_List[current_id].get("references", [])
        # gets the references of the current object

        for ref_id in child_refs:
            if ref_id not in visited:
                queue.append(ref_id)
        #checks if each of those refs exist in visited, if they dont then it appends it to queue
        #Working behind it, ensure if some id is visited then it is not checked again


print(visited)

    