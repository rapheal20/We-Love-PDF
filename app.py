from flask import *
from werkzeug.utils import secure_filename
import os
import tempfile

from MergePDF import MergePDFFunc
from SplitPDF import SplitPDFFunc
from CompressPDF import PDFCompressFunc
from PDFToWord import PDFToWordFunc
from PDFToPowerPoint import PDFToPowerPointFunc

app = Flask(__name__)

TEMP_DIR = tempfile.gettempdir()
OUTPUT_DIR = TEMP_DIR

# Uncomment for local running
# OUTPUT_DIR = "D:/CS related/Third Space/We-Love-PDF/AppOutputs" 

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/MergePDF', methods=["GET", "POST"])
def MergePDF():
    if request.method == "GET":
        return render_template("MergePDF.html")

    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = TEMP_DIR

        files = request.files.getlist("files")
        savedPaths = []

        for file in files:
            filename = secure_filename(file.filename)
            fullPath = os.path.join(path, filename)
            file.save(fullPath)
            savedPaths.append(fullPath)

        outputPaths = MergePDFFunc(*savedPaths)
                
        outputType = "merged PDF"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route('/SplitPDF', methods=["GET", "POST"])
def SplitPDF():
    if request.method == "GET":
            return render_template("SplitPDF.html")
    
    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = TEMP_DIR

        file = request.files["files"]

        try:
            page = int(request.form["page"])
        except:
            return "Page must be a number", 400
        
        filename = secure_filename(file.filename)
        fullPath = os.path.join(path, filename)
        file.save(fullPath)

        outputPaths = SplitPDFFunc(fullPath, page)
            
        outputType = "PDF"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route('/CompressPDF', methods=["GET", "POST"])
def CompressPDF():
    if request.method == "GET":
        return render_template("CompressPDF.html")

    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = TEMP_DIR

        file = request.files["files"]
        
        filename = secure_filename(file.filename)
        fullPath = os.path.join(path, filename)
        file.save(fullPath)

        outputPaths = PDFCompressFunc(fullPath)

        outputType = "Compressed PDF"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route('/PDFToWord', methods=["GET", "POST"])
def PDFToWord():
    if request.method == "GET":
        return render_template("PDFToWord.html")

    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = TEMP_DIR

        file = request.files["files"]
        
        filename = secure_filename(file.filename)
        fullPath = os.path.join(path, filename)
        file.save(fullPath)

        outputPaths = PDFToWordFunc(fullPath)

        outputType = ".docx file"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route('/PDFToPowerPoint', methods=["GET", "POST"])
def PDFToPowerPoint():
    if request.method == "GET":
        return render_template("PDFToPowerPoint.html")

    elif request.method == "POST":
        #path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"
        path = TEMP_DIR

        file = request.files["files"]
        
        filename = secure_filename(file.filename)
        fullPath = os.path.join(path, filename)
        file.save(fullPath)

        outputPaths = PDFToPowerPointFunc(fullPath)

        outputType = ".pptx file"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(p) for p in outputPaths])

@app.route("/WorkInProgress")
def WorkInProgress():
    return render_template("WorkInProgress.html")

@app.route('/download/<filename>')
def download(filename):
    try:
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return "The processed file has expired or was cleared from temporary storage. Please try processing it again.", 404