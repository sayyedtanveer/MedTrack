import io
import zipfile

from backend.app.application.inventory.services.material_onboarding_service import (
    FIELDS,
    MaterialOnboardingService,
)


def _xlsx_with_blank_middle_cell() -> bytes:
    sheet = """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>material_name</t></is></c>
      <c r="B1" t="inlineStr"><is><t>material_category</t></is></c>
      <c r="C1" t="inlineStr"><is><t>uom</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>Brass Rod</t></is></c>
      <c r="C2" t="inlineStr"><is><t>KG</t></is></c>
    </row>
  </sheetData>
</worksheet>"""
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    workbook = """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
  xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Raw Materials" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return out.getvalue()


def test_template_csv_uses_supported_upload_columns():
    header = MaterialOnboardingService.template_csv().decode("utf-8").splitlines()[0]

    assert header.split(",") == FIELDS
    assert {"material_name", "material_category", "uom"}.issubset(set(FIELDS))


def test_xlsx_reader_preserves_blank_middle_cells():
    rows = MaterialOnboardingService._read_xlsx(_xlsx_with_blank_middle_cell())

    assert rows == [
        {
            "material_name": "Brass Rod",
            "material_category": "",
            "uom": "KG",
        }
    ]


def test_suggest_mapping_keeps_common_customer_headers():
    mapping = MaterialOnboardingService.suggest_mapping(["Material Code", "Name", "Category", "Unit"])

    assert mapping == {
        "Material Code": "item_code",
        "Name": "material_name",
        "Category": "material_category",
        "Unit": "uom",
    }
