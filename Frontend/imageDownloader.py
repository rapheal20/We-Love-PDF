import requests as rq
from bs4 import BeautifulSoup as bs
import html5lib


url = "https://www.ilovepdf.com/"
data_res = rq.get(url)
format_res = bs(data_res.content, 'html5lib')

divs_res = format_res.findAll('div', attrs = {'class':"tools__item"})


features = [

]

for oneDiv in divs_res:
    # oneDiv = divs_res[0]
    try:
        svgIMG = oneDiv.find('div', attrs = {'class': "tools__item__icon"})
        svgData = svgIMG.decode_contents()
        functionName = str((oneDiv.find('h3')).decode_contents())
        filename = "IMAGES\\" + (functionName.replace(" ","_")) + ".svg"
        filename = filename.replace("/","_")
        # print(filename)
        catagory_name = oneDiv['data-category']

        # print(catagory_name)
        with open(filename, "w", encoding="utf-8") as file:
            file.write(svgData)


        features.append({"img" : filename, "catagory": catagory_name})
    except:
        print("error")
print(features)