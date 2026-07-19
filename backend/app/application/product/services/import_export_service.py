from __future__ import annotations

"""
CSV/Excel parser for product import/export operations.
"""

import csv
import io
from typing import Dict, List, Optional, Any
from decimal import Decimal


class VariantImportParser:
    """Parse variants from CSV format."""

    @staticmethod
    def parse_csv(csv_data: str, template_attributes: List[Dict[str, Any]]) -> tuple[List[Dict], List[str]]:
        """
        Parse CSV data and return list of variant dictionaries.
        
        Expected CSV columns:
        - attribute_key (e.g., SIZE, COLOR) for each template attribute
        - standard_cost (required)
        - selling_price (optional)
        
        Args:
            csv_data: Raw CSV text
            template_attributes: List of attribute definitions from template
            
        Returns:
            (variant_list, errors) - list of parsed variants and list of error messages
        """
        variants: List[Dict] = []
        errors: List[str] = []

        attribute_keys = [str(a["key"]).upper() for a in template_attributes]

        try:
            reader = csv.DictReader(io.StringIO(csv_data.strip("\ufeff\r\n ")))
            if not reader or not reader.fieldnames:
                return [], ["Invalid CSV format"]
            header_lookup = {
                str(header).strip().upper(): header
                for header in reader.fieldnames
                if header is not None
            }

            for row_num, row in enumerate(reader, start=2):  # start=2 to skip header
                try:
                    # Build attribute_values from columns matching template attributes
                    attribute_values: Dict[str, Any] = {}
                    for key in attribute_keys:
                        val = row.get(header_lookup.get(key, key))
                        if val:
                            attribute_values[key] = val.strip()

                    # Parse standard_cost (required)
                    cost_str = (row.get(header_lookup.get("STANDARD_COST", "standard_cost"), "") or "").strip()
                    if not cost_str:
                        errors.append(f"Row {row_num}: standard_cost is required")
                        continue

                    try:
                        standard_cost = Decimal(cost_str)
                    except:
                        errors.append(f"Row {row_num}: standard_cost must be a valid decimal")
                        continue

                    # Parse selling_price (optional)
                    selling_price = None
                    price_str = (row.get(header_lookup.get("SELLING_PRICE", "selling_price"), "") or "").strip()
                    if price_str:
                        try:
                            selling_price = Decimal(price_str)
                        except:
                            errors.append(f"Row {row_num}: selling_price must be a valid decimal")
                            continue

                    variant: Dict[str, Any] = {
                        "attribute_values": attribute_values,
                        "standard_cost": standard_cost,
                    }
                    if selling_price is not None:
                        variant["selling_price"] = selling_price

                    variants.append(variant)

                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")

        except Exception as e:
            errors.append(f"CSV parsing error: {str(e)}")

        return variants, errors

    @staticmethod
    def parse_csv_bytes(csv_bytes: bytes, template_attributes: List[Dict[str, Any]], encoding: str = "utf-8") -> tuple[List[Dict], List[str]]:
        """Parse CSV from bytes."""
        try:
            csv_text = csv_bytes.decode(encoding)
            return VariantImportParser.parse_csv(csv_text, template_attributes)
        except Exception as e:
            return [], [f"Encoding error: {str(e)}"]

    @staticmethod
    def generate_csv_template(template_attributes: List[Dict[str, Any]]) -> str:
        """Generate a CSV template for users to fill in."""
        headers = []
        for attr in template_attributes:
            headers.append(str(attr["key"]).upper())
        headers.extend(["standard_cost", "selling_price"])

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        # Add example row
        example_row = [""] * len(headers)
        example_row[-2] = "10.50"  # standard_cost example
        example_row[-1] = "20.00"  # selling_price example
        writer.writerow(example_row)

        return output.getvalue()


class VariantExportService:
    """Export variants to CSV format."""

    @staticmethod
    def export_variants_to_csv(variants: List[Dict[str, Any]], template_attributes: List[Dict[str, Any]]) -> str:
        """Export variant list to CSV."""
        attribute_keys = [str(a["key"]).upper() for a in template_attributes]
        headers = attribute_keys + ["code", "standard_cost", "selling_price", "is_active"]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()

        for variant in variants:
            row = {}
            # Add attribute values
            for key in attribute_keys:
                row[key] = variant.get("attribute_values", {}).get(key, "")
            # Add other fields
            row["code"] = variant.get("code", "")
            row["standard_cost"] = str(variant.get("standard_cost", ""))
            row["selling_price"] = str(variant.get("selling_price", "")) if variant.get("selling_price") else ""
            row["is_active"] = "Yes" if variant.get("is_active") else "No"
            writer.writerow(row)

        return output.getvalue()
