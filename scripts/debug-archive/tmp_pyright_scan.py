"""Find Pyright-style errors in supply_chain.py by pattern matching."""
lines = open("backend/app/interfaces/api/v1/routes/supply_chain.py", encoding="utf-8").read().splitlines()

errors = []

for i, line in enumerate(lines, 1):
    s = line.strip()

    # Duplicate top-level import
    if s.startswith("from fastapi.responses import StreamingResponse") and i > 100:
        errors.append((i, "DUPLICATE IMPORT - StreamingResponse imported twice at module level", s))

    # async def without await inside (heuristic: session.get result used directly)
    # Pattern: variable assigned without await from async call
    if "= session.get(" in s and "await" not in s:
        errors.append((i, "MISSING await on session.get()", s))

    # Optional attribute used directly in non-guarded str()
    # Only flag truly unguarded ones
    if "str(o.bom_id)" in s and "if o.bom_id" not in s:
        errors.append((i, "str(o.bom_id) without guard", s))

    # _bom_id assignment type annotation check
    if "_bom_id: uuid.UUID = o.bom_id" in s:
        errors.append((i, "OK: bom_id narrowed", s))

    # Possible None.something
    if ".batch_number" in s and "output_batch" in s and "if output_batch" not in s and "output_batch." in s:
        # check if output_batch could be None here
        errors.append((i, "POSSIBLE: output_batch might be None", s))

    # Return statement with output_batch that might not be bound
    if "output_batch.batch_number" in s:
        errors.append((i, "WARN: output_batch.batch_number — is output_batch always bound?", s))

print(f"Scanned {len(lines)} lines\n")
for lineno, label, content in errors:
    print(f"L{lineno:4d}  {label}")
    print(f"       {content[:110]}")
    print()
