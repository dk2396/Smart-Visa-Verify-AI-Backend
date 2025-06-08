# Updated Flask backend using Google Gemini Flash 2.0 for document field extraction and comparison

import os
import json
from flask import Flask, request, jsonify
from PIL import Image
from datetime import datetime

from flask_cors import CORS
from google import genai
import base64
import io
import re

app = Flask(__name__)
CORS(app, resources={r"/validate-documents": {"origins": "*"},r"/check-timatic": {"origins": "*"}})  # or replace * with "http://localhost:3000"

# --- Configure Gemini API Key ---
GEMINI_API_KEY = "YOUR_API_KEY_HERE"
# Updated Flask backend using Google Gemini Flash 2.0 for document field extraction and comparison

client = genai.Client(api_key="your api key")

# --- Gemini Prompt Generation ---
def generate_gemini_prompt(doc_type):
    prompt = f"""
You are a document understanding expert. Extract the following fields from the uploaded image of a {doc_type} document:

- fullName
- passportNumber
- documentExpiryDate (for visa, this refers to the visa expiry date)

For visa documents:
- visaType
- Validate document authenticity based on structure and field completeness.
- Respond with "isAuthentic": "yes" or "no" and a brief "authenticityReason".

Respond in compact JSON , without any explanations
for doc type passport dont include authenticityReason and isAuthentic.
"""
    return prompt.strip()

# --- Send Image and Prompt to Gemini ---
def extract_fields_with_gemini(image_path, doc_type):

    prompt = generate_gemini_prompt(doc_type)

    image = client.files.upload(file=image_path)

    try:
        response = client.models.generate_content(
        model="gemini-2.5-flash-preview-05-20",
        contents=[image, prompt],
        )
        text = response.text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group(0).strip()) if match else {"error": "Invalid JSON from model", "raw": text}
    except Exception as e:
        return {"error": str(e)}

# --- Date Normalization ---
def normalize_date(date_str):
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except:
            continue
    return date_str

# --- Field Comparison ---
def compare_passport_and_visa(passport, visa):
    issues = []

    if "error" in passport:
        issues.append("Passport parsing failed")
    if "error" in visa:
        issues.append("Visa parsing failed")

    if not issues:
        if passport.get("fullName") and visa.get("fullName") and \
                passport["fullName"].lower() not in visa["fullName"].lower():
            issues.append("Full name mismatch")

        if passport.get("passportNumber") and visa.get("passportNumber") and \
                passport["passportNumber"] != visa["passportNumber"]:
            issues.append("Passport number mismatch")

        if visa.get("documentExpiryDate"):
            try:
                expiry_date = datetime.strptime(normalize_date(visa["documentExpiryDate"]), "%Y-%m-%d")
                if expiry_date < datetime.now():
                    issues.append("Visa is expired")
            except:
                issues.append("Invalid visa expiry date format")

    return {
        "passport_fields": passport,
        "visa_fields": visa,
        "issues": issues,
        "status": "Matched" if not issues else "Mismatch Found"
    }

# --- API Endpoint ---
@app.route("/validate-documents", methods=["POST"])
def validate_documents():
    if 'passport' not in request.files or 'visa' not in request.files:
        return jsonify({"error": "Missing passport or visa files"}), 400

    passport_img = request.files['passport']
    visa_img = request.files['visa']
    passport_path= os.path.join("uploads",passport_img.filename)
    visa_path = os.path.join("uploads", visa_img.filename)
    passport_img.save(passport_path)
    visa_img.save(visa_path)



    passport_fields = extract_fields_with_gemini(passport_path, "passport")
    visa_fields = extract_fields_with_gemini(visa_path, "visa")

    result = compare_passport_and_visa(passport_fields, visa_fields)
    os.remove(passport_path)
    os.remove(visa_path)
    return jsonify(result)

# --- Run Flask App ---
if __name__ == "__main__":
    app.run(debug=True, port=5001)



