import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import converter


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = patch.object(converter, "OUTPUT_DIR", self.temp.name)
        self.directory.start()
        self.addCleanup(self.directory.stop)
        self.client = converter.app.test_client()

    def post(self, data, customer="C00250"):
        return self.client.post("/convert", data={
            "file": (io.BytesIO(data), "input.csv"),
            "customer_code": customer,
            "customer_name": "Synthetic customer " + customer,
        }, content_type="multipart/form-data")

    def test_portal_upload_and_download(self):
        response = self.post(
            b"\xef\xbb\xbfItem Number;Quantity;Delivery Date;PO Number;Requirement type\r\n"
            b"000001;168;19/10/2099;00001234;Forecast\r\n"
        )
        self.assertEqual(response.status_code, 200)
        download = self.client.get("/download/C00250.csv")
        self.addCleanup(download.close)
        self.assertEqual(download.status_code, 200)
        self.assertIn(b"000001;168;19/10/2099", download.data)
        self.assertIn(b";00001234;20190101\r\n", download.data)
        self.assertIn("Quantité".encode("cp1252"), download.data)

    def test_download_uses_conversion_directory_when_cwd_differs(self):
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp.name)
            Path("outputs").mkdir()
            with patch.object(converter, "OUTPUT_DIR", "outputs"):
                response = self.post(
                    b"Item Number;Quantity;Delivery Date;PO Number;Requirement type\n"
                    b"TEST-A;168;19/10/2099;00001234;Forecast\n"
                )
                self.assertEqual(response.status_code, 200)
                expected = Path("outputs/C00250.csv").read_bytes()
                download = self.client.get("/download/C00250.csv")
                self.addCleanup(download.close)
                self.assertEqual(download.status_code, 200)
                self.assertEqual(download.data, expected)
                self.assertIn("attachment; filename=C00250.csv",
                              download.headers["Content-Disposition"])
                self.assertEqual(download.mimetype, "text/csv")
        finally:
            os.chdir(original_cwd)

    def test_missing_download_still_returns_not_found(self):
        response = self.client.get("/download/missing.csv")
        self.assertEqual(response.status_code, 404)

    def test_portal_malformed_row_is_rejected(self):
        response = self.post(
            b"Item Number;Quantity;Delivery Date;PO Number;Requirement type\n"
            b"A;1;19/10/2099;1234;Forecast;unexpected\n"
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"inconsistent column count", response.data)
        self.assertFalse(Path(self.temp.name, "C00250.csv").exists())

    def test_portal_missing_header_is_rejected_without_output(self):
        response = self.post(
            b"Item Number;Quantity;Delivery Date;PO Number\n"
            b"A;5;19/10/2099;1234\n"
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"missing columns: Requirement type", response.data)
        self.assertFalse(Path(self.temp.name, "C00250.csv").exists())

    def test_portal_duplicate_quantity_is_rejected_without_output(self):
        response = self.post(
            b"Item Number;Quantity;Delivery Date;PO Number;Requirement type;Quantity\n"
            b"A;5;19/10/2099;1234;Forecast;200\n"
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"duplicate columns: Quantity", response.data)
        self.assertFalse(Path(self.temp.name, "C00250.csv").exists())

    def test_legacy_schema_both_customers_unchanged(self):
        for customer in ("C00250", "C00999"):
            response = self.post(
                b"Material_No_Customer;Despatch_Qty;Delivery_Date;Release_Status;Purchase_Order_No\n"
                b"TEST-A;168;19/10/2099;Forecast;1234\n"
                b"TEST-B;0;19/10/2099;Forecast;1234\n", customer)
            self.assertEqual(response.status_code, 200)
            result = Path(self.temp.name, customer + ".csv").read_bytes()
            self.assertIn("Quantité".encode("utf-8"), result)
            self.assertIn(b"TEST-A;168;19/10/2099", result)
            self.assertNotIn(b"TEST-B", result)

    def test_legacy_alternate_schema(self):
        response = self.post(
            b"Material;DespatchQty;DateUntil;Status;PONumber\n"
            b"TEST-A;168;19/10/2099;Backlog;1234\n", "C00999")
        self.assertEqual(response.status_code, 200)
        result = Path(self.temp.name, "C00999.csv").read_text()
        self.assertIn("Synthetic customer;1;", result)


if __name__ == "__main__":
    unittest.main()
