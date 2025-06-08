from flask import Flask, request, jsonify
from mrz.checker.td3 import TD3CodeChecker  # Passport
from mrz.checker.td2 import TD2CodeChecker
from mrz.checker.mrvb import MRVBCodeChecker # Visa
from datetime import datetime, date
from flask_cors import CORS

from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/validate-mrz": {"origins": "*"},r"/check-timatic": {"origins": "*"}})  # or replace * with "http://localhost:3000"



def parse_passport_mrz(mrz_string):
    try:
        mrz = TD3CodeChecker(mrz_string)
        return {
            "passport_number": mrz.document_number,
            "full_name": f"{mrz.fields('given_names')} {mrz.fields('surname')}".strip(),
            "expiry_date": format_date_field(mrz.fields('expiry_date')),
            "nationality": mrz.nationality,
        }
    except Exception as e:
        return {"error": f"Passport MRZ parse error: {str(e)}"}

def format_date_field(date_field):
    if isinstance(date_field, (datetime, date)):
        return date_field.strftime("%Y-%m-%d")
    elif isinstance(date_field, str):
        try:
            # Convert from YYMMDD to YYYY-MM-DD
            dt = datetime.strptime(date_field, "%y%m%d")
            return dt.strftime("%Y-%m-%d")
        except:
            return None
    return None

def parse_passport_mrz(mrz_string):
    try:
        mrz = TD3CodeChecker(mrz_string)
        fields = mrz.fields()
        return {
            "passport_number": fields.document_number,
            "full_name": f"{fields.name} {fields.surname}".strip(),
            "expiry_date": format_date_field(fields.expiry_date),
            "nationality": fields.nationality,
        }
    except Exception as e:
        return {"error": f"Passport MRZ parse error: {str(e)}"}

def parse_visa_mrz(mrz_string):
    try:
        mrz = MRVBCodeChecker(mrz_string)
        fields = mrz.fields()
        return {
            "passport_number": fields.document_number,
            "full_name": f"{fields.name} {fields.surname}".strip(),
            "expiry_date": format_date_field(fields.expiry_date),
            "nationality": fields.nationality,
            "issuing_country" : fields.country
        }
    except Exception as e:
        return {"error": f"Visa MRZ parse error: {str(e)}"}


def compare_fields(passport_data, visa_data):
    result = {}
    for field in ["passport_number", "full_name"]:
        if field not in passport_data or field not in visa_data:
            result[field] = "field missing"
        elif passport_data[field] == visa_data[field]:
            result[field] = "matched"
        else:
            result[field] = f"unmatched (passport: {passport_data[field]}, visa: {visa_data[field]})"

    # Expiry date check only for visa
    try:
        expiry_date = datetime.strptime(visa_data["expiry_date"], "%Y-%m-%d")
        result["visa_expiry_valid"] = "valid" if expiry_date > datetime.now() else "expired"
    except:
        result["visa_expiry_valid"] = "invalid or missing"

    return result

@app.route("/validate-mrz", methods=["POST"])
def validate_mrz():
    data = request.get_json()
    passport_mrz = data.get("passport_mrz", "")
    visa_mrz = data.get("visa_mrz", "")

    passport_data = parse_passport_mrz(passport_mrz)
    visa_data = parse_visa_mrz(visa_mrz)

    if "error" in passport_data or "error" in visa_data:
        return jsonify({
            "status": "error",
            "passport_error": passport_data.get("error"),
            "visa_error": visa_data.get("error")
        }), 400

    comparison = compare_fields(passport_data, visa_data)

    return jsonify({
        "status": "success",
        "passport_data": passport_data,
        "visa_data": visa_data,
        "comparison_result": comparison
    })

@app.route("/check-timatic", methods=["POST"])
def check_timatic():
    data = request.get_json()
    nationality = data.get("nationality", "UNKNOWN")

    # Mock logic - always return visa required = true
    return jsonify({
        "nationality": nationality,
        "visa_required": True
    })

if __name__ == "__main__":
    app.run(debug=True)