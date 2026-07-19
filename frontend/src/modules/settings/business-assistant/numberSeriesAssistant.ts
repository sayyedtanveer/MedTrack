import type { BusinessAssistantConfig } from "@/components/shared/BusinessAssistantPanel"

// ── Number Series LIST page ───────────────────────────────────────────────────

export const numberSeriesListAssistant: BusinessAssistantConfig = {
  pageTitle: "Number Series",

  about:
    "Number Series defines how MedTrack automatically generates unique identification codes for every business document — materials, products, purchase orders, sales orders, invoices, work orders, batches, GRNs, customers and suppliers. " +
    "Without proper number series configuration, the ERP cannot create records consistently, making traceability and auditing impossible. " +
    "This page is the control panel for all code generation across your entire MedTrack workspace.",

  businessPurpose:
    "Every business document needs a unique, traceable code. RM-ABC-000001 tells you immediately it is a Raw Material, carries the item abbreviation, and is the first record in the sequence. Without this, you cannot find documents quickly, cannot run quality audits, and cannot track materials through production. This page controls that entire system.",

  erpFlow: [
    { label: "Company Setup" },
    { label: "Business Configuration" },
    { label: "Number Series", active: true, description: "You are here" },
    { label: "Create Materials / Products" },
    { label: "Purchase Orders" },
    { label: "Manufacturing & Work Orders" },
    { label: "Sales Orders & Dispatch" },
    { label: "Finance & Invoicing" },
  ],

  canDo: [
    "View all configured entity types in one table",
    "See the current format preview for each entity",
    "Check whether auto-generation is enabled per entity",
    "Navigate to edit any individual entity configuration",
    "Initialize default configurations if none exist yet",
  ],

  screenWalkthrough: [
    {
      section: "Entity Type column",
      purpose: "Lists every business document type that requires a unique code in MedTrack.",
      impact: "Each row represents an independent numbering series — changing one does not affect others.",
    },
    {
      section: "Auto Generate badge",
      purpose: "Shows whether MedTrack automatically generates codes when new records are created.",
      impact: "If Off, users must enter codes manually. Risk of duplicate or inconsistent codes increases.",
    },
    {
      section: "Prefix column",
      purpose: "The short uppercase code that appears at the start of every generated document number.",
      impact: "Makes documents instantly recognizable. PO = Purchase Order, SO = Sales Order, WO = Work Order.",
    },
    {
      section: "Format Preview column",
      purpose: "Shows a sample code based on the current configuration for that entity.",
      impact: "Lets you verify the format before any real records are created.",
    },
    {
      section: "Edit button",
      purpose: "Opens the detailed configuration page for that specific entity type.",
      impact: "Admin-only. Non-admin users see a View button instead.",
    },
    {
      section: "Initialize Default Configuration button",
      purpose: "Only visible when no configurations exist. Seeds all entity types with sensible defaults.",
      impact: "Must be done before creating any materials, products or orders.",
    },
  ],

  fieldGuide: [
    {
      field: "Entity Type",
      purpose: "The type of business document this configuration applies to.",
      meaning: "Each entity type (material, product, purchase_order, etc.) has its own independent numbering series.",
      example: "purchase_order",
      recommended: "Do not change — these are system-defined.",
    },
    {
      field: "Auto Generate",
      purpose: "Controls whether MedTrack automatically creates the code when a new record is saved.",
      meaning: "When On, users never type a code — the system generates it. When Off, users must type it manually.",
      example: "On",
      recommended: "Keep On for all entity types in production.",
      bestPractice: "Only disable Auto Generate if you are migrating existing records from another system.",
    },
    {
      field: "Prefix",
      purpose: "The short code prepended to every document number for that entity type.",
      meaning: "Makes documents immediately recognizable at a glance. RM = Raw Material, PO = Purchase Order.",
      example: "PO",
      recommended: "2–4 uppercase letters. No spaces or special characters.",
      bestPractice: "Each entity type must have a unique prefix. Duplicate prefixes cause confusion in reports.",
    },
    {
      field: "Format Preview",
      purpose: "A sample code showing what generated numbers will look like.",
      meaning: "Based on the current prefix, abbreviation, separator and sequence length settings.",
      example: "PO-000001",
      recommended: "Review this before saving any configuration.",
    },
  ],

  buttonGuide: [
    {
      button: "Edit",
      what: "Opens the Number Series configuration page for the selected entity type.",
      continues: "Configure prefix, sequence length, separator and abbreviation settings.",
      reversible: true,
    },
    {
      button: "Initialize Default Configuration",
      what: "Seeds the database with default number series settings for all entity types.",
      continues: "After initialization, you can edit each entity type individually.",
      reversible: true,
    },
  ],

  beforeYouStart: [
    "Company profile has been created (Settings → Company Setup)",
    "You have ADMIN role — only admins can edit Number Series",
    "No materials, products or orders have been created yet (configure before first use)",
  ],

  afterSave: [
    { label: "Configuration Active" },
    { label: "Create Material / Product / Order" },
    { label: "System generates code automatically" },
    { label: "Code appears in record and all related documents" },
  ],

  bestPractices: [
    "Configure all entity types before creating any records",
    "Keep prefixes short (2–4 chars) and uppercase",
    "Use a consistent separator character across all entity types (e.g. always '-')",
    "Enable 'Lock after save' to prevent code changes once a record is created",
    "Review format previews before going live",
    "Never use duplicate prefixes across entity types",
  ],

  commonMistakes: [
    "Configuring number series after materials or orders already exist — existing records keep old codes",
    "Using duplicate prefixes (e.g. both Material and Product using 'RM') causing confusion in reports",
    "Disabling Auto Generate without a clear manual numbering policy, leading to duplicate codes",
    "Using long sequence lengths (10 digits) unnecessarily — 6 is sufficient for most operations",
    "Forgetting to initialize configuration before the team starts creating records",
  ],

  relatedScreens: [
    { label: "Business Configuration", href: "/settings/business-config" },
    { label: "Company Setup", href: "/settings/company-setup" },
    { label: "Materials", href: "/inventory/materials" },
    { label: "Products", href: "/products" },
    { label: "Purchase Orders", href: "/procurement/purchase-orders" },
  ],

  faqs: [
    {
      question: "Can I change the prefix after records have been created?",
      answer: "Yes, but existing records keep their old codes. Only new records use the updated prefix. This can cause inconsistency in reports — avoid changing prefixes in production.",
    },
    {
      question: "What does 'Auto Generate' actually do?",
      answer: "When enabled, MedTrack automatically creates the next code in sequence every time a new record is saved. You never have to type it. When disabled, users must enter the code manually.",
    },
    {
      question: "What is the Format Preview column?",
      answer: "It shows a sample code based on current settings. The actual generated codes will have real sequence numbers (000001, 000002...) instead of zeros.",
    },
    {
      question: "Can numbering be reset to start from 1 again?",
      answer: "Not currently implemented in MedTrack. Sequence numbers are cumulative and cannot be reset through the UI.",
    },
    {
      question: "What happens if I do not initialize the configuration?",
      answer: "Without initialization, the system cannot auto-generate codes. Record creation will fail or require manual code entry.",
    },
  ],

  tips: [
    "Configure Number Series as the very first step before any other data entry",
    "Use meaningful prefixes: PO for Purchase Orders, SO for Sales Orders, WO for Work Orders",
    "Sequence length 6 supports up to 999,999 records — sufficient for most businesses",
    "The Format Preview column is your safety check before going live",
  ],

  warnings: [
    "Changing prefixes after records exist will make old and new records use different codes — avoid in production",
    "Disabling Auto Generate without a manual coding policy risks duplicate or missing codes",
    "Deleting configurations is not supported through the UI — contact your system administrator",
  ],

  successResult: [
    "All entity types show a valid Format Preview",
    "Auto Generate is enabled for all active entity types",
    "Prefixes are unique across all entity types",
    "New records now automatically receive properly formatted codes",
    "Existing records are not affected by configuration changes",
  ],
}

// ── Number Series ENTITY CONFIG page ─────────────────────────────────────────

export function makeNumberSeriesEntityAssistant(entityLabel: string): BusinessAssistantConfig {
  return {
    pageTitle: `Number Series — ${entityLabel}`,

    about:
      `This page configures exactly how ${entityLabel} codes are generated in MedTrack. ` +
      `You control the prefix, whether item abbreviations are included, how many digits the sequence uses, and what separator character is used between parts. ` +
      `A live preview shows you the exact format before you save.`,

    businessPurpose:
      `${entityLabel} codes must be unique, consistent and recognizable across your organization. ` +
      `A well-configured number series means every ${entityLabel.toLowerCase()} can be identified immediately from its code — ` +
      `making warehouse operations, procurement, quality control and financial audits faster and more accurate.`,

    erpFlow: [
      { label: "Business Configuration" },
      { label: "Number Series List" },
      { label: `${entityLabel} Series Config`, active: true, description: "You are here" },
      { label: `Create ${entityLabel}` },
      { label: "Code auto-generated" },
      { label: "Document enters workflow" },
    ],

    canDo: [
      `Configure the prefix for ${entityLabel} codes`,
      "Enable or disable auto-generation",
      "Set the manual override policy (who can enter codes manually)",
      "Include or exclude item abbreviation in the code",
      "Set abbreviation length (2–6 characters)",
      "Set sequence length (4–10 digits)",
      "Choose the separator character",
      "Lock codes after creation (immutable)",
      "Edit sub-type prefixes if applicable",
      "View a live preview of the generated format",
      "Review the change history in the Audit Log tab",
    ],

    screenWalkthrough: [
      {
        section: "Live Preview",
        purpose: "Shows a real-time preview of what a generated code will look like based on your current settings.",
        impact: "Updates instantly as you type. Use this to verify the format before saving.",
      },
      {
        section: "General Settings card",
        purpose: "Controls core numbering behavior: auto-generation, manual override policy, abbreviation, sequence length and separator.",
        impact: "These settings determine the structure of every new code created for this entity type.",
      },
      {
        section: "Sub-Type Prefixes table",
        purpose: "Only visible when the entity type has sub-types (e.g. materials can be Raw Material, Packaging, etc.).",
        impact: "Each sub-type can have its own prefix (RM, PKG, FG) making codes self-identifying by material category.",
      },
      {
        section: "Audit Log tab",
        purpose: "Shows a full history of every change made to this entity's number series configuration.",
        impact: "Provides traceability for compliance and debugging — who changed what and when.",
      },
    ],

    fieldGuide: [
      {
        field: "Auto-generate codes",
        purpose: "When enabled, MedTrack creates the code automatically on record save.",
        meaning: "Users never need to type a code. The system picks the next number in sequence.",
        example: "✓ Enabled",
        recommended: "Always keep enabled in production.",
        bestPractice: "Only disable when migrating records from a legacy system with existing codes.",
      },
      {
        field: "Manual Override Policy",
        purpose: "Controls who is allowed to type a custom code instead of using the auto-generated one.",
        meaning: "Never = nobody can override. Admin Only = only admin users can. Always = any user can.",
        example: "Never",
        recommended: "Set to 'Never' for standard production use.",
        bestPractice: "Use 'Admin Only' during data migration, then switch back to 'Never'.",
      },
      {
        field: "Include abbreviation",
        purpose: "Adds a short text abbreviation (derived from the record name) into the generated code.",
        meaning: "Code becomes PREFIX-ABC-000001 instead of PREFIX-000001. Makes codes more readable.",
        example: "✓ Enabled → RM-STE-000001 (Steel = STE)",
        recommended: "Enable for Materials and Products where item names are meaningful.",
      },
      {
        field: "Abbreviation Length",
        purpose: "How many characters of the item name to include in the abbreviation segment.",
        meaning: "3 characters is the standard. More characters make codes longer but more descriptive.",
        example: "3",
        recommended: "3 characters — balances readability and code length.",
        bestPractice: "Must be between 2 and 6. Changing after records exist does not retroactively update old codes.",
      },
      {
        field: "Sequence Length",
        purpose: "How many digits the numeric counter part of the code uses.",
        meaning: "6 digits supports up to 999,999 unique codes. The counter is zero-padded (000001, 000002...).",
        example: "6 → 000001",
        recommended: "6 for most entity types. Use 8 only if you expect over 1 million records.",
        bestPractice: "Do not reduce sequence length after records exist — existing codes would not match.",
      },
      {
        field: "Separator",
        purpose: "The character placed between each segment of the code (prefix, abbreviation, sequence).",
        meaning: "Typically a hyphen (-). Can be empty for no separator or custom characters.",
        example: "- → RM-STE-000001",
        recommended: "Use '-' consistently across all entity types.",
        bestPractice: "Keep the same separator character across all entity types for consistency.",
      },
      {
        field: "Lock code after save",
        purpose: "When enabled, a generated code cannot be changed after the record is first saved.",
        meaning: "Prevents accidental or unauthorized code changes. Essential for financial and audit compliance.",
        example: "✓ Enabled",
        recommended: "Always enable in production.",
        bestPractice: "This is a one-way setting per record — once locked, codes cannot be edited through the UI.",
      },
      {
        field: "Sub-Type Prefix",
        purpose: "A per-sub-type prefix applied in addition to the entity prefix.",
        meaning: "Materials with type 'raw_material' get prefix RM. Materials with type 'finished_good' get FG.",
        example: "RM (for Raw Material sub-type)",
        recommended: "Use meaningful 2–4 character uppercase codes.",
        bestPractice: "Each sub-type prefix within an entity must be unique to avoid code collisions.",
      },
    ],

    buttonGuide: [
      {
        button: "Save Configuration",
        what: "Saves all changes made on this page — general settings, abbreviation, sequence and prefixes.",
        continues: "Configuration becomes active immediately. Next new record uses the new format.",
        reversible: true,
      },
      {
        button: "Cancel",
        what: "Discards all unsaved changes and navigates back to the Number Series list.",
        continues: "No changes are saved. The previous configuration remains active.",
        reversible: true,
      },
    ],

    beforeYouStart: [
      "You have ADMIN role",
      "You are in Settings → Business Configuration → Number Series",
      "No records of this entity type have been created yet (best practice)",
      "You have decided on the prefix convention for your organization",
    ],

    afterSave: [
      { label: "Configuration saved & active" },
      { label: "Audit log entry created" },
      { label: `Create new ${entityLabel}` },
      { label: "ERP auto-generates code in new format" },
      { label: "Code appears on all related documents" },
    ],

    bestPractices: [
      `Configure ${entityLabel} series before any ${entityLabel.toLowerCase()} records are created`,
      "Use a short, memorable prefix that matches your organization's naming conventions",
      "Test the format preview before saving — make sure it looks right",
      "Enable 'Lock code after save' for all financial document types",
      "Keep sequence length at 6 unless you have very high volume (1M+ records)",
      "Be consistent — use the same separator across all entity types",
    ],

    commonMistakes: [
      `Changing the prefix after ${entityLabel.toLowerCase()} records exist — old records keep old codes, new ones get the new prefix`,
      "Setting abbreviation length to a value that makes codes too long for display fields",
      "Disabling 'Lock code after save' for financial documents — codes can be accidentally changed",
      "Using spaces or special characters in prefix — causes display and search issues",
      "Setting sequence length below 6 — risks running out of numbers faster than expected",
    ],

    relatedScreens: [
      { label: "Number Series List", href: "/settings/business-config/number-series" },
      { label: "Business Configuration", href: "/settings/business-config" },
    ],

    faqs: [
      {
        question: "Does saving change existing codes?",
        answer: "No. Existing records always keep the code they were originally generated with. Configuration changes only affect new records created after the save.",
      },
      {
        question: "What is the Audit Log tab?",
        answer: "It shows every change ever made to this entity's number series configuration — what changed, when, and what the old and new values were.",
      },
      {
        question: "What if I enable abbreviation but the item has no name?",
        answer: "The system will use a fallback placeholder. Always ensure items have meaningful names before auto-generating codes.",
      },
      {
        question: "Can I set different separators per sub-type?",
        answer: "No. The separator is shared across all sub-types within an entity. Only the prefix differs per sub-type.",
      },
      {
        question: "What does 'Lock code after save' actually prevent?",
        answer: "Once a record is saved with a generated code and lock is enabled, the code field cannot be edited through the UI. It prevents accidental renaming of documents.",
      },
    ],

    tips: [
      "The Live Preview updates instantly as you type — use it to verify before saving",
      "The Audit Log tab shows the full change history — useful for troubleshooting",
      "Sub-Type Prefixes are only visible if this entity type has sub-types defined",
      "Abbreviation adds the first N characters of the item name — meaningful item names produce better codes",
    ],

    warnings: [
      "Changing the prefix after records exist creates inconsistency — old codes use old prefix, new codes use new prefix",
      "Disabling auto-generation mid-operation requires someone to manually enter every future code",
      "Reducing sequence length below existing record count will not cause errors but will create confusion",
    ],

    successResult: [
      "Live Preview shows the expected code format",
      "Configuration is saved and immediately active",
      "An audit log entry is created recording the change",
      `New ${entityLabel.toLowerCase()} records will now auto-generate codes in the configured format`,
      "Existing records are not affected",
    ],
  }
}
