import type { BusinessAssistantConfig } from "@/components/shared/BusinessAssistantPanel"

export const unitMasterAssistant: BusinessAssistantConfig = {
  pageTitle: "Units of Measure",

  about:
    "Units of Measure defines every measurement unit available across MedTrack — KG, Gram, Liter, ML, Piece, Box, Meter, Roll and any custom unit your business needs. " +
    "These units appear in Material forms, Product forms, BOM line quantities, Purchase Orders, and inventory transactions. " +
    "Without correctly configured units, the ERP cannot track quantities accurately across the supply chain.",

  businessPurpose:
    "Every material in your ERP is measured in a unit. When you receive 500 KG of steel, the '500' is meaningless without 'KG'. " +
    "When a BOM says a tablet contains 250 MG of active ingredient, the 'MG' unit controls how the system calculates batch quantities and purchase requirements. " +
    "This page is where you define and maintain all those units before any material or product is created.",

  erpFlow: [
    { label: "Company Setup" },
    { label: "Unit Master", active: true, description: "You are here" },
    { label: "Material Categories" },
    { label: "Storage Locations" },
    { label: "Materials" },
    { label: "Products" },
    { label: "Bill of Materials" },
  ],

  canDo: [
    "View all configured units of measure in one table",
    "Create new units with code, name, and decimal precision",
    "Edit unit name and precision (code is locked after creation)",
    "Deactivate units to hide them from new dropdowns",
    "Search units by code or name",
    "Filter by Active / Inactive / All status",
  ],

  screenWalkthrough: [
    {
      section: "Code column",
      purpose: "The short uppercase identifier for the unit (e.g. KG, ML, PCS).",
      impact: "Appears in all dropdowns, BOM lines, purchase orders, and inventory records. Immutable after creation.",
    },
    {
      section: "Name column",
      purpose: "The full human-readable name of the unit (e.g. Kilogram, Milliliter, Pieces).",
      impact: "Displayed in forms and reports where space allows the full name.",
    },
    {
      section: "Precision column",
      purpose: "How many decimal places are allowed when entering quantities for this unit.",
      impact: "Precision 0 = whole numbers only (Pieces). Precision 2 = up to 0.01 (KG). Precision 3 = up to 0.001 (MG for pharmaceuticals).",
    },
    {
      section: "Status badge",
      purpose: "Shows whether the unit is Active or Inactive.",
      impact: "Inactive units are hidden from all dropdowns in Material, Product, and BOM forms. Existing records that use the unit are not affected.",
    },
    {
      section: "Actions column",
      purpose: "Edit button opens the drawer to modify name and precision. Deactivate removes the unit from active use.",
      impact: "Code cannot be changed after creation. Use Deactivate instead of Delete when a unit is in use.",
    },
  ],

  fieldGuide: [
    {
      field: "Code",
      purpose: "Short uppercase identifier for the unit.",
      meaning: "Used as the display code in all dropdowns and transaction records throughout the ERP.",
      example: "KG, ML, PCS, MG, MTR",
      recommended: "2–10 uppercase alphanumeric characters. No spaces.",
      bestPractice: "Immutable after creation — choose carefully. Once materials reference this unit, the code cannot be changed.",
    },
    {
      field: "Name",
      purpose: "Full name of the unit of measure.",
      meaning: "Shown in forms and reports where the full name provides more clarity than the code alone.",
      example: "Kilogram, Milliliter, Pieces, Milligram, Meter",
      recommended: "Must be unique per tenant. Max 100 characters.",
    },
    {
      field: "Precision",
      purpose: "Number of decimal places allowed in quantity fields for this unit.",
      meaning: "Controls how precisely quantities can be entered across all forms that use this unit.",
      example: "0 for Pieces (no fractions), 2 for KG (e.g. 1.25 KG), 3 for MG (e.g. 0.125 MG)",
      recommended: "0–6 decimal places. Default is 2.",
      bestPractice: "Set precision based on the smallest measurable increment for your business. Liquids typically need 2–3. Solid count units need 0.",
    },
    {
      field: "Is Active",
      purpose: "Controls whether this unit appears in dropdowns when creating new materials or products.",
      meaning: "Inactive units are hidden from new dropdowns but all existing records that reference the unit continue to work.",
      example: "Active = appears in dropdowns. Inactive = hidden from dropdowns, existing data preserved.",
      recommended: "Deactivate instead of deleting when a unit is no longer needed.",
    },
  ],

  buttonGuide: [
    {
      button: "Add Unit",
      what: "Opens the Drawer form to create a new unit of measure.",
      continues: "Fill in code, name, and precision; save to make the unit available across all forms.",
      reversible: true,
    },
    {
      button: "Edit",
      what: "Opens the Drawer form pre-populated with the selected unit's current values.",
      continues: "Code field is disabled — only name, precision, and active status can be changed.",
      reversible: true,
    },
    {
      button: "Deactivate",
      what: "Opens a confirmation dialog before hiding the unit from active dropdowns.",
      continues: "After confirmation, the unit's status changes to Inactive. Existing material and BOM references are preserved.",
      reversible: true,
    },
  ],

  beforeYouStart: [
    "Company profile has been created (Settings → Company Setup)",
    "You have ADMIN, TENANT_ADMIN, or MANAGER role to create or edit units",
    "You have decided on a consistent code convention (e.g. always uppercase, e.g. KG not kg)",
    "Configure units before creating any Materials, Products, or BOMs",
  ],

  afterSave: [
    { label: "Unit created / updated" },
    { label: "Unit appears in Material Base Unit dropdown" },
    { label: "Unit appears in Product Base Unit dropdown" },
    { label: "Unit appears in BOM line Unit dropdown" },
    { label: "Audit log entry recorded" },
  ],

  bestPractices: [
    "Create all required units before onboarding materials — changing a material's base unit after stock transactions is not retroactive",
    "Use uppercase codes consistently (KG not kg) — the system is case-sensitive in some contexts",
    "Set precision correctly from the start — especially for liquids and pharmaceuticals where fractions matter",
    "Keep codes short and memorable: KG, GM, LTR, ML, PCS, NOS, MTR, ROL",
    "Deactivate obsolete units rather than deleting them to preserve historical data",
    "Review units together with your production and procurement teams before going live",
  ],

  commonMistakes: [
    "Creating 'KG' and 'Kg' as separate units — case-insensitive duplicates cause confusion in reports and dropdowns",
    "Not setting precision correctly for liquids — ML needs precision 2 or 3, not 0; entering 0.5 ML would be blocked with precision 0",
    "Trying to delete a unit that materials already reference — the system blocks deletion; deactivate instead",
    "Creating units after materials are already in use — changing a material's base unit is not retroactive for existing stock entries",
    "Using overly long codes (e.g. 'KILOGRAM') — short codes like 'KG' are more readable in crowded table columns and dropdowns",
  ],

  relatedScreens: [
    { label: "Material Categories", href: "/settings/master-data/categories" },
    { label: "Storage Locations", href: "/settings/master-data/locations" },
    { label: "Materials", href: "/inventory/materials" },
    { label: "Company Setup", href: "/settings/company-setup" },
  ],

  faqs: [
    {
      question: "Can I change the code of a unit after creation?",
      answer: "No. The code field is locked after the unit is first saved. This is by design — changing a code after materials reference it would break traceability. If you need a different code, create a new unit and deactivate the old one.",
    },
    {
      question: "Why can't I delete a unit that is in use?",
      answer: "Deleting a unit that materials reference would leave those materials with a broken base unit — they would lose their quantity context. The system blocks deletion and shows how many materials reference the unit. Deactivate the unit instead; it disappears from dropdowns but existing records remain intact.",
    },
    {
      question: "What precision should I use for pharmaceutical units like MG?",
      answer: "Use precision 3 for MG to allow quantities like 0.125 MG. For ML use precision 2 (e.g. 0.50 ML). For solid count units like Tablets (TAB) or Capsules (CAP), use precision 0 since you cannot have half a tablet.",
    },
    {
      question: "Does deactivating a unit affect existing materials?",
      answer: "No. Deactivating a unit only hides it from the dropdown when creating new materials or BOMs. All existing materials that already use the unit continue to work normally — their base unit is preserved.",
    },
    {
      question: "Can the same unit be used in both materials and BOM lines?",
      answer: "Yes. A single unit like KG is available in Material Base Unit dropdowns, BOM line unit dropdowns, Purchase Order line unit fields, and inventory transaction forms — all from this same master list.",
    },
  ],

  tips: [
    "A pharmaceutical company should add MG (Milligram, precision 3) before creating any tablet formulation material",
    "The search box filters by both code and name simultaneously — type 'kg' or 'kilo' and it finds the same record",
    "Precision 0 for count units (Pieces, Nos, Box) prevents accidentally entering 1.5 pieces in a BOM",
    "If your supplier invoices in a different unit than your BOM (e.g. supplier sends in KG, BOM uses GM), configure both units — conversion is handled at the transaction level",
  ],

  warnings: [
    "Code is immutable after creation — double-check spelling and case before saving a new unit",
    "Deleting a unit used by active materials is blocked by the system (HTTP 409) — always deactivate instead",
    "Changing precision after materials are in use does not retroactively update existing stock entries",
  ],

  successResult: [
    "All required measurement units are visible in the Active filter",
    "Units appear in Material, Product, and BOM form dropdowns correctly",
    "Precision values match your business's measurement requirements",
    "Codes are consistent and uppercase across all units",
    "Audit log shows each unit creation and edit",
  ],
}
