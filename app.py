from flask import *
from fileinput import filename
from werkzeug.utils import secure_filename

app = Flask(__name__)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/MergePDF', methods=["GET", "POST"])
def MergePDF():
    filename = None

    if request.method == "GET":
        return render_template("MergePDF.html", filename=filename)
    elif request.method == "POST":
        f = request.files['file']
        filename = secure_filename(f.filename)
        f.save(filename)
        return render_template("MergePDF.html", filename=filename)


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