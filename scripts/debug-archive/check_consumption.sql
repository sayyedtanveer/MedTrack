-- Check if consumption is happening after subcontract receipt

-- 1. Check if consumed_quantity column exists
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name='subcontract_order_lines' 
AND column_name='consumed_quantity';

-- 2. Check recent subcontract orders
SELECT 
    o.order_number,
    o.status,
    o.quantity as output_qty,
    o.received_quantity,
    l.material_id,
    l.required_quantity,
    l.issued_quantity,
    l.consumed_quantity,
    l.returned_quantity
FROM subcontract_orders o
JOIN subcontract_order_lines l ON l.subcontract_order_id = o.id
WHERE o.status IN ('materials_issued', 'partially_received', 'completed')
ORDER BY o.created_at DESC
LIMIT 10;

-- 3. Check stock levels for materials at subcontractor locations
SELECT 
    m.code,
    m.name,
    l.name as location,
    l.type as location_type,
    sl.quantity,
    sl.stock_status
FROM stock_levels sl
JOIN materials m ON m.id = sl.material_id
JOIN locations l ON l.id = sl.location_id
WHERE l.type = 'subcontractor'
AND sl.quantity > 0
AND sl.is_deleted = false
ORDER BY m.code;
