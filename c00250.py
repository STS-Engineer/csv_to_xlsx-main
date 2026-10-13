"""Valeo C00250 portal CSV support, isolated from legacy customer formats."""

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

SOURCE_COLUMNS = (
    "Item Number", "Quantity", "Delivery Date", "PO Number", "Requirement type"
)
OUTPUT_COLUMNS = (
    "TIERSLU", "Material_No_Customer", "Quantité", "LIVRFINLU",
    "Libelle client", "Statut", "Tiers livré", "REFEXTERNELU",
    "Date debut Validité",
)


def is_portal_csv(columns, customer_code):
    if customer_code != "C00250":
        return False
    columns = list(columns)
    # Portal names do not occur in the two supported legacy schemas. Seeing
    # any of them means this upload must pass the complete portal contract.
    if not any(column in columns for column in SOURCE_COLUMNS):
        return False
    missing = [column for column in SOURCE_COLUMNS if column not in columns]
    duplicates = [column for column in SOURCE_COLUMNS if columns.count(column) > 1]
    if missing:
        raise ValueError("C00250 portal CSV: missing columns: " + ", ".join(missing))
    if duplicates:
        raise ValueError("C00250 portal CSV: duplicate columns: " + ", ".join(duplicates))
    return True


def transform_portal_rows(rows, customer_name, today=None):
    """Preserve nonzero source quantities; sort by material and delivery date.

    As in the legacy converter, firm/forecast map to 4 and past ISO weeks
    to 1. Explicit backlog/backorder also maps to 1. Unknown or invalid
    source values fail rather than silently discarding business records.
    """
    today = today or date.today()
    current_week = today.isocalendar()[:2]
    transformed = []
    for number, source in enumerate(rows, start=2):
        row = {key: str(source.get(key, "")).strip() for key in SOURCE_COLUMNS}
        if any(not row[key] for key in SOURCE_COLUMNS):
            raise ValueError(f"C00250 row {number}: missing required value")
        try:
            delivery = datetime.strptime(row["Delivery Date"], "%d/%m/%Y").date()
        except ValueError as error:
            raise ValueError(f"C00250 row {number}: invalid Delivery Date") from error
        try:
            quantity = Decimal(row["Quantity"].replace(",", "."))
            if not quantity.is_finite() or quantity < 0:
                raise InvalidOperation
        except InvalidOperation as error:
            raise ValueError(f"C00250 row {number}: invalid Quantity") from error
        # The existing converter excludes zero-quantity delivery lines.
        if quantity == 0:
            continue
        status_name = row["Requirement type"].casefold()
        if status_name not in {"firm", "forecast", "backlog", "backorder"}:
            raise ValueError(f"C00250 row {number}: unknown Requirement type")
        status = "1" if (
            status_name in {"backlog", "backorder"}
            or delivery.isocalendar()[:2] < current_week
        ) else "4"
        # Decimal formatting avoids scientific notation and float rounding.
        quantity_text = format(quantity, "f")
        if "." in quantity_text:
            quantity_text = quantity_text.rstrip("0").rstrip(".")
        transformed.append((delivery, {
            "TIERSLU": "C00250",
            "Material_No_Customer": row["Item Number"],
            "Quantité": quantity_text,
            "LIVRFINLU": delivery.strftime("%d/%m/%Y"),
            "Libelle client": customer_name.split(" C")[0],
            "Statut": status,
            "Tiers livré": "C00250",
            "REFEXTERNELU": row["PO Number"],
            "Date debut Validité": "20190101",
        }))
    transformed.sort(key=lambda item: (item[1]["Material_No_Customer"], item[0]))
    return [row for _, row in transformed]


def encode_portal_csv(rows):
    """Match the supplied format model: semicolons, CRLF, Windows-1252."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=OUTPUT_COLUMNS, delimiter=";",
                            lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("cp1252")
