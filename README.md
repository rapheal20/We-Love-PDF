## We love PDF
We love PDF is a complete recreation of the website "I love PDF. It is being coded by Anael and Rapheal.

This project was initally planned as a website, but while hosting we realized the limitations of free hosting services like vercel. That's why, now it is an application that runs locally on your computer. A release will be added soon.

Vercel only allows files upto 4 MB to be uploaded. That's why, only files upto 4 MB can be processed on the website,but heavier files can be processed by runing the program locally. 

To make this challenging, we have not used any libraries except default python ones. We have done direct implementation of libraries such as PyPDF2 by parsubg abd editing the PDF source code. Due to this, this project has helped us learn how complicated and well made the PDF file structure actually is. Sometimes the features written by us are buggy as well, because we have not covered all edge cases but we are fixing any bugs/issues we find. 

## Overview
# Features: 
1. Merge PDF (Done by Rapheal)
2. Split PDF (Done by Anael)
3. Compress PDF (Done by Rapheal)
4. PDF to Word (Done by Anael)
5. PDF to PowerPoint (Done by Rapheal)
6. PDF to Excel (Done by Rapheal)
7. Word to PDF (Work in progress)
8. PowerPoint to PDF (Work in progress)
9. Excel to PDF (Work in progress)
10. Edit PDF (Work in progress)
11. PDF to JPG (Done by Rapheal)
12. JPG to PDF (Work in progress)
13. Sign PDF (Work in progress)
14. Watermark (Done by Rapheal)
15. Rotate PDF (Work in progress)
16. HTML to PDF (Work in progress)
17. Unlock PDF (Work in progress)
18. Protect PDF (Work in progress)
19. Organize PDF (Done by Rapheal)
20. PDF to PDF/A (Work in progress)
21. Repair PDF (Work in progress)
22. Page numbers (Done by Rapheal)
22. Scan to PDF (Work in progress)
23. OCR PDF (Done by Anael)
24. Compare PDF (Work in progress)
25. Redact PDF (Work in progress)
26. Crop PDF (Work in progress)
27. PDF Forms (Work in progress)
28. AI summarizer (Work in progress)
29. Translate PDF (Work in progress)
30. PDF to Markdown (Work in progress)

The specific details of what each feature does can be found in their description on the website's homepage. 

## Technologies Used
* **Python and Flask:** Backend server and Advanced libraries for calculations.
* **HTML & CSS:** Frontend design and user interface.

## How to Run Locally

To run this project on your local machine, follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rapheal20/We-Love-PDF
   cd We-Love-PDF
   ```

2. **Create and activate a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the Flask application:**
   ```bash
   flask run
   ```
   *The application should now be running locally at `http://127.0.0.1:5000/`.*

---

---
## AI Usage
AI was used for:

    * Debugging errors.
    * Research purposes (as an alternative to Google Search).
    * Snippets of code of completely new concepts.
    * No direct copy-pasting without understanding.
    * All code is mostly written by hand. 

---

This project is made as part of Third Space event in Hack Club. 


command to make exe: 
pyinstaller --noconsole --onefile --hidden-import=cgi --add-data "templates;templates" --add-data "static;static" desktop.py