"""UI contract tests. Only synthetic data is used."""
import io
import unittest
from html.parser import HTMLParser
from unittest.mock import patch

import pandas as pd
import converter


class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.client = converter.app.test_client()

    def test_form_contract_and_all_customers(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        parser = FormParser()
        parser.feed(response.get_data(as_text=True))
        form = next(attrs for tag, attrs in parser.elements if tag == 'form')
        self.assertEqual(form['action'], '/convert')
        self.assertEqual(form['method'], 'post')
        self.assertEqual(form['enctype'], 'multipart/form-data')
        codes = [attrs['data-code'] for tag, attrs in parser.elements if tag == 'option' and 'data-code' in attrs]
        self.assertEqual(set(codes), {'C00241', 'C00410', 'C00409', 'C00125', 'C00072', 'C00050', 'C00303', 'C00250', 'C00113', 'C00132', 'C00126'})
        self.assertEqual(len(codes), 11)
        file_input = next(attrs for tag, attrs in parser.elements if tag == 'input' and attrs.get('name') == 'file')
        self.assertEqual(file_input['accept'], '.csv,.pdf')
        self.assertIn('required', file_input)
        self.assertNotIn('CONVERSION COMPLETE', response.get_data(as_text=True))

    def test_local_assets_and_accessible_labels(self):
        html = self.client.get('/').get_data(as_text=True)
        parser = FormParser()
        parser.feed(html)
        labels = {attrs.get('for') for tag, attrs in parser.elements if tag == 'label'}
        self.assertTrue({'customer_name', 'customer_code', 'source-file'}.issubset(labels))
        self.assertIn('aria-live="polite"', html)
        self.assertIn('Skip to converter', html)
        self.assertNotIn('https://', html)
        for path in ('converter.css', 'converter.js'):
            response = self.client.get('/static/' + path)
            self.addCleanup(response.close)
            self.assertEqual(response.status_code, 200)

    def test_result_escapes_filename_and_preview_cells(self):
        malicious = '<script>alert(1)</script>'
        df = pd.DataFrame({'Material': [malicious]})
        with patch.object(converter, 'process_csv', return_value=(df, 'C00250.csv')):
            response = self.client.post('/convert', data={
                'file': (io.BytesIO(b'synthetic'), '<img src=x onerror=alert(1)>.csv'),
                'customer_name': 'Synthetic customer', 'customer_code': 'C00250',
            }, content_type='multipart/form-data')
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(malicious, html)
        self.assertNotIn('<img src=x', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&lt;img src=x', html)
        self.assertIn('/download/C00250.csv', html)
        self.assertIn('role="region" aria-label="Transformed data preview" tabindex="0"', html)
        self.assertEqual(html.count('<table '), 1)
        self.assertIn('data-code="C00250" selected', html)

    def test_pdf_upload_retains_backend_dispatch(self):
        with patch.object(converter, 'process_pdf', return_value=(pd.DataFrame({'Material': ['TEST']}), 'C00113.csv')) as process:
            response = self.client.post('/convert', data={
                'file': (io.BytesIO(b'synthetic'), 'sample.pdf'),
                'customer_name': 'Synthetic customer', 'customer_code': 'C00113',
            }, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        process.assert_called_once()


if __name__ == '__main__':
    unittest.main()
