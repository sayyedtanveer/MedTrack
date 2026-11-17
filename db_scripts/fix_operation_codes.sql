-- Fix null operation_code values in operations table
-- SAFE: Uses 10-character limit (OP-xxxxxx = 10 chars max)
-- 
-- Issue: Original query generated strings like "OP-xxxxxxxx" (11 chars)
-- which exceeded VARCHAR(10) limit
--
-- Solution: Use first 6 characters of UUID instead of 8
-- Format: OP-{6-char-uuid-hex} = exactly 9 characters (within limit)

-- Step 1: Verify current state
SELECT COUNT(*) as null_operation_codes, COUNT(DISTINCT tenant_id) as affected_tenants
FROM operations 
WHERE operation_code IS NULL;

-- Step 2: Fix null operation_code values
UPDATE operations 
SET operation_code = 'OP-' || SUBSTRING(id::text, 1, 6)
WHERE operation_code IS NULL;

-- Step 3: Verify the fix
SELECT operation_code, COUNT(*) as count, LENGTH(operation_code) as code_length
FROM operations 
GROUP BY operation_code
ORDER BY code_length DESC, operation_code;

-- Step 4: Check for any duplicates (should be 0 since unique constraint exists per tenant)
SELECT tenant_id, operation_code, COUNT(*) as duplicate_count
FROM operations 
WHERE is_deleted = false
GROUP BY tenant_id, operation_code
HAVING COUNT(*) > 1;

-- Step 5: Verify all operation_codes are now populated
SELECT COUNT(*) as total_records, 
       COUNT(operation_code) as populated_codes,
       COUNT(*) - COUNT(operation_code) as remaining_nulls
FROM operations
WHERE is_deleted = false;
