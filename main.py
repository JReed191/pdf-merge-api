from flask import Flask, request, send_file, jsonify
import requests
from PyPDF2 import PdfMerger

app = Flask(__name__)

@app.route("/merge", methods=["POST"])
def merge_pdfs():
    nec_url = request.json.get("nec_url")
    z_url = request.json.get("z_url")

    if not nec_url or not z_url:
        return jsonify({"error": "Missing file URLs"}), 400

    nec_file = "nec.pdf"
    z_file = "zclauses.pdf"
    merged_file = "merged_contract.pdf"

    with open(nec_file, "wb") as f:
        f.write(requests.get(nec_url).content)
    with open(z_file, "wb") as f:
        f.write(requests.get(z_url).content)

    merger = PdfMerger()
    merger.append(nec_file)
    merger.append(z_file)
    merger.write(merged_file)
    merger.close()

    return send_file(merged_file, as_attachment=True)

app.run(host='0.0.0.0', port=8080)
