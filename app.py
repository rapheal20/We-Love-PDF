from flask import *
from werkzeug.utils import secure_filename
import os

from MergePDF import MergePDFFunc
from SplitPDF import SplitPDFFunc

app = Flask(__name__)

OUTPUT_DIR = "D:/CS related/Third Space/We-Love-PDF/AppOutputs" 

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/MergePDF', methods=["GET", "POST"])
def MergePDF():
    if request.method == "GET":
        return render_template("MergePDF.html")

    elif request.method == "POST":
        path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"

        files = request.files.getlist("files")
        savedPaths = []

        for file in files:
            filename = secure_filename(file.filename)
            fullPath = os.path.join(path, filename)
            file.save(fullPath)
            savedPaths.append(fullPath)

        outputPath = MergePDFFunc(*savedPaths)
                
        outputType = "merged PDF"
        return render_template("DownloadPage.html", outputType=outputType, outputFiles=[os.path.basename(outputPath)])

@app.route('/SplitPDF', methods=["GET", "POST"])
def SplitPDF():
    if request.method == "GET":
            return render_template("SplitPDF.html")
    
    elif request.method == "POST":
        path = "D:/CS related/Third Space/We-Love-PDF/AppInputs"

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
    return render_template("CompressPDF.html")

@app.route('/PDFToWord', methods=["GET", "POST"])
def PDFToWord():
    return render_template("PDFToWord.html")

@app.route('/PDFToPowerPoint', methods=["GET", "POST"])
def PDFToPowerPoint():
    return render_template("PDFToPowerPoint.html")

@app.route("/WorkInProgress")
def WorkInProgress():
    return render_template("WorkInProgress.html")

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
