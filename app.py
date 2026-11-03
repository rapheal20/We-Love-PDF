from flask import *
from werkzeug.utils import secure_filename
import os
import tempfile
import sys

from MergePDF import MergePDFFunc
from SplitPDF import SplitPDFFunc
from CompressPDF import PDFCompressFunc
from PDFToWord import PDFToWordFunc
from PDFToPowerPoint import PDFToPowerPointFunc
from OCRPDF import OCRPDFFunc

app = Flask(__name__)

'''if getattr(sys, 'frozen', False):
    BASE_DIR = tempfile.gettempdir()
else:
    # If running locally during development, use project folders
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
'''

BASE_DIR = os.path.join(os.path.expanduser('~'), 'WeLovePDF_Storage')

os.makedirs(BASE_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/MergePDF', methods=["GET", "POST"])
def MergePDF():
    if request.method == "GET":
        return render_template("MergePDF.html")

    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = BASE_DIR

        files = request.files.getlist("files")
        savedPaths = []

        for file in files:
            filename = secure_filename(file.filename)
            fullPath = os.path.join(path, filename)
            file.save(fullPath)
            savedPaths.append(fullPath)

        outputPaths = MergePDFFunc(*savedPaths)

        if not outputPaths:
            return "An error occurred while processing your PDF files.", 500
                
        outputType = "merged PDF"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route('/SplitPDF', methods=["GET", "POST"])
def SplitPDF():
    if request.method == "GET":
            return render_template("SplitPDF.html")
    
    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = BASE_DIR

        file = request.files["files"]

        try:
            page = int(request.form["page"])
        except:
            return "Page must be a number", 400
        
        filename = secure_filename(file.filename)
        fullPath = os.path.join(path, filename)
        file.save(fullPath)

        outputPaths = SplitPDFFunc(fullPath, page)

        if not outputPaths:
            return "An error occurred while processing your PDF files.", 500
            
        outputType = "PDF"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route('/CompressPDF', methods=["GET", "POST"])
def CompressPDF():
    if request.method == "GET":
        return render_template("CompressPDF.html")

    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = BASE_DIR

        file = request.files["files"]
        
        filename = secure_filename(file.filename)
        fullPath = os.path.join(path, filename)
        file.save(fullPath)

        outputPaths = PDFCompressFunc(fullPath)

        if not outputPaths:
            return "An error occurred while processing your PDF files.", 500

        outputType = "Compressed PDF"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route('/PDFToWord', methods=["GET", "POST"])
def PDFToWord():
    if request.method == "GET":
        return render_template("PDFToWord.html")

    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = BASE_DIR

        file = request.files["files"]
        
        filename = secure_filename(file.filename)
        fullPath = os.path.join(path, filename)
        file.save(fullPath)

        outputPaths = PDFToWordFunc(fullPath)

        if not outputPaths:
            return "An error occurred while processing your PDF files.", 500

        outputType = ".docx file"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route('/PDFToPowerPoint', methods=["GET", "POST"])
def PDFToPowerPoint():
    if request.method == "GET":
        return render_template("PDFToPowerPoint.html")

    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = BASE_DIR

        file = request.files["files"]
        
        filename = secure_filename(file.filename)
        fullPath = os.path.join(path, filename)
        
        #file.save(fullPath)

        with open(fullPath, "wb") as f:
            while True:
                chunk = file.stream.read(16384)
                if not chunk:
                    break
                f.write(chunk)

        outputPaths = PDFToPowerPointFunc(fullPath)

        if not outputPaths:
            return "An error occurred while processing your PDF files.", 500

        outputType = ".pptx file"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route('/OCRPDF', methods=["GET", "POST"])
def OCRPDF():
    if request.method == "GET":
        return render_template("OCRPDF.html")

    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = BASE_DIR

        file = request.files["files"]
        
        filename = secure_filename(file.filename)
        fullPath = os.path.join(path, filename)
        file.save(fullPath)

        outputPaths = OCRPDFFunc(fullPath)

        outputType = "text file"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route("/WorkInProgress")
def WorkInProgress():
    return render_template("WorkInProgress.html")

@app.route('/download/<filename>')
def download(filename):
    try:
        return send_from_directory(BASE_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return "The processed file has expired or was cleared from temporary storage. Please try processing it again.", 404