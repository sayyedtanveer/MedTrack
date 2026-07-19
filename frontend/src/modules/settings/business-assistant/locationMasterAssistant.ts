import type { BusinessAssistantConfig } from "@/components/shared/BusinessAssistantPanel"

export const locationMasterAssistant: BusinessAssistantConfig = {
  pageTitle: "Storage Locations",

  about:
    "Storage Locations defines the physical areas within your warehouse where materials are stored, inspected, and dispatched. " +
    "MedTrack uses a single-warehouse model — you configure one root location of type 'warehouse', then add racks, bins, quarantine areas, production zones, and shipping areas as child locations beneath it. " +
    "These locations are used in Material assignments, GRN receipts, QC workflows, and subcontracting operations.",

  businessPurpose:
    "Without storage locations, you cannot track where materials physically are. When a GRN arrives, the system needs to know: which bin did this go into? When QC rejects material, it needs a Quarantine location to move it to. " +
    "When production needs to pick material, it needs to know which rack to pull from. " +
    "This page is where you build the map of your physical warehouse before any inventory movement begins.",

  erpFlow: [
    { label: "Company Setup" },
    { label: "Unit Master" },
    { label: "Material Categories" },
    { label: "Storage Locations", active: true, description: "You are here" },
    { label: "Materials (location_id assignment)" },
    { label: "GRN (goods receipt)" },
    { label: "QC Inspection" },
    { label: "Subcontracting" },
  ],

  canDo: [
    "View all configured locations in a hierarchical table (warehouse → rack → bin)",
    "Create new locations with name, code, type, and parent location",
    "Edit location name, code, type, and parent",
    "Deactivate locations to remove them from material assignment dropdowns",
    "Search locations by name or code",
    "Filter by location type and status",
    "See the hierarchy indentation showing parent-child relationships",
  ],

  screenWalkthrough: [
    {
      section: "Name column",
      purpose: "The display name of the storage location (e.g. Raw Material Store, Rack A, Shelf 1).",
      impact: "This name appears in Material assignment dropdowns, GRN location fields, and QC movement fields across the ERP.",
    },
    {
      section: "Code column",
      purpose: "Optional short code for the location (e.g. WH-01, RACK-A, BIN-A1).",
      impact: "Used in reports and barcoding workflows where a short identifier is needed instead of the full name.",
    },
    {
      section: "Type badge",
      purpose: "Indicates the role of this location: warehouse (blue), rack (slate), bin (gray), quarantine (amber), production (green), shipping (indigo).",
      impact: "Type determines how the location appears in workflow-specific dropdowns. QC workflows specifically look for quarantine-type locations.",
    },
    {
      section: "Parent column",
      purpose: "Shows the immediate parent location in the hierarchy.",
      impact: "Child locations inherit the context of their parent. A bin under Rack A in the Raw Material Store is understood to be in that area of the warehouse.",
    },
    {
      section: "Hierarchy indentation",
      purpose: "Child locations appear indented under their parent in the table.",
      impact: "Provides a visual map of your warehouse structure. Maximum 3 levels: Warehouse → Rack → Bin.",
    },
    {
      section: "Actions column",
      purpose: "Edit opens the drawer. Deactivate triggers a confirmation dialog.",
      impact: "Deletion is blocked if materials or child locations reference this location. The error shows the count.",
    },
  ],

  fieldGuide: [
    {
      field: "Name",
      purpose: "The human-readable name of the storage location.",
      meaning: "This is what your warehouse team and system users see in every dropdown and report.",
      example: "Raw Material Store, FG Store, QC Hold, Rejected Area, Rack A, Shelf 1",
      recommended: "Descriptive and unique per tenant. Max 100 characters.",
      bestPractice: "Use names that match the physical labels on your racks and areas so there is no confusion between the system and the warehouse floor.",
    },
    {
      field: "Code",
      purpose: "Optional short identifier for the location.",
      meaning: "Used in reports and barcoding where a compact code is preferred over the full name.",
      example: "WH-RM, WH-FG, QC-HOLD, RACK-A, SHELF-A1",
      recommended: "Optional. Max 50 characters. No spaces recommended.",
    },
    {
      field: "Location Type",
      purpose: "Classifies the role and level of this location in the warehouse hierarchy.",
      meaning: "warehouse = the single facility root; rack = intermediate storage area; bin = smallest storage unit; quarantine = materials under inspection hold; production = manufacturing floor area; shipping = dispatch/outbound area.",
      example: "warehouse (blue), rack (slate), bin (gray), quarantine (amber), production (green), shipping (indigo)",
      recommended: "Required. Must match the physical purpose of the location.",
      bestPractice: "Create one and only one warehouse-type location as the root of your hierarchy. All other locations should be children of this root.",
    },
    {
      field: "Parent Location",
      purpose: "The location this location sits inside in the hierarchy.",
      meaning: "Establishes the Warehouse → Rack → Bin tree structure. A bin with parent 'Rack A' is understood to be physically inside Rack A.",
      example: "Rack A (parent: Raw Material Store); Shelf 1 (parent: Rack A)",
      recommended: "Optional for warehouse-type (it is the root). Required for rack, bin, and other child locations.",
      bestPractice: "Maximum 3 levels deep. Circular references (A → B → A) are blocked by the system.",
    },
    {
      field: "Is Active",
      purpose: "Controls whether this location appears in material assignment and GRN dropdowns.",
      meaning: "Inactive locations are hidden from new assignments. Existing materials that already reference the location continue to function.",
      example: "Active = available in dropdowns. Inactive = hidden from dropdowns.",
      recommended: "Deactivate rather than delete when a location is taken out of use.",
    },
  ],

  buttonGuide: [
    {
      button: "Add Location",
      what: "Opens the Drawer form to create a new storage location.",
      continues: "Fill in name, type, optional code and parent location; save to make it available in material assignment dropdowns.",
      reversible: true,
    },
    {
      button: "Edit",
      what: "Opens the Drawer form pre-populated with the selected location's current values.",
      continues: "All fields including parent location are editable. Self-reference is blocked in the parent selector.",
      reversible: true,
    },
    {
      button: "Deactivate",
      what: "Opens a confirmation dialog before hiding the location from active use.",
      continues: "After confirmation, the location is Inactive. Existing material references are preserved.",
      reversible: true,
    },
  ],

  beforeYouStart: [
    "Unit Master and Material Categories are configured",
    "You have ADMIN, TENANT_ADMIN, or MANAGER role to create or edit locations",
    "You have a floor plan or list of your physical warehouse areas",
    "Plan your hierarchy before creating locations: start with the warehouse root, then racks, then bins",
    "Identify which location will serve as your Quarantine / QC Hold area — QC workflows require it",
    "Create all locations before assigning them to materials",
  ],

  afterSave: [
    { label: "Location created / updated" },
    { label: "Location appears in Material assignment dropdown" },
    { label: "Location available in GRN receipt location field" },
    { label: "Quarantine-type location available for QC workflows" },
    { label: "Audit log entry recorded" },
  ],

  bestPractices: [
    "Create ONE warehouse-type root location first, then add all racks and bins as children — this is a single-warehouse system",
    "Always create a Quarantine or QC Hold location (type: quarantine) before starting any QC or inspection workflows",
    "Match location names to physical labels on your warehouse floor to eliminate confusion",
    "Use 3 levels maximum: Warehouse → Rack → Bin. Deeper hierarchies are not supported",
    "Assign materials to the most specific location possible (bin > rack > warehouse) for accurate stock reporting",
    "Deactivate locations that are taken out of use rather than deleting them",
  ],

  commonMistakes: [
    "Creating multiple warehouse-type locations — MedTrack is a single-warehouse system; only one root warehouse location should exist",
    "Not setting location type correctly — a quarantine area created as 'bin' type will not appear in QC workflow dropdowns that filter for quarantine-type locations",
    "Creating circular parent references (Rack A → Rack B → Rack A) — the system blocks this at the form level, but plan your hierarchy before entering data",
    "Trying to delete a location that materials reference — the system blocks deletion and shows the material count; deactivate instead",
    "Forgetting to create a Quarantine / QC Hold location before starting QC workflows — QC moves will fail with no destination",
  ],

  relatedScreens: [
    { label: "Unit Master", href: "/settings/master-data/units" },
    { label: "Material Categories", href: "/settings/master-data/categories" },
    { label: "Materials", href: "/inventory/materials" },
    { label: "Company Setup", href: "/settings/company-setup" },
  ],

  faqs: [
    {
      question: "Can I have multiple warehouses?",
      answer: "No. MedTrack is a single-warehouse system. Create exactly one location with type 'warehouse' as your root. All racks, bins, quarantine areas, and other zones are child locations within that single facility.",
    },
    {
      question: "What is the difference between rack, bin, and production location types?",
      answer: "Rack = intermediate storage area that contains bins (e.g. Rack A in the Raw Material Store). Bin = smallest storage unit where material physically sits (e.g. Shelf 1). Production = manufacturing floor area used during work order operations. Quarantine = holding area for materials under QC inspection or rejection. Each type has a distinct color badge in the table.",
    },
    {
      question: "How deep can the hierarchy go?",
      answer: "Maximum 3 levels: Warehouse → Rack → Bin. For example: Raw Material Store (warehouse) → Rack A (rack) → Shelf 1 (bin). You cannot add a 4th level.",
    },
    {
      question: "Why is deletion blocked for a location with active children?",
      answer: "Deleting a parent location while it has active children would leave the children orphaned with an invalid parent reference. The system blocks deletion and shows the child count. You must deactivate or delete the children first, then deactivate or delete the parent.",
    },
    {
      question: "Does deactivating a location affect materials assigned to it?",
      answer: "No. Deactivating a location only hides it from the dropdown when creating new material assignments or GRN entries. Existing materials that already reference the location continue to function and display correctly.",
    },
    {
      question: "What location should I assign to materials during initial setup?",
      answer: "Assign materials to the most specific location that reflects where they are physically stored — ideally a bin-level location. If your warehouse is not yet racked and binned, assign to the warehouse root or a rack-level location and refine later.",
    },
  ],

  tips: [
    "A typical setup: Raw Material Store (warehouse) → Rack A (rack) → Shelf 1 (bin). Start with this skeleton, then add more racks and bins as needed.",
    "Create a 'QC Hold' location of type quarantine before running your first goods receipt — GRN-to-QC moves need it",
    "Color-coded type badges make it easy to see the warehouse map at a glance in the table",
    "The hierarchy indentation in the table gives you a visual floor plan of your warehouse — check it after adding new locations",
  ],

  warnings: [
    "Do not create more than one warehouse-type location — MedTrack is single-warehouse; multiple warehouse roots are not supported",
    "Deleting a location with active materials or active child locations is blocked (HTTP 409) — deactivate instead",
    "Circular parent references are prevented by the form — plan your hierarchy before creating locations to avoid reorganizing later",
  ],

  successResult: [
    "One warehouse-type root location exists",
    "Racks and bins appear as indented children under the warehouse in the table",
    "At least one quarantine-type location exists for QC workflows",
    "Location dropdown in Material forms shows the configured locations",
    "All location type badges display the correct colors",
    "Audit log shows each location creation and edit",
  ],
}
