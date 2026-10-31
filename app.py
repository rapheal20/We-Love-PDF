from flask import *
from fileinput import filename
from werkzeug.utils import secure_filename
import os

from MergePDF import MergePDFFunc

app = Flask(__name__)

FILES_DIRECTORY = os.path.abspath("./AppOutputs")

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
        return render_template("DownloadPage.html", outputType=outputType)

@app.route('/SplitPDF', methods=["GET", "POST"])
def SplitPDF():
    return render_template("SplitPDF.html")

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