import csv
import io
import unittest
from datetime import date

from c00250 import (
    OUTPUT_COLUMNS, encode_portal_csv, is_portal_csv, transform_portal_rows,
)


def source(material="TEST-B", quantity="168", delivery="19/10/2026",
           po="00001234", status="Forecast"):
    return dict(zip(
        ("Item Number", "Quantity", "Delivery Date", "PO Number", "Requirement type"),
        (material, quantity, delivery, po, status),
    ))


class PortalTests(unittest.TestCase):
    def transform(self, rows):
        return transform_portal_rows(rows, "Synthetic customer C00250", date(2026, 10, 13))

    def test_exact_headers_encoding_and_line_endings(self):
        actual = encode_portal_csv(self.transform([source()]))
        expected = (
            "TIERSLU;Material_No_Customer;Quantité;LIVRFINLU;Libelle client;"
            "Statut;Tiers livré;REFEXTERNELU;Date debut Validité\r\n"
            "C00250;TEST-B;168;19/10/2026;Synthetic customer;4;"
            "C00250;00001234;20190101\r\n"
        ).encode("cp1252")
        self.assertEqual(actual, expected)

    def test_stable_material_and_chronological_sort(self):
        rows = [source(delivery="02/11/2026"),
                source(delivery="19/10/2026", po="00002"),
                source(material="TEST-A"), source(po="00003")]
        result = self.transform(rows)
        self.assertEqual([r["REFEXTERNELU"] for r in result],
                         ["00001234", "00002", "00003", "00001234"])

    def test_preserve_duplicates_decimals_identifiers_and_drop_zeroes(self):
        rows = [source(material="0000123", quantity="10"), source(quantity="0"),
                source(quantity="168.50"), source(quantity="168.50")]
        result = self.transform(rows)
        self.assertEqual(len(result), 3)
        self.assertEqual([r["Quantité"] for r in result], ["10", "168.5", "168.5"])
        self.assertEqual(result[0]["Material_No_Customer"], "0000123")

    def test_status_mapping_and_year_boundary(self):
        rows = [source(status=s) for s in ["Firm", "Forecast", "Backorder", "Backlog"]]
        self.assertEqual([r["Statut"] for r in self.transform(rows)], ["4", "4", "1", "1"])
        rows = [source(delivery="09/10/2026"), source(delivery="12/10/2026"),
                source(delivery="04/01/2027")]
        self.assertEqual([r["Statut"] for r in self.transform(rows)], ["1", "4", "4"])

    def test_invalid_values_are_rejected(self):
        for field, value in [("Quantity", "NaN"), ("Quantity", "-1"),
                             ("Quantity", "garbage"), ("Delivery Date", "31/02/2026"),
                             ("Requirement type", "Unexpected"), ("PO Number", "")]:
            row = source()
            row[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.transform([row])

    def test_customer_and_schema_gate(self):
        self.assertTrue(is_portal_csv(source(), "C00250"))
        self.assertFalse(is_portal_csv(source(), "C00999"))
        self.assertFalse(is_portal_csv(["Material_No_Customer", "Despatch_Qty"], "C00250"))

    def test_partial_and_duplicate_portal_headers_are_rejected(self):
        columns = list(source())
        for field in columns:
            with self.subTest(missing=field), self.assertRaises(ValueError):
                is_portal_csv([c for c in columns if c != field], "C00250")
            with self.subTest(duplicate=field), self.assertRaises(ValueError):
                is_portal_csv(columns + [field], "C00250")

    def test_quoted_fields_and_empty_file(self):
        result = self.transform([source(material='TEST;"A"')])
        data = encode_portal_csv(result)
        decoded = list(csv.DictReader(io.StringIO(data.decode("cp1252")), delimiter=";"))
        self.assertEqual(decoded, result)
        self.assertEqual(encode_portal_csv([]),
                         (";".join(OUTPUT_COLUMNS) + "\r\n").encode("cp1252"))


if __name__ == "__main__":
    unittest.main()
