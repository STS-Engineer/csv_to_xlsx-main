from flask import Flask, request, send_file, render_template_string
import pandas as pd
import os
import chardet
import time
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from PyPDF2 import PdfReader
import re
import logging
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Directory for output files
OUTPUT_DIR = "outputs"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

ALLOWED_EXTENSIONS = {'csv', 'pdf'}

# HTML Template for Upload Form
UPLOAD_FORM_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>CSV Transformer</title>
    <style>
      body {
        font-family: 'Arial', sans-serif;
        background-color: #f4f7f6;
        margin: 0;
        padding: 0;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
      }
      .container {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        text-align: center;
        width: 80%;
        overflow: auto;
        max-height: 90vh;
      }
      h1 {
        color: #333;
        font-size: 24px;
        margin-bottom: 20px;
      }
      p {
        font-size: 16px;
        color: #555;
        margin-bottom: 20px;
      }
      form {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 15px;
      }
      input[type="file"], input[type="text"], input[type="submit"], a.download-btn {
        padding: 12px;
        font-size: 16px;
        border: 1px solid #ddd;
        border-radius: 5px;
        outline: none;
        transition: all 0.3s ease-in-out;
        width: 100%;
        max-width: 400px;
        margin: 0 auto;
      }
      input[type="file"], input[type="text"] {
        background-color: #f8f9fa;
      }
      input[type="file"]:hover, input[type="text"]:hover {
        background-color: #e9ecef;
      }
      input[type="submit"], a.download-btn {
        background-color: #28a745;
        color: white;
        cursor: pointer;
        border: none;
      }
      input[type="submit"]:hover, a.download-btn:hover {
        background-color: #218838;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
      }
      table th, table td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
      }
      table th {
        background-color: #28a745;
        color: white;
      }
      table tbody tr:nth-child(odd) {
        background-color: #f9f9f9;
      }
      table tbody tr:hover {
        background-color: #e9ecef;
      }
      .scrollable {
        overflow-x: auto;
        margin-top: 20px;
        max-height: 300px;
      }
      footer {
        margin-top: 20px;
        color: #888;
        font-size: 14px;
      }
      img {
        max-width: 300px;
        margin-bottom: 20px;
      }
      select.select-btn {
        appearance: none;
        background-color: #007bff;
        color: white;
        font-size: 16px;
        padding: 12px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        text-align: center;
        width: 100%;
        max-width: 400px;
        margin: 10px auto;
      }
      select.select-btn:hover {
        background-color: #0056b3;
      }
    </style>
    <script>
      function updateCustomerCode() {
        const customerDropdown = document.getElementById('customer_name');
        const customerCodeInput = document.getElementById('customer_code');
        const selectedOption = customerDropdown.options[customerDropdown.selectedIndex];
        const customerCode = selectedOption.getAttribute('data-code');
        customerCodeInput.value = customerCode ? customerCode : '';
      }
    </script>
  </head>
  <body>
    <div class="container">
    <img src="/static/logo-avocarbon (1).png" alt="Logo">
      <h1>CSV Transformation Tool</h1>
      <p>Upload your CSV file or PDF file and enter the customer code to transform your data.</p>
      <form action="/convert" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".csv,.pdf" required>
        <select name="customer_name" class="btn select-btn" id="customer_name" onchange="updateCustomerCode()" required>
          <option value="" disabled selected>Select Customer Name</option>
          <option value="INTEVA PRODUCTS, LLC C00241" data-code="C00241">INTEVA PRODUCTS, LLC C00241</option>
          <option value="Inteva Esson C00410" data-code="C00410">Inteva Esson C00410</option>
          <option value="VALEO NEVERS C00409" data-code="C00409">VALEO NEVERS C00409</option>
          <option value="VALEO ILUMINACION S.A.U C00125" data-code="C00125">VALEO ILUMINACION S.A.U C00125</option>
          <option value="VALEO SISTEMAS AUTOMOTIVOS BRESIL C00072" data-code="C00072">VALEO SISTEMAS AUTOMOTIVOS BRESIL C00072</option>
          <option value="NIDEC SPAIN MOTORS AND ACTUATORS C00050" data-code="C00050">NIDEC SPAIN MOTORS AND ACTUATORS C00050</option>
          <option value="VALEO NORTH AMERICA INC.(WIPERS) C00303" data-code="C00303">VALEO NORTH AMERICA INC.(WIPERS) C00303</option>
          <option value="VALEO AUTOSYSTEMY SP Z.O.O C00250" data-code="C00250">VALEO AUTOSYSTEMY SP Z.O.O C00250</option>
          <option value="NIDEC MOTORS & ACTUATORS (GERMANY) GmbH C00113" data-code="C00113">NIDEC MOTORS & ACTUATORS (GERMANY) GmbH C00113</option>
          <option value="VALEO SHARED SERVICE CENTER C00132" data-code="C00132">VALEO SHARED SERVICE CENTER C00132</option>
          <option value="NIDEC MOTORS & ACTUATORS (POLAND)Sp C00126" data-code="C00126">NIDEC MOTORS & ACTUATORS (POLAND)Sp C00126</option>
        </select>
        <input type="text" name="customer_code" id="customer_code" placeholder="Customer Code" readonly required>
        <input type="submit" value="Transform">
      </form>
      {% if summary_table %}
      <div class="scrollable">
        <h2>Transformed Data Preview</h2>
        <table>{{ summary_table|safe }}</table>
      </div>
      {% endif %}
      {% if show_download %}
      <a href="/download/{{ download_path }}" class="btn download-btn">Download Transformed CSV</a>
      {% endif %}
      <footer>
        &copy; 2024 CSV Transformation Tool. All rights reserved. powered by STS
      </footer>
    </div>
  </body>
</html>
"""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_encoding(file):
    raw_data = file.read()
    result = chardet.detect(raw_data)
    file.seek(0)
    return result['encoding']


def extract_before_date(line):
    """
    Extracts specific values (FORECAST, Backlog, Firm) before a date in a line of text.
    If none of these are found, extracts the first matching value before the date.
    """
    # Regex to capture any value before the date
    pattern = r"(.*?)\s+(\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})"
    match = re.search(pattern, line)

    if match:
        before_date = match.group(1).strip()  # Capture text before the date

        # Check for specific keywords
        keywords = ["FORECAST", "Backlog", "Firm"]
        for keyword in keywords:
            if keyword.lower() in before_date.lower():  # Case-insensitive check
                return keyword

        # If no keywords are found, return the first value
        return before_date

    return None  # Return None if no match found


# Return None if no relevant value found

def extract_date_and_number(text):
    # Pattern for dates in formats like MM/DD/YYYY, DD/MM/YYYY, or YYYY-MM-DD
    # Also captures the number immediately following the date.
    date_number_pattern = r"(\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})\s+(\d+(?:,\d{3})*)"

    # Find all occurrences of dates followed by numbers
    matches = re.findall(date_number_pattern, text)

    # Clean up numbers (remove commas and convert to integer)
    cleaned_matches = [(date, int(number.replace(",", ""))) for date, number in matches]

    return cleaned_matches


def parse_pdf(file):
    # Save the uploaded PDF to a temporary file
    temp_filename = secure_filename(file.filename)
    temp_filepath = os.path.join(OUTPUT_DIR, temp_filename)

    # Save the file temporarily
    file.save(temp_filepath)

    # Parse the PDF using PyPDF2
    with open(temp_filepath, 'rb') as pdf_file:
        reader = PdfReader(pdf_file)
        text = ''
        for page in reader.pages:
            text += page.extract_text() + '\n'

    # Remove temporary file after parsing
    os.remove(temp_filepath)

    return text

material_ref_map = {
  "53343086": "5503001138",
  "1001MR035": "5503001140",
  "W000024158": "5503001143",
  "W000037335": "5503001144",
  "W000035923": "5503002299",
  "53342696": "5503003594",
  "W000058808": "5503003595",
  "W000037397": "5503003675",
  "W000038990": "5503003722",
  "W151616": "5503003740",
  "W447251": "5503003895"
}


def process_pdf(file, customer_code, customer_name, material_ref_map, output_dir=None):
    """
    Parses a PDF file, extracts text, and transforms it into a structured DataFrame.
    If a material number matches a value in the material_ref_map, the corresponding
    REFEXTERNELU value is assigned.

    :param output_dir: Directory where the CSV file will be saved (default is current directory).
    """
    # If output_dir is not provided, default to the current working directory
    if output_dir is None:
        output_dir = os.getcwd()

    try:
        # Parse PDF to extract text
        text = parse_pdf(file)
    except Exception as e:
        raise ValueError(f"Failed to parse PDF file: {e}")

    data = []
    lines = text.split('\n')

    current_material = None
    current_statut = None
    keywords_pattern = re.compile(r"(forecast|backlog|firm)", re.IGNORECASE)
    one_week_ago = datetime.now() - timedelta(days=7)

    for line in lines:
        # Extract material number
        material_match = re.match(r"Material\s*[:\-]?\s*(\S+)", line)
        if material_match:
            current_material = material_match.group(1)

        # Match keywords to set initial status
        keyword_match = keywords_pattern.search(line)
        if keyword_match:
            current_statut = 4 if keyword_match.group(0).lower() in ['forecast', 'firm'] else 1

        # Extract dates and quantities
        if current_material:
            date_quantity_matches = re.findall(r"(\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})\s+([\d,]+)",
                                               line.strip())
            for date, quantity in date_quantity_matches:
                try:
                    # Try parsing the date in both formats
                    date_obj = datetime.strptime(date, "%d/%m/%Y" if '/' in date else "%d-%m-%Y")
                except ValueError:
                    try:
                        # If the first format fails, try mm/dd/yyyy
                        date_obj = datetime.strptime(date, "%m/%d/%Y")
                    except ValueError:
                        logging.warning(f"Skipping invalid date format: {date}")
                        continue

                # Format the date as dd/mm/yyyy
                formatted_date = date_obj.strftime("%d/%m/%Y")

                # Remove commas from the quantity
                cleaned_quantity = int(quantity.replace(',', ''))

                # Check if the date is older than a week
                if date_obj < one_week_ago:
                    statut = 1  # Set Statut to 1 if the date is more than a week old
                else:
                    statut = current_statut

                data.append({
                    'Material_No_Customer': current_material,
                    'Quantité': cleaned_quantity,
                    'LIVRFINLU': formatted_date,
                    'Statut': statut,
                    'REFEXTERNELU': material_ref_map.get(current_material, current_material)
                    # Default to material number if no match
                })

    # Validate extracted data
    if not data:
        raise ValueError("No valid data extracted from the PDF.")

    # Create DataFrame
    df = pd.DataFrame(data)
    df['TIERSLU'] = customer_code
    df['Libelle client'] = customer_name.split(" C")[0]  # Extract customer name without code
    df['Tiers livré'] = customer_code
    df['Date debut Validité'] = "20190101"

    # Reorder columns
    df = df[['TIERSLU', 'Material_No_Customer', 'Quantité', 'LIVRFINLU', 'Libelle client', 'Statut', 'Tiers livré',
             'REFEXTERNELU', 'Date debut Validité']]

    # Save transformed data to CSV
    output_filename = f"{customer_code}.csv"
    output_path = os.path.join(output_dir, output_filename)

    df.to_csv(output_path, index=False, sep=';')
    logging.info(f"Data saved to {output_path}")
    return df, output_filename
def safe_convert_calendar_week_to_date(cw_string):
    """
    Converts a calendar week string (e.g., 'CW 07/2025') to a date string in the format 'D/M/Y'.
    If conversion fails or the format is unexpected, returns the original value.
    """
    try:
        # Check if the input is in the 'CW xx/yyyy' format
        if isinstance(cw_string, str) and cw_string.startswith('CW'):
            week_number, year = map(int, cw_string.replace("CW", "").strip().split("/"))
            first_day_of_year = datetime.strptime(f"{year}-01-01", "%Y-%m-%d")
            first_monday = first_day_of_year + timedelta(days=(7 - first_day_of_year.weekday()) % 7)
            date = first_monday + timedelta(weeks=week_number - 1)
            return date.strftime("%d/%m/%Y")
        else:
            # Return the original value if it's not in the expected format
            return cw_string
    except Exception as e:
        # Log the error and return the original value
        print(f"Error converting CW to date: {e}, input was: {cw_string}")
        return cw_string


def get_first_available_column(df, columns):
    for col in columns:
        if col in df.columns:
            return df[col]
    return None  # Return None if no column matches


def is_old_week(date_str):
    try:
        date_obj = pd.to_datetime(date_str, format='%d/%m/%Y', errors='coerce')
        if pd.isna(date_obj):
            return False

        # Get current week number and the week number of the date
        current_week = datetime.datetime.now().isocalendar()[1]
        date_week = date_obj.isocalendar()[1]
        return date_week < current_week
    except Exception as e:
        return False  # Assume it's not an old week if any error occurs




def process_csv(file, customer_code, customer_name):
    encoding = detect_encoding(file)
    df = pd.read_csv(file, delimiter=';', encoding=encoding, on_bad_lines='skip')

    # Remove rows where specific column values match their corresponding headers
    if all(col in df.columns for col in ['Material_No_Customer', 'Delivery_Date', 'Release_Status', 'Purchase_Order_No']):
        df = df[~(
            (df['Material_No_Customer'] == 'Material_No_Customer') &
            (df['Delivery_Date'] == 'Delivery_Date') &
            (df['Release_Status'] == 'Release_Status') &
            (df['Purchase_Order_No'] == 'Purchase_Order_No')
        )]

    # Transform the DataFrame (date formatting, etc.)
    if 'DateUntil' in df.columns:
        df['DateUntil'] = pd.to_datetime(df['DateUntil'], errors='coerce', dayfirst=True).dt.strftime('%d/%m/%Y')
    if 'Despatch_Qty' in df.columns:
        # Skip conversion, keep the values as they are (string format or whatever they are in CSV)
        pass
    if 'Delivery_Date' in df.columns:
        df['Delivery_Date'] = df['Delivery_Date'].apply(
            lambda x: safe_convert_calendar_week_to_date(x) if isinstance(x, str) and x.startswith('CW') else x)
    # Remove rows where 'Despatch_Qty' or 'DespatchQty' equals 0
    # Delete rows where 'Despatch_Qty' or 'DespatchQty' equals 0
    if 'Despatch_Qty' in df.columns or 'DespatchQty' in df.columns:
        def clean_and_convert(value):
            try:
                # Remove all non-numeric characters except '.' and ','
                cleaned = re.sub(r'[^\d.,]', '', str(value))
                # If both '.' and ',' are present, assume European format (e.g., '3.780,00')
                if '.' in cleaned and ',' in cleaned:
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                elif ',' in cleaned:
                    cleaned = cleaned.replace(',', '.')
                return float(cleaned)
            except (ValueError, TypeError):
                return None

        # Apply the cleaning and conversion function
        if 'Despatch_Qty' in df.columns:
            df['Despatch_Qty'] = df['Despatch_Qty'].apply(clean_and_convert)
        if 'DespatchQty' in df.columns:
            df['DespatchQty'] = df['DespatchQty'].apply(clean_and_convert)

        # Remove rows where 'Despatch_Qty' or 'DespatchQty' equals 0 or conversion failed (None)
        df = df[
            ~(
                (df['Despatch_Qty'] == 0) if 'Despatch_Qty' in df.columns else False
            ) &
            ~(
                (df['DespatchQty'] == 0) if 'DespatchQty' in df.columns else False
            )
            ]

    if 'Status' in df.columns or 'Release_Status' in df.columns:
        status_column = 'Status' if 'Status' in df.columns else 'Release_Status'
        df[status_column] = df[status_column].apply(
            lambda x: 4 if str(x).lower() in ['firm', 'forecast'] else (1 if str(x).lower() == 'backlog' else x)
        )

    # Add condition to set Statut based on LIVRFINLU being an old week
    if 'LIVRFINLU' in df.columns:
        df['Statut'] = df.apply(
            lambda row: 1 if is_old_week(row['LIVRFINLU']) else 4,  # Set 1 for old week, 4 for not old week
            axis=1
        )

    # Create the transformed DataFrame
    transformed_df = pd.DataFrame({
        'TIERSLU': customer_code,
        'Material_No_Customer': get_first_available_column(df, ['Material_No_Customer', 'Material']),
        'Quantité': get_first_available_column(df, ['Despatch_Qty', 'DespatchQty']),
        'LIVRFINLU': get_first_available_column(df, ['Delivery_Date', 'DateUntil']),
        'Libelle client': customer_name.split(" C")[0],
        'Statut': get_first_available_column(df, ['Release_Status', 'Status']),
        'Tiers livré': customer_code,
        'REFEXTERNELU': get_first_available_column(df, ['Purchase_Order_No', 'PONumber']),
        'Date debut Validité': "20190101",
    })

    # Remove '.0' from 'Quantité' column if it exists (for display purposes)
    if 'Quantité' in transformed_df.columns:
        transformed_df['Quantité'] = transformed_df['Quantité'].apply(
            lambda x: str(int(float(str(x).replace(',', '.')))) if pd.notnull(x) and str(x).replace(',', '.').replace(
                '.', '').isdigit() else x
        )
    if 'Statut' in transformed_df.columns:
        transformed_df['Statut'] = transformed_df['Statut'].apply(
            lambda x: str(int(float(str(x).replace(',', '.')))) if pd.notnull(x) and str(x).replace(',', '.').replace(
                '.', '').isdigit() else x
        )

    # Define the output file path
    timestamp = int(time.time())
    output_filename = secure_filename(f"{customer_code}.csv")
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    # Save the transformed DataFrame to a CSV file
    transformed_df.to_csv(output_path, index=False, sep=';')

    return transformed_df, output_filename


@app.route('/')
def index():
    return render_template_string(UPLOAD_FORM_HTML, summary_table=None, show_download=False)


@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files or 'customer_code' not in request.form or 'customer_name' not in request.form:
        return "Missing file, customer code, or customer name", 400

    # Get the uploaded file and customer details
    file = request.files['file']
    customer_code = request.form['customer_code']
    customer_name = request.form['customer_name']  # Get the customer name from the form

    if not file.filename:
        return "No file selected", 400

    try:
        # Determine file type and process accordingly
        if file.filename.lower().endswith('.pdf'):
            transformed_data, output_filename = process_pdf(file, customer_code, customer_name, material_ref_map)
        elif file.filename.lower().endswith('.csv'):
            transformed_data, output_filename = process_csv(file, customer_code, customer_name)
        else:
            return "Invalid file type. Please upload a CSV or PDF file.", 400

        # Display the first 20 rows of the transformed data as HTML
        transformed_table_html = transformed_data.head(20).to_html(classes='table', index=False)

        # Return the transformed data and a download link for the CSV
        return render_template_string(
            UPLOAD_FORM_HTML,
            summary_table=transformed_table_html,
            show_download=True,
            download_path=output_filename
        )
    except Exception as e:
        return f"Error processing the file: {e}", 500


# Function to handle file download (if the user clicks the download button)
@app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True, port=5000)
