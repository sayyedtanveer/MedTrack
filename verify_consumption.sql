-- Verify Consumption Logic is Working
-- Run this after backend restart to check subcontract inventory state

-- 1. Check if consumed_quantity column exists
SELECT 
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'subcontract_order_lines' 
  AND column_name = 'consumed_quantity';

-- 2. Show all subcontract orders with their current state
SELECT 
    so.order_number,
    so.status,
    so.order_date,
    m.code as semi_finished_code,
    m.name as semi_finished_name,
    so.ordered_quantity,
    so.received_quantity,
    v.name as subcontractor_name
FROM subcontract_orders so
JOIN materials m ON so.material_id = m.id
JOIN vendors v ON so.subcontractor_id = v.id
ORDER BY so.order_date DESC
LIMIT 10;

-- 3. Show raw materials with their consumption status for recent orders
SELECT 
    so.order_number,
    sol.line_number,
    rm.code as raw_material_code,
    rm.name as raw_material_name,
    sol.required_quantity,
    sol.issued_quantity,
    sol.consumed_quantity,  -- Should be > 0 after receipt
    sol.returned_quantity,
    (sol.issued_quantity - sol.consumed_quantity - sol.returned_quantity) as remaining_at_subcontractor
FROM subcontract_order_lines sol
JOIN subcontract_orders so ON sol.subcontract_order_id = so.id
JOIN materials rm ON sol.material_id = rm.id
WHERE so.order_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY so.order_date DESC, sol.line_number;

-- 4. Check stock levels for raw materials used in subcontracting
SELECT 
    m.code,
    m.name,
    m.current_stock,
    m.available_stock,
    m.reserved_stock,
    m.minimum_stock_level
FROM materials m
WHERE m.id IN (
    SELECT DISTINCT material_id 
    FROM subcontract_order_lines
    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
)
ORDER BY m.code;

-- 5. Check inventory transactions for raw materials (issues and consumptions)
SELECT 
    it.transaction_date,
    it.transaction_type,
    m.code as material_code,
    it.quantity,
    it.reference_type,
    it.reference_id,
    l.name as location_name,
    it.notes
FROM inventory_transactions it
JOIN materials m ON it.material_id = m.id
LEFT JOIN locations l ON it.location_id = l.id
WHERE it.transaction_type IN ('SUBCONTRACT_ISSUE', 'SUBCONTRACT_CONSUMPTION', 'SUBCONTRACT_RETURN')
  AND it.transaction_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY it.transaction_date DESC, m.code;

-- 6. Show stock by location for materials in recent subcontracts
SELECT 
    m.code,
    m.name,
    l.name as location_name,
    l.location_type,
    SUM(sl.quantity) as quantity_at_location
FROM stock_levels sl
JOIN materials m ON sl.material_id = m.id
JOIN locations l ON sl.location_id = l.id
WHERE m.id IN (
    SELECT DISTINCT material_id 
    FROM subcontract_order_lines
    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
)
GROUP BY m.code, m.name, l.name, l.location_type
ORDER BY m.code, l.location_type, l.name;
