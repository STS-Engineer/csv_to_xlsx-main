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
    pattern = r"(.*?)\s+(\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})"
    match = re.search(pattern, line)

    if match:
        before_date = match.group(1).strip()

        keywords = ["FORECAST", "Backlog", "Firm"]
        for keyword in keywords:
            if keyword.lower() in before_date.lower():
                return keyword

        return before_date

    return None


def extract_date_and_number(text):
    date_number_pattern = r"(\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})\s+(\d+(?:,\d{3})*)"
    matches = re.findall(date_number_pattern, text)
    cleaned_matches = [(date, int(number.replace(",", ""))) for date, number in matches]
    return cleaned_matches


def parse_pdf(file):
    temp_filename = secure_filename(file.filename)
    temp_filepath = os.path.join(OUTPUT_DIR, temp_filename)
    file.save(temp_filepath)

    with open(temp_filepath, 'rb') as pdf_file:
        reader = PdfReader(pdf_file)
        text = ''
        for page in reader.pages:
            text += page.extract_text() + '\n'

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


def iso_week_to_date(year, week):
    """Convert ISO year + week number to the Monday of that week as a datetime."""
    # %G = ISO year, %V = ISO week, %u = weekday (1=Monday)
    return datetime.strptime(f"{year}-W{week:02d}-1", "%G-W%V-%u")


def process_pdf(file, customer_code, customer_name, material_ref_map, output_dir=None):
    """
    Handles Valeo-style PDFs where:
    - Material reference is on lines like: N° de référence: W000026780
    - Delivery lines look like: 2025 w06 - 2025 w06   336   3410953 Prévision
      or with a date range where both weeks are the same or different
    - Status is 'Prévision' (forecast=4) or 'Arriéré' (backlog=1)
    - Also handles legacy dd/mm/yyyy date formats as a fallback
    """
    if output_dir is None:
        output_dir = os.getcwd()

    try:
        text = parse_pdf(file)
    except Exception as e:
        raise ValueError(f"Failed to parse PDF file: {e}")

    data = []
    lines = text.split('\n')

    current_material = None
    one_week_ago = datetime.now() - timedelta(days=7)

    # Pattern for Valeo week-based delivery lines:
    # e.g. "2025 w06 - 2025 w06 336 3410953 Prévision"
    # or   "2024 w47 - 2024 w48 1920 5393741 Prévision"
    # We take the END week as the delivery date
    week_line_pattern = re.compile(
        r"(\d{4})\s+w(\d{1,2})\s*-\s*(\d{4})\s+w(\d{1,2})\s+([\d,]+)\s+[\d,]+\s*(\S+)"
    )

    # Pattern for legacy dd/mm/yyyy date lines
    date_line_pattern = re.compile(
        r"(\d{2}[-/]\d{2}[-/]\d{4}|\d{4}[-/]\d{2}[-/]\d{2})\s+([\d,]+)"
    )

    # Pattern for material reference in Valeo format
    # "N° de référence: W000026780" — may have extra spaces due to PDF extraction
    material_pattern = re.compile(r"N[°o][\s\xa0]*de[\s\xa0]*r[eé]f[eé]rence[\s\xa0]*[:\-]?\s*(\S+)", re.IGNORECASE)

    # Also support original format: "Material: XXXXX"
    material_pattern_alt = re.compile(r"Material\s*[:\-]?\s*(\S+)", re.IGNORECASE)

    # Backlog/arriéré lines: "Arriéré 16000" — no date, just a quantity
    backlog_pattern = re.compile(r"Arri[eé]r[eé]\s+([\d,]+)", re.IGNORECASE)

    for line in lines:
        line = line.strip()

        # Detect material reference
        m = material_pattern.search(line)
        if m:
            candidate = m.group(1).strip()
            # Avoid matching the DL number that appears right after on the same line
            # Only update if it looks like a part number (not purely numeric short string)
            if candidate and not candidate.isdigit():
                current_material = candidate
            continue

        m_alt = material_pattern_alt.search(line)
        if m_alt:
            current_material = m_alt.group(1).strip()
            continue

        if current_material is None:
            continue

        # Handle backlog/arriéré lines (no delivery date, treated as past-due → Statut=1)
        backlog_match = backlog_pattern.search(line)
        if backlog_match:
            qty = int(backlog_match.group(1).replace(',', ''))
            if qty > 0:
                # Use today as delivery date for backlog rows
                formatted_date = datetime.now().strftime("%d/%m/%Y")
                data.append({
                    'Material_No_Customer': current_material,
                    'Quantité': qty,
                    'LIVRFINLU': formatted_date,
                    'Statut': 1,
                    'REFEXTERNELU': material_ref_map.get(current_material, current_material)
                })
            continue

        # Handle week-format delivery lines
        wm = week_line_pattern.search(line)
        if wm:
            end_year = int(wm.group(3))
            end_week = int(wm.group(4))
            quantity = int(wm.group(5).replace(',', ''))
            status_str = wm.group(6).lower()

            if quantity == 0:
                continue

            try:
                date_obj = iso_week_to_date(end_year, end_week)
            except ValueError:
                logging.warning(f"Skipping invalid week: {end_year} w{end_week}")
                continue

            formatted_date = date_obj.strftime("%d/%m/%Y")

            if date_obj < one_week_ago:
                statut = 1
            elif 'arri' in status_str:  # arriéré
                statut = 1
            else:
                statut = 4  # Prévision / forecast

            data.append({
                'Material_No_Customer': current_material,
                'Quantité': quantity,
                'LIVRFINLU': formatted_date,
                'Statut': statut,
                'REFEXTERNELU': material_ref_map.get(current_material, current_material)
            })
            continue

        # Fallback: legacy dd/mm/yyyy date lines
        date_matches = date_line_pattern.findall(line)
        for date_str, quantity_str in date_matches:
            try:
                date_obj = datetime.strptime(date_str, "%d/%m/%Y" if '/' in date_str else "%d-%m-%Y")
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                except ValueError:
                    logging.warning(f"Skipping invalid date: {date_str}")
                    continue

            quantity = int(quantity_str.replace(',', ''))
            if quantity == 0:
                continue

            formatted_date = date_obj.strftime("%d/%m/%Y")
            statut = 1 if date_obj < one_week_ago else 4

            data.append({
                'Material_No_Customer': current_material,
                'Quantité': quantity,
                'LIVRFINLU': formatted_date,
                'Statut': statut,
                'REFEXTERNELU': material_ref_map.get(current_material, current_material)
            })

    if not data:
        raise ValueError("No valid data extracted from the PDF.")

    df = pd.DataFrame(data)
    df['TIERSLU'] = customer_code
    df['Libelle client'] = customer_name.split(" C")[0]
    df['Tiers livré'] = customer_code
    df['Date debut Validité'] = "20190101"

    df = df[['TIERSLU', 'Material_No_Customer', 'Quantité', 'LIVRFINLU', 'Libelle client', 'Statut', 'Tiers livré',
             'REFEXTERNELU', 'Date debut Validité']]

    output_filename = f"{customer_code}.csv"
    output_path = os.path.join(output_dir, output_filename)

    df.to_csv(output_path, index=False, sep=';')
    logging.info(f"Data saved to {output_path}")
    return df, output_filename


def safe_convert_calendar_week_to_date(cw_string):
    """
    Converts a calendar week string (e.g., 'CW 07/2025') to a date string in the format 'D/M/Y'.
    """
    try:
        if isinstance(cw_string, str) and cw_string.startswith('CW'):
            week_number, year = map(int, cw_string.replace("CW", "").strip().split("/"))
            first_day_of_year = datetime.strptime(f"{year}-01-01", "%Y-%m-%d")
            first_monday = first_day_of_year + timedelta(days=(7 - first_day_of_year.weekday()) % 7)
            date = first_monday + timedelta(weeks=week_number - 1)
            return date.strftime("%d/%m/%Y")
        else:
            return cw_string
    except Exception as e:
        print(f"Error converting CW to date: {e}, input was: {cw_string}")
        return cw_string


def get_first_available_column(df, columns):
    for col in columns:
        if col in df.columns:
            return df[col]
    return None


def is_old_week(date_str):
    """Returns True if the given date string (dd/mm/yyyy) is in a past ISO week."""
    try:
        date_obj = pd.to_datetime(date_str, format='%d/%m/%Y', errors='coerce')
        if pd.isna(date_obj):
            return False
        # FIX 2: was datetime.datetime.now() — datetime is already imported directly
        current_week = datetime.now().isocalendar()[1]
        current_year = datetime.now().isocalendar()[0]
        date_iso = date_obj.isocalendar()
        # Compare year first so weeks from past years are always considered old
        if date_iso[0] < current_year:
            return True
        return date_iso[1] < current_week
    except Exception:
        return False


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

    if 'DateUntil' in df.columns:
        df['DateUntil'] = pd.to_datetime(df['DateUntil'], errors='coerce', dayfirst=True).dt.strftime('%d/%m/%Y')

    if 'Delivery_Date' in df.columns:
        df['Delivery_Date'] = df['Delivery_Date'].apply(
            lambda x: safe_convert_calendar_week_to_date(x) if isinstance(x, str) and x.startswith('CW') else x)

    if 'Despatch_Qty' in df.columns or 'DespatchQty' in df.columns:
        def clean_and_convert(value):
            try:
                cleaned = re.sub(r'[^\d.,]', '', str(value))
                if '.' in cleaned and ',' in cleaned:
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                elif ',' in cleaned:
                    cleaned = cleaned.replace(',', '.')
                return float(cleaned)
            except (ValueError, TypeError):
                return None

        if 'Despatch_Qty' in df.columns:
            df['Despatch_Qty'] = df['Despatch_Qty'].apply(clean_and_convert)
        if 'DespatchQty' in df.columns:
            df['DespatchQty'] = df['DespatchQty'].apply(clean_and_convert)

        # FIX 3: was using & (AND) — should be | (OR) so rows where EITHER qty is 0 are dropped
        qty_mask = pd.Series([False] * len(df), index=df.index)
        if 'Despatch_Qty' in df.columns:
            qty_mask = qty_mask | (df['Despatch_Qty'] == 0) | df['Despatch_Qty'].isna()
        if 'DespatchQty' in df.columns:
            qty_mask = qty_mask | (df['DespatchQty'] == 0) | df['DespatchQty'].isna()
        df = df[~qty_mask]

    if 'Status' in df.columns or 'Release_Status' in df.columns:
        status_column = 'Status' if 'Status' in df.columns else 'Release_Status'
        df[status_column] = df[status_column].apply(
            lambda x: 4 if str(x).lower() in ['firm', 'forecast'] else (1 if str(x).lower() == 'backlog' else x)
        )

    # FIX 4: Determine the delivery date column from the SOURCE df (not from transformed_df)
    # and compute Statut before building transformed_df so old-week logic works correctly.
    delivery_col = next((c for c in ['Delivery_Date', 'DateUntil'] if c in df.columns), None)
    status_col = next((c for c in ['Release_Status', 'Status'] if c in df.columns), None)

    if delivery_col:
        def compute_statut(row):
            if is_old_week(row[delivery_col]):
                return 1
            # Fall back to the already-mapped status value if available
            if status_col and pd.notnull(row.get(status_col)):
                return row[status_col]
            return 4
        df['_computed_statut'] = df.apply(compute_statut, axis=1)
    elif status_col:
        df['_computed_statut'] = df[status_col]
    else:
        df['_computed_statut'] = 4

    # Build the transformed DataFrame
    transformed_df = pd.DataFrame({
        'TIERSLU': customer_code,
        'Material_No_Customer': get_first_available_column(df, ['Material_No_Customer', 'Material']),
        'Quantité': get_first_available_column(df, ['Despatch_Qty', 'DespatchQty']),
        'LIVRFINLU': get_first_available_column(df, ['Delivery_Date', 'DateUntil']),
        'Libelle client': customer_name.split(" C")[0],
        'Statut': df['_computed_statut'],
        'Tiers livré': customer_code,
        'REFEXTERNELU': get_first_available_column(df, ['Purchase_Order_No', 'PONumber']),
        'Date debut Validité': "20190101",
    })

    # Clean up display formatting for Quantité and Statut
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

    output_filename = secure_filename(f"{customer_code}.csv")
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    transformed_df.to_csv(output_path, index=False, sep=';')

    return transformed_df, output_filename


@app.route('/')
def index():
    return render_template_string(UPLOAD_FORM_HTML, summary_table=None, show_download=False)


@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files or 'customer_code' not in request.form or 'customer_name' not in request.form:
        return "Missing file, customer code, or customer name", 400

    file = request.files['file']
    customer_code = request.form['customer_code']
    customer_name = request.form['customer_name']

    if not file.filename:
        return "No file selected", 400

    try:
        if file.filename.lower().endswith('.pdf'):
            transformed_data, output_filename = process_pdf(file, customer_code, customer_name, material_ref_map, OUTPUT_DIR)
        elif file.filename.lower().endswith('.csv'):
            transformed_data, output_filename = process_csv(file, customer_code, customer_name)
        else:
            return "Invalid file type. Please upload a CSV or PDF file.", 400

        transformed_table_html = transformed_data.head(20).to_html(classes='table', index=False)

        return render_template_string(
            UPLOAD_FORM_HTML,
            summary_table=transformed_table_html,
            show_download=True,
            download_path=output_filename
        )
    except Exception as e:
        return f"Error processing the file: {e}", 500


@app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)
