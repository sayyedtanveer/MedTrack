"""Report export service for PDF, Excel, and CSV formats."""

import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import csv


class ReportExporter:
    """Service for exporting reports in various formats."""

    @staticmethod
    def export_to_csv(report_data: Dict[str, Any], filename: str) -> bytes:
        """Export report data to CSV format."""
        output = io.StringIO()
        
        # Write report header
        output.write(f"Report: {report_data.get('report_type', 'Unknown')}\n")
        if report_data.get('period'):
            output.write(f"Period: {report_data['period'].get('start')} to {report_data['period'].get('end')}\n")
        output.write(f"Generated: {datetime.utcnow().isoformat()}\n\n")

        # Write data
        data = report_data.get('data', [])
        if not data:
            output.write("No data available\n")
            return output.getvalue().encode('utf-8')

        writer = csv.DictWriter(output, fieldnames=data[0].keys() if data else [])
        writer.writeheader()
        writer.writerows(data)

        # Write summary
        output.write("\n\nSummary:\n")
        summary = report_data.get('summary', {})
        for key, value in summary.items():
            output.write(f"{key}: {value}\n")

        return output.getvalue().encode('utf-8')

    @staticmethod
    def export_to_json(report_data: Dict[str, Any], filename: str) -> bytes:
        """Export report data to JSON format."""
        json_data = json.dumps(report_data, indent=2, default=str)
        return json_data.encode('utf-8')

    @staticmethod
    def export_to_excel(report_data: Dict[str, Any], filename: str) -> bytes:
        """Export report data to Excel format."""
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            raise ImportError("openpyxl is required for Excel export")

        wb = Workbook()
        ws = wb.active
        ws.title = "Report"

        # Write header
        row = 1
        ws[f"A{row}"] = f"Report: {report_data.get('report_type', 'Unknown')}"
        ws[f"A{row}"].font = Font(bold=True, size=14)
        
        row += 1
        if report_data.get('period'):
            ws[f"A{row}"] = f"Period: {report_data['period'].get('start')} to {report_data['period'].get('end')}"
        
        row += 1
        ws[f"A{row}"] = f"Generated: {datetime.utcnow().isoformat()}"
        
        row += 2

        # Write data
        data = report_data.get('data', [])
        if data:
            # Write headers
            headers = list(data[0].keys())
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col_idx)
                cell.value = header
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
                cell.font = Font(bold=True, color="FFFFFF")

            row += 1

            # Write data rows
            for data_row in data:
                for col_idx, header in enumerate(headers, 1):
                    cell = ws.cell(row=row, column=col_idx)
                    value = data_row.get(header)
                    cell.value = value
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                row += 1

        # Write summary
        row += 2
        ws[f"A{row}"] = "Summary"
        ws[f"A{row}"].font = Font(bold=True, size=12)
        
        row += 1
        summary = report_data.get('summary', {})
        for key, value in summary.items():
            ws[f"A{row}"] = str(key)
            ws[f"B{row}"] = value
            ws[f"A{row}"].font = Font(bold=True)
            row += 1

        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        # Write to bytes
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    @staticmethod
    def export_bom_cost_analysis(report: Dict[str, Any]) -> bytes:
        """Write an authorized, already-calculated BOM analysis using openpyxl."""
        from datetime import datetime, timezone
        from decimal import Decimal
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        book = Workbook()
        book.remove(book.active)
        product = report["product"] or {}
        currency = report["currency_code"]
        complete = report["is_complete"]

        def exact(value: Any) -> str | None:
            return format(value, "f") if isinstance(value, Decimal) else None

        def put_sheet(name: str, headers: list[str], rows: list[tuple]) -> None:
            sheet = book.create_sheet(name)
            sheet.append(headers)
            sheet.freeze_panes = "B2" if len(headers) > 4 else "A2"
            widths = [len(label) for label in headers]
            for row_number, row in enumerate(rows, 2):
                for col, value in enumerate(row, 1):
                    cell = sheet.cell(row=row_number, column=col)
                    if isinstance(value, datetime):
                        cell.value = value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
                        cell.number_format = "yyyy-mm-dd hh:mm:ss"
                    else:
                        cell.value = value
                        if isinstance(value, str):
                            cell.data_type = "s"
                        elif isinstance(value, Decimal):
                            cell.number_format = "0.00###########"
                    widths[col - 1] = max(widths[col - 1], len(str(value)) if value is not None else 0)
            sheet.auto_filter.ref = sheet.dimensions
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="243A55")
                cell.alignment = Alignment(wrap_text=True, vertical="center")
            sheet.row_dimensions[1].height = 30
            for index, width in enumerate(widths, 1):
                sheet.column_dimensions[get_column_letter(index)].width = max(14, min(60, width + 3))

        metrics = [
            ("Calculated BOM cost per output unit", report["total_cost"]),
            ("Direct material cost", report["direct_material_cost"]),
            ("Nested BOM contribution", report["nested_cost"]),
            ("Own operation cost", report["own_operation_cost"]),
            ("Own outside processing (estimated BOM cost)", report["own_outside_processing_cost"]),
        ]
        put_sheet("Summary", ["Field", "Value", "Exact decimal"], [
            ("Report", "BOM Cost Analysis", None), ("Company", report["company"], None),
            ("Product", product.get("name"), None), ("Product code", product.get("code"), None),
            ("Variant", report["target_name"] if report["variant_id"] else None, None),
            ("Variant code", report["target_code"] if report["variant_id"] else None, None),
            ("BOM ID filter", report["bom_id"], None), ("Version filter", report["version"], None),
            ("Status", "Active" if report["is_active"] else "Draft / inactive", None),
            ("Calculated at (UTC)", report["generated_at"], None), ("Currency", currency, None),
            ("Output quantity", report["output_quantity"], None), ("Output UOM", report["output_uom"], None),
            ("Cost status", "Complete" if complete else "Incomplete", None),
            ("Calculation basis", "Current standards and estimated BOM processing per output unit", None),
            ("Precision", "Exact decimal text is the authoritative value when Excel rounds numeric cells.", None),
            *((name, value, exact(value)) for name, value in metrics),
        ])
        breakdown = [("Selected BOM", name, value, exact(value)) for name, value in metrics]
        if report["composition"] is not None:
            for key, label in (
                ("material", "Raw material leaves"), ("operations", "Operations across all levels"),
                ("outside_processing", "Outside processing across all levels (estimated BOM cost)"),
            ):
                value = report["composition"][key]
                breakdown.append(("Flattened composition", label, value, exact(value)))
            breakdown.append(("Flattened composition", "Reconciled total", report["total_cost"], exact(report["total_cost"])))

        hierarchy = []

        def walk(node: dict, path: str, parent: str | None) -> None:
            quantity, unit_cost, cost = (node.get(field) for field in ("quantity", "unit_cost", "cost"))
            hierarchy.append((
                path, parent, node.get("version"), node.get("code"), node.get("name"),
                node.get("cost_basis") or node["type"], quantity, exact(quantity), node.get("unit"),
                unit_cost, exact(unit_cost), cost, exact(cost),
                node.get("stored_standard_cost"), exact(node.get("stored_standard_cost")), node.get("message"),
            ))
            for index, op in enumerate(node.get("operations", []), 1):
                op_cost = op.get("cost")
                hierarchy.append((f"{path}.op{index}", path, None, op.get("code"), op["name"],
                                  "Operation", None, None, None, None, None, op_cost, exact(op_cost), None, None, None))
            making = node.get("making_cost")
            if making is not None and making > 0:
                hierarchy.append((f"{path}.outside", path, None, None, "Outside processing (estimated BOM cost)",
                                  "Outside processing", None, None, None, None, None, making, exact(making), None, None, None))
            for index, child in enumerate(node["children"], 1):
                walk(child, f"{path}.{index}", path)

        walk(report["tree"], "1", None)
        if len(hierarchy) > 10001:
            raise OverflowError("Workbook hierarchy exceeds the 10,001-row limit")
        put_sheet("Cost Breakdown", ["View", "Cost category", "Amount", "Exact amount"], breakdown)
        put_sheet("BOM Hierarchy", [
            "Row path", "Parent path", "BOM version", "Code", "Component", "Cost basis",
            "Quantity", "Exact quantity", "UOM", "Unit cost", "Exact unit cost", "Extended cost",
            "Exact extended cost", "Stored Standard Cost", "Exact stored cost", "Exception",
        ], hierarchy)
        put_sheet("Exceptions", ["Type", "Component", "Code", "Name", "Reason", "Detail"], [
            (issue.get("component_type"), issue.get("component_id"), issue.get("code"),
             issue.get("name"), issue.get("reason"), issue.get("message"))
            for issue in report["missing_costs"]
        ])
        output = io.BytesIO()
        book.save(output)
        return output.getvalue()

    @staticmethod
    def export_to_pdf(report_data: Dict[str, Any], filename: str) -> bytes:
        """Export report data to PDF format."""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.units import inch
            from io import BytesIO
        except ImportError:
            raise ImportError("reportlab is required for PDF export")

        # Create PDF document
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor("#1F2937"),
            spaceAfter=12,
        )
        elements.append(Paragraph(f"Report: {report_data.get('report_type', 'Unknown')}", title_style))
        
        # Period info
        if report_data.get('period'):
            period_text = f"Period: {report_data['period'].get('start')} to {report_data['period'].get('end')}"
            elements.append(Paragraph(period_text, styles['Normal']))
        
        elements.append(Paragraph(f"Generated: {datetime.utcnow().isoformat()}", styles['Normal']))
        elements.append(Spacer(1, 0.3 * inch))

        # Data table
        data = report_data.get('data', [])
        if data:
            table_data = []
            # Headers
            headers = list(data[0].keys())
            table_data.append(headers)
            
            # Data rows
            for row in data:
                table_data.append([str(row.get(h, '')) for h in headers])

            table = Table(table_data, colWidths=[1.2 * inch] * len(headers))
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            elements.append(table)

        # Summary
        elements.append(Spacer(1, 0.2 * inch))
        summary_title = ParagraphStyle(
            'SummaryTitle',
            parent=styles['Heading2'],
            fontSize=12,
        )
        elements.append(Paragraph("Summary", summary_title))
        
        summary = report_data.get('summary', {})
        for key, value in summary.items():
            elements.append(Paragraph(f"<b>{key}:</b> {value}", styles['Normal']))

        # Build PDF
        doc.build(elements)
        return output.getvalue()


class ExportService:
    """Main export service orchestrator."""

    EXPORTERS = {
        'csv': ReportExporter.export_to_csv,
        'json': ReportExporter.export_to_json,
        'excel': ReportExporter.export_to_excel,
        'pdf': ReportExporter.export_to_pdf,
    }

    @classmethod
    def export_report(
        cls,
        report_data: Dict[str, Any],
        export_format: str,
        filename: str,
    ) -> tuple[bytes, str]:
        """Export report data in specified format.
        
        Returns:
            Tuple of (file_bytes, mime_type)
        """
        if export_format not in cls.EXPORTERS:
            raise ValueError(f"Unsupported export format: {export_format}")

        exporter = cls.EXPORTERS[export_format]
        file_bytes = exporter(report_data, filename)

        mime_types = {
            'csv': 'text/csv',
            'json': 'application/json',
            'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf',
        }

        return file_bytes, mime_types.get(export_format, 'application/octet-stream')
