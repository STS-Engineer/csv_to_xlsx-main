from flask import Flask, request, send_file, render_template_string
import pandas as pd
import os

app = Flask(__name__)

# Configure the static folder to serve the logo
app.config['STATIC_FOLDER'] = 'static'

# HTML template for the file upload form and Excel viewer
UPLOAD_FORM_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>CSV to Excel Converter</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        background-color: #f8f9fa;
        margin: 0;
        padding: 20px;
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
        height: 100vh;
        background-image: url('/static/background1.webp');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
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
        margin-bottom: 20px;
      }
      form {
        display: flex;
        justify-content: center;
        gap: 10px;
        flex-wrap: wrap;
      }
      input[type="file"] {
        margin-bottom: 10px;
      }
      input[type="submit"], a.download-btn {
        background-color: #007bff;
        color: #ffffff;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
      }
      input[type="submit"]:hover, a.download-btn:hover {
        background-color: #0056b3;
      }
      img {
        max-width: 150px;
        margin-bottom: 20px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
      }
      table, th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
      }
      th {
        background-color: #007bff;
        color: white;
        text-transform: uppercase;
      }
      td {
        max-width: 200px;
        word-wrap: break-word;
      }
      table tbody tr:nth-child(odd) {
        background-color: #f9f9f9;
      }
      table tbody tr:hover {
        background-color: #f1f1f1;
      }
      .scrollable {
        overflow: auto;
        max-height: 400px;
      }
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <link rel="icon" href="/static/logo-avocarbon-carre.ico" type="image/x-icon">
  </head>
  <body>
    <div class="container">
      <img src="/static/logo-avocarbon (1).png" alt="Logo">
      <h1 style="color: green;"><i class="fas fa-file-csv" style="color: green; vertical-align: middle;"></i> Upload CSV to Convert to Excel<i class="fas fa-file-excel" style="color: green; vertical-align: middle;"></i></h1>
      <form action="/convert" method="post" enctype="multipart/form-data">
        <input type="file" name="file" accept=".csv" required>
        <input type="submit" value="Convert">
        {% if show_download %}
        <a href="/download" class="download-btn"><i class="fas fa-download"></i> Download Excel</a>
        {% endif %}
      </form>
      {% if table %}
      <h2>Excel File Preview</h2>
      <div class="scrollable">
        <table>
          {{ table|safe }}
        </table>
      </div>
      {% endif %}
    </div>
  </body>
</html>
"""

# Store the output file path for later use
output_excel_path = "converted_output.xlsx"

@app.route('/')
def index():
    return render_template_string(UPLOAD_FORM_HTML, show_download=False)

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return "No file part"

    file = request.files['file']
    if file.filename == '':
        return "No selected file"

    if file and file.filename.endswith('.csv'):
        # Read CSV file into a DataFrame
        df = pd.read_csv(file)

        # Save DataFrame to an Excel file
        df.to_excel(output_excel_path, index=False)

        # Convert entire DataFrame to HTML for preview
        table_html = df.to_html(classes='table table-striped', index=False)

        # Render the page with the table and download button
        return render_template_string(UPLOAD_FORM_HTML, table=table_html, show_download=True)
    else:
        return "Invalid file type. Please upload a CSV file."

@app.route('/download')
def download():
    if os.path.exists(output_excel_path):
        return send_file(output_excel_path, as_attachment=True)
    else:
        return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
