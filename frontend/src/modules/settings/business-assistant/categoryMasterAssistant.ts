import type { BusinessAssistantConfig } from "@/components/shared/BusinessAssistantPanel"

export const categoryMasterAssistant: BusinessAssistantConfig = {
  pageTitle: "Material Categories",

  about:
    "Material Categories is the shared classification master used by both Materials and Products in MedTrack. " +
    "Every material and every product belongs to exactly one category — Metal, Packaging, Chemical, Consumable, Electrical, and so on. " +
    "Categories drive item code generation via the Number Series (the code_prefix field), power report filtering, and provide the taxonomy for your entire inventory. " +
    "This is a single shared master — there is no separate Product Category module. Products reuse the same category list.",

  businessPurpose:
    "Without categories, your inventory has no structure. You cannot filter materials by type, cannot generate meaningful item codes, and cannot run category-level cost or usage reports. " +
    "A well-configured category master ensures that RM-MET-000001 immediately tells you it is a Raw Material in the Metal category — before you even open the record. " +
    "Because products share this same master, a 'Packaging' category configured here appears in both the Material form and the Product form.",

  erpFlow: [
    { label: "Company Setup" },
    { label: "Unit Master" },
    { label: "Material Categories", active: true, description: "You are here" },
    { label: "Storage Locations" },
    { label: "Materials" },
    { label: "Products" },
    { label: "Number Series (code_prefix drives item code generation)" },
  ],

  canDo: [
    "View all configured categories with name, code prefix, material count, and status",
    "Create new categories with name, code prefix, description, and active toggle",
    "Edit all category fields including code prefix",
    "Deactivate categories to hide them from material and product dropdowns",
    "Search categories by name or code prefix",
    "Filter by Active / Inactive / All status",
    "See how many active materials reference each category",
  ],

  screenWalkthrough: [
    {
      section: "Name column",
      purpose: "The full category name shown in all Material and Product form dropdowns.",
      impact: "Must be unique per tenant. This is what your team sees when selecting a category during data entry.",
    },
    {
      section: "Code Prefix column",
      purpose: "Short 2–6 character uppercase code that the Number Series uses when generating item codes.",
      impact: "A category with prefix 'MET' causes all metal materials to receive codes like RM-MET-000001. Changing the prefix does not update existing codes — only new codes use the new prefix.",
    },
    {
      section: "Material Count column",
      purpose: "Shows how many active materials currently use this category.",
      impact: "A count greater than 0 means the category cannot be deleted — only deactivated. This protects referential integrity.",
    },
    {
      section: "Status badge",
      purpose: "Active = appears in material and product form dropdowns. Inactive = hidden from dropdowns.",
      impact: "Inactive categories are hidden from new record creation but all existing materials and products that use the category continue to display and function correctly.",
    },
    {
      section: "Actions column",
      purpose: "Edit opens the drawer. Deactivate triggers a confirmation dialog.",
      impact: "Deletion is blocked when materials reference the category. The system shows the material count in the rejection message.",
    },
  ],

  fieldGuide: [
    {
      field: "Name",
      purpose: "Full display name of the category.",
      meaning: "This name appears in the Category dropdown on every Material and Product form across MedTrack.",
      example: "Metal, Packaging, Chemical, Consumable, Electrical, Plastic",
      recommended: "Meaningful, specific names. Max 100 characters. Unique per tenant.",
      bestPractice: "Avoid generic names like 'Other' or 'Misc' — these make reports and filtering useless. Create specific categories instead.",
    },
    {
      field: "Code Prefix",
      purpose: "Short code used by the Number Series when auto-generating item codes for materials in this category.",
      meaning: "If a material's category has prefix 'MET', its auto-generated item code will be RM-MET-000001. The prefix is embedded in the item code.",
      example: "MET (Metal), PKG (Packaging), CHM (Chemical), CON (Consumable), ELE (Electrical)",
      recommended: "2–6 uppercase alphanumeric characters. Must be unique per tenant.",
      bestPractice: "Choose prefixes that will not collide as your category list grows. MET and MTL would cause confusion — pick one convention and stick to it.",
    },
    {
      field: "Description",
      purpose: "Optional free-text explanation of what materials belong in this category.",
      meaning: "Helps team members understand the scope of the category when creating new materials.",
      example: "All ferrous and non-ferrous metals used in fabrication and machining",
      recommended: "Optional but recommended for categories that might be ambiguous. Max 500 characters.",
    },
    {
      field: "Is Active",
      purpose: "Controls whether this category appears in Material and Product form dropdowns.",
      meaning: "Inactive categories are hidden from new record creation. Existing materials and products that reference the category continue to work.",
      example: "Active = available in dropdowns. Inactive = hidden from dropdowns.",
      recommended: "Deactivate rather than delete when a category is no longer needed.",
    },
  ],

  buttonGuide: [
    {
      button: "Add Category",
      what: "Opens the Drawer form to create a new category.",
      continues: "Fill in name, code prefix, and optional description; save to make the category available in Material and Product forms.",
      reversible: true,
    },
    {
      button: "Edit",
      what: "Opens the Drawer form pre-populated with the selected category's current values.",
      continues: "All fields are editable including code prefix — but note that changing code prefix does not update existing item codes.",
      reversible: true,
    },
    {
      button: "Deactivate",
      what: "Opens a confirmation dialog before hiding the category from dropdowns.",
      continues: "After confirmation, the category is Inactive. Existing material and product references are preserved.",
      reversible: true,
    },
  ],

  beforeYouStart: [
    "Company profile and Unit Master are configured (Units must exist before Materials can reference them)",
    "You have ADMIN, TENANT_ADMIN, or MANAGER role to create or edit categories",
    "You have agreed on your category taxonomy with your operations and finance teams",
    "You have decided on a code prefix convention (2–3 chars is most readable in item codes)",
    "Configure all categories before creating any Materials or Products",
  ],

  afterSave: [
    { label: "Category created / updated" },
    { label: "Category appears in Material form Category dropdown" },
    { label: "Category appears in Product form Category dropdown" },
    { label: "Number Series uses code_prefix for new item codes" },
    { label: "Audit log entry recorded" },
  ],

  bestPractices: [
    "Create all categories before onboarding materials — item codes are generated at creation time using code_prefix",
    "Keep category names specific and industry-standard (Metal, Packaging, Chemical) not vague (Raw, Misc, Other)",
    "Choose code prefixes that are unique and intuitive: MET, PKG, CHM, CON, ELE, PLS",
    "Remember: this same list appears in both Material and Product forms — do not create categories that only make sense for one type",
    "Do not change code_prefix after materials with that category already have item codes — the prefix change does not retroactively update existing codes",
    "Review categories together with your reporting and finance team — categories drive cost reports and inventory analysis",
  ],

  commonMistakes: [
    "Creating duplicate categories with different prefixes — e.g. both 'Packaging' (PKG) and 'Packaging Materials' (PKM) — causes confusion in reports and item codes",
    "Changing code_prefix after materials exist — existing item codes are not retroactively updated; old codes keep old prefix, new materials get the new prefix",
    "Creating a separate 'Product Category' master — products in MedTrack reuse this exact same category list; a separate module is never needed",
    "Using generic names like 'Other' or 'Misc' — makes category-level reports and inventory filtering useless",
    "Setting code prefixes longer than 4 characters — makes item codes unnecessarily long (RM-PACKAGING-000001 vs RM-PKG-000001)",
  ],

  relatedScreens: [
    { label: "Unit Master", href: "/settings/master-data/units" },
    { label: "Storage Locations", href: "/settings/master-data/locations" },
    { label: "Materials", href: "/inventory/materials" },
    { label: "Number Series", href: "/settings/business-config/number-series" },
  ],

  faqs: [
    {
      question: "Do Products use the same categories as Materials?",
      answer: "Yes — this is intentional. MedTrack uses a single material_categories table for both Materials and Products. When you create a 'Metal' category here, it appears in both the Material form and the Product form. You do not need and should not create a separate Product Category page.",
    },
    {
      question: "What is code_prefix and why does it matter?",
      answer: "code_prefix is the short code (e.g. MET, PKG) that Number Series embeds into auto-generated item codes. A metal raw material gets a code like RM-MET-000001. The prefix makes the item code self-identifying — you know immediately from the code that it is a Metal Raw Material.",
    },
    {
      question: "Can I change code_prefix after materials already exist?",
      answer: "Yes, you can change it — but it only affects new materials created after the change. Existing materials keep the item code they were generated with. This can cause inconsistency (old metal materials have PKG in their code, new ones have MET). Avoid changing prefixes once materials are in production.",
    },
    {
      question: "Why can't I delete a category with materials?",
      answer: "Deleting a category that materials reference would leave those materials with a broken category field. The system blocks deletion and shows the count of materials referencing the category. Deactivate the category instead — it disappears from dropdowns but all existing material and product records are preserved.",
    },
    {
      question: "How does the code prefix auto-suggestion work?",
      answer: "As you type the category name, the Code Prefix field automatically suggests a value derived from the first 3 uppercase letters of the name (e.g. 'Metal' → 'MET'). You can override this suggestion manually before saving.",
    },
  ],

  tips: [
    "A metal parts manufacturer should create 'Metal' (MET), 'Packaging' (PKG), 'Consumable' (CON) before any data entry — these same categories then appear in both Material and Product forms",
    "The Material Count column is your safety check before deactivating — a category with count 0 can be safely deleted",
    "Sort by Material Count descending to quickly see your most-used categories",
    "If your ERP is used across multiple product lines, consider industry-standard category names so reports remain meaningful across product lines",
  ],

  warnings: [
    "Changing code_prefix after materials exist creates item code inconsistency — old codes keep the old prefix, new codes use the new prefix",
    "Deleting a category with active materials is blocked (HTTP 409) — deactivate instead",
    "Products and Materials share this category list — do not create categories that would be confusing when applied to both",
  ],

  successResult: [
    "All required categories appear in the Active filter with correct names and prefixes",
    "Category dropdown in Material and Product forms shows the configured categories",
    "Material Count column correctly reflects how many materials use each category",
    "Code prefixes are unique and follow your naming convention",
    "Number Series generates item codes with the correct category prefix",
    "Audit log shows each category creation and edit",
  ],
}
