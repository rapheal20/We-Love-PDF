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

user_home = os.path.expanduser('~')

BASE_DIR = f"{user_home}/WeLovePDF_Storage"

os.makedirs(BASE_DIR, exist_ok=True)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/MergePDF', methods=["GET", "POST"])
def MergePDF():
    if request.method == "GET":
        return render_template("MergePDF.html")

    elif request.method == "POST":
        files = request.files.getlist("files")
        savedNames = []
        for i, file in enumerate(files):
            filename = os.path.splitext(secure_filename(file.filename))[0] or f"upload_{i}"
            fullPath = os.path.join(BASE_DIR, f"{filename}.pdf")
            fullPath = os.path.normpath(fullPath)
            file.save(fullPath)
            savedNames.append(filename)

        fileQuery = ",".join(savedNames)

        outputType = "merged PDF"
        return render_template("DownloadPage.html", outputType=outputType, convertUrl=url_for("convert", tool="MergePDF", files=fileQuery))

@app.route('/SplitPDF', methods=["GET", "POST"])
def SplitPDF():
    if request.method == "GET":
            return render_template("SplitPDF.html")
    
    elif request.method == "POST":
        file = request.files["files"]

        try:
            page = int(request.form["page"])
        except:
            return "Page must be a number", 400
        
        filename = os.path.splitext(secure_filename(file.filename))[0] or "upload"
        fullPath = os.path.join(BASE_DIR, f"{filename}.pdf")
        fullPath = os.path.normpath(fullPath)
        file.save(fullPath)

        outputType = "PDF"
        return render_template("DownloadPage.html", outputType=outputType, convertUrl=url_for("convert", tool="SplitPDF", file=filename, page=page))

@app.route('/CompressPDF', methods=["GET", "POST"])
def CompressPDF():
    if request.method == "GET":
        return render_template("CompressPDF.html")

    elif request.method == "POST":
        file = request.files["files"]
        
        filename = os.path.splitext(secure_filename(file.filename))[0] or "upload"
        fullPath = os.path.join(BASE_DIR, f"{filename}.pdf")
        fullPath = os.path.normpath(fullPath)
        file.save(fullPath)

        outputType = "Compressed PDF"
        return render_template("DownloadPage.html", outputType=outputType, convertUrl=url_for("convert", tool="CompressPDF", file=filename))

@app.route('/PDFToWord', methods=["GET", "POST"])
def PDFToWord():
    if request.method == "GET":
        return render_template("PDFToWord.html")

    elif request.method == "POST":
        file = request.files["files"]
        
        filename = os.path.splitext(secure_filename(file.filename))[0] or "upload"
        fullPath = os.path.join(BASE_DIR, f"{filename}.pdf")
        fullPath = os.path.normpath(fullPath)
        file.save(fullPath)

        outputType = ".docx file"
        return render_template("DownloadPage.html", outputType=outputType, convertUrl=url_for("convert", tool="PDFToWord", file=filename))

@app.route('/PDFToPowerPoint', methods=["GET", "POST"])
def PDFToPowerPoint():
    if request.method == "GET":
        return render_template("PDFToPowerPoint.html")

    elif request.method == "POST":
        file = request.files["files"]
        filename = os.path.splitext(secure_filename(file.filename))[0] or "upload"
        fullPath = os.path.join(BASE_DIR, f"{filename}.pdf")
        fullPath = os.path.normpath(fullPath)
        file.save(fullPath)

        outputType = ".pptx file"
        return render_template("DownloadPage.html", outputType=outputType, convertUrl=url_for("convert", tool="PDFToPowerPoint", file=filename))

@app.route('/OCRPDF', methods=["GET", "POST"])
def OCRPDF():
    if request.method == "GET":
        return render_template("OCRPDF.html")

    elif request.method == "POST":
        file = request.files["files"]
        
        filename = os.path.splitext(secure_filename(file.filename))[0] or "upload"
        fullPath = os.path.join(BASE_DIR, f"{filename}.pdf")
        fullPath = os.path.normpath(fullPath)
        file.save(fullPath)

        outputType = "text file"
        return render_template("DownloadPage.html", outputType=outputType, convertUrl=url_for("convert", tool="OCRPDF", file=filename))

@app.route("/WorkInProgress")
def WorkInProgress():
    return render_template("WorkInProgress.html")

@app.route('/download/<filename>')
def download(filename):
    try:
        return send_from_directory(BASE_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return "The processed file has expired or was cleared from storage. Please try processing it again.", 404

TOOLS = {
    "MergePDF": MergePDFFunc,
    "SplitPDF": SplitPDFFunc,
    "CompressPDF": PDFCompressFunc,
    "PDFToWord": PDFToWordFunc,
    "PDFToPowerPoint": PDFToPowerPointFunc,
    "OCRPDF": OCRPDFFunc
}

@app.route('/convert/<tool>')
def convert(tool):
    func = TOOLS.get(tool)

    fileParam = request.args.get("files", "") or request.args.get("file", "")
    if not fileParam:
        return jsonify(error="File not found. Please upload it again."), 404

    filenames = fileParam.split(",")
    paths = [os.path.join(BASE_DIR, f"{name.strip()}.pdf") for name in filenames]

    for path in paths:
        if not os.path.isfile(path):
            return jsonify(error="File not found. Please upload it again."), 404
    
    try:
        if tool == "MergePDF":
            outputs = func(*paths)
        elif tool == "SplitPDF":
            page = int(request.args.get("page", 1))
            outputs = func(paths[0], page)
        else:
            outputs = func(paths[0])
            
        return jsonify(files=[os.path.basename(p) for p in outputs])
    except Exception as e:
        raise e