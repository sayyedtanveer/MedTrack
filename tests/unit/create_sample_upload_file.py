"""
Create a sample material upload file to test the complete workflow.
This file contains multiple material records that can be used for testing.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from datetime import datetime

# Create workbook
wb = openpyxl.Workbook()

# Remove default sheet
if 'Sheet' in wb.sheetnames:
    del wb['Sheet']

# === Worksheet 1: Field Guide ===
ws_guide = wb.create_sheet("Field Guide", 0)
ws_guide['A1'] = "MedTrack ERP - Raw Material Field Guide"
ws_guide['A1'].font = Font(bold=True, size=14)
ws_guide['A3'] = "This guide explains each field in the template with examples and best practices."

# === Worksheet 2: Quick Start ===
ws_quick = wb.create_sheet("Quick Start", 1)
ws_quick['A1'] = "MedTrack ERP - Quick Start Guide"
ws_quick['A1'].font = Font(bold=True, size=14)
ws_quick['A3'] = "📋 STEPS TO IMPORT:"

# === Worksheet 3: Raw Materials ===
ws_data = wb.create_sheet("Raw Materials", 2)

# Headers
headers = [
    'Item Code', 'Material Name', 'Category', 'Base Unit', 'Barcode',
    'Warehouse', 'Zone', 'Rack / Bin', 'Opening Stock', 'Minimum Stock',
    'Maximum Stock', 'Reorder Level', 'Reorder Quantity', 'Track by Batch?',
    'Track Expiry?', 'Shelf Life', 'Track Traceability?', 'Quality Check Required?',
    'Preferred Supplier', 'Supplier Item Code', 'Purchase Unit', 'Lead Time (Days)',
    'Minimum Order Quantity', 'Length Unit', 'Can Be Cut?', 'Track Remaining Quantity?',
    'Decimal Places', 'Reuse Remaining Material?'
]

# Add header row
for col_idx, header in enumerate(headers, 1):
    cell = ws_data.cell(row=1, column=col_idx, value=header)
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# Add sample data rows
sample_materials = [
    {
        'Item Code': 'STL-PLATE-001',
        'Material Name': 'Steel Plate 10MM',
        'Category': 'Steel Products',
        'Base Unit': 'KG',
        'Barcode': 'EAN-STL-001',
        'Warehouse': 'Main Warehouse',
        'Zone': 'Zone-A',
        'Rack / Bin': 'Rack-01-Bin-05',
        'Opening Stock': '500',
        'Minimum Stock': '50',
        'Maximum Stock': '2000',
        'Reorder Level': '100',
        'Reorder Quantity': '500',
        'Track by Batch?': 'No',
        'Track Expiry?': 'No',
        'Shelf Life': '',
        'Track Traceability?': 'Yes',
        'Quality Check Required?': 'Yes',
        'Preferred Supplier': 'Steel Co Ltd',
        'Supplier Item Code': 'SC-STL-10MM',
        'Purchase Unit': 'KG',
        'Lead Time (Days)': '7',
        'Minimum Order Quantity': '100',
        'Length Unit': 'MM',
        'Can Be Cut?': 'Yes',
        'Track Remaining Quantity?': 'Yes',
        'Decimal Places': '2',
        'Reuse Remaining Material?': 'Yes',
    },
    {
        'Item Code': 'ALU-EXTRUDE-002',
        'Material Name': 'Aluminum Extrusion Profile',
        'Category': 'Aluminum',
        'Base Unit': 'METER',
        'Barcode': 'EAN-ALU-002',
        'Warehouse': 'Secondary Warehouse',
        'Zone': 'Zone-B',
        'Rack / Bin': 'Rack-02-Bin-03',
        'Opening Stock': '300',
        'Minimum Stock': '30',
        'Maximum Stock': '1000',
        'Reorder Level': '60',
        'Reorder Quantity': '200',
        'Track by Batch?': 'Yes',
        'Track Expiry?': 'No',
        'Shelf Life': '',
        'Track Traceability?': 'Yes',
        'Quality Check Required?': 'No',
        'Preferred Supplier': 'Aluminum International',
        'Supplier Item Code': 'AI-ALU-PROF-001',
        'Purchase Unit': 'METER',
        'Lead Time (Days)': '14',
        'Minimum Order Quantity': '50',
        'Length Unit': 'MM',
        'Can Be Cut?': 'Yes',
        'Track Remaining Quantity?': 'No',
        'Decimal Places': '3',
        'Reuse Remaining Material?': 'No',
    },
    {
        'Item Code': 'PAINT-BLUE-003',
        'Material Name': 'Industrial Paint - Blue',
        'Category': 'Paints & Coatings',
        'Base Unit': 'LITER',
        'Barcode': 'EAN-PAINT-003',
        'Warehouse': 'Main Warehouse',
        'Zone': 'Zone-C',
        'Rack / Bin': 'Rack-03-Bin-02',
        'Opening Stock': '200',
        'Minimum Stock': '20',
        'Maximum Stock': '500',
        'Reorder Level': '50',
        'Reorder Quantity': '100',
        'Track by Batch?': 'No',
        'Track Expiry?': 'Yes',
        'Shelf Life': '365',
        'Track Traceability?': 'No',
        'Quality Check Required?': 'Yes',
        'Preferred Supplier': 'Paint Masters',
        'Supplier Item Code': 'PM-BLUE-LTR',
        'Purchase Unit': 'LITER',
        'Lead Time (Days)': '3',
        'Minimum Order Quantity': '10',
        'Length Unit': '',
        'Can Be Cut?': 'No',
        'Track Remaining Quantity?': 'No',
        'Decimal Places': '1',
        'Reuse Remaining Material?': 'No',
    },
    {
        'Item Code': 'BOLT-M12-004',
        'Material Name': 'Bolt M12 x 80MM',
        'Category': 'Fasteners',
        'Base Unit': 'PIECE',
        'Barcode': 'EAN-BOLT-004',
        'Warehouse': 'Main Warehouse',
        'Zone': 'Zone-A',
        'Rack / Bin': 'Rack-04-Bin-01',
        'Opening Stock': '10000',
        'Minimum Stock': '500',
        'Maximum Stock': '50000',
        'Reorder Level': '2000',
        'Reorder Quantity': '5000',
        'Track by Batch?': 'No',
        'Track Expiry?': 'No',
        'Shelf Life': '',
        'Track Traceability?': 'No',
        'Quality Check Required?': 'No',
        'Preferred Supplier': 'Bolt Supplier Inc',
        'Supplier Item Code': 'BSI-M12-80',
        'Purchase Unit': 'BOX/100',
        'Lead Time (Days)': '5',
        'Minimum Order Quantity': '100',
        'Length Unit': 'MM',
        'Can Be Cut?': 'No',
        'Track Remaining Quantity?': 'No',
        'Decimal Places': '0',
        'Reuse Remaining Material?': 'No',
    },
]

# Add data rows
for row_idx, material in enumerate(sample_materials, 2):
    for col_idx, header in enumerate(headers, 1):
        value = material.get(header, '')
        cell = ws_data.cell(row=row_idx, column=col_idx, value=value)
        if value:
            cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

# Auto-adjust column widths
for col_idx, header in enumerate(headers, 1):
    ws_data.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = 15

# Save
output_path = "data/templates/sample-materials-for-upload.xlsx"
wb.save(output_path)
print(f"✅ Created sample upload file: {output_path}")
print(f"   - Field Guide worksheet (informational)")
print(f"   - Quick Start worksheet (tutorial)")
print(f"   - Raw Materials worksheet with {len(sample_materials)} sample materials")
print(f"\nSample materials:")
for material in sample_materials:
    print(f"   • {material['Item Code']}: {material['Material Name']}")
