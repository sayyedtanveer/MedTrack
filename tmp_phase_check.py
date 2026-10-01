errors = []
def ck(path, present=None, absent=None):
    c = open(path, encoding='utf-8').read()
    for p, d in (present or []):
        if p in c: print(f'OK   {d}')
        else: errors.append(d); print(f'FAIL {d}')
    for p, d in (absent or []):
        if p not in c: print(f'OK   ABSENT: {d}')
        else: errors.append(d); print(f'FAIL STILL PRESENT: {d}')

# products.py: semi_finished now allowed
ck('backend/app/interfaces/api/v1/routes/products.py', [
    ('semi_finished', 'semi_finished allowed in variant link'),
    ('_LINKABLE_TYPES', 'uses set for linkable types'),
], [
    ('!= "finished"', 'old finished-only restriction removed'),
])

# supply_chain.py: explicit FK first
ck('backend/app/interfaces/api/v1/routes/supply_chain.py', [
    ('Strategy 0: explicit FK', 'explicit FK strategy present'),
    ('Strategy 1: code match', 'code match fallback present'),
    ('link_type', 'link_type returned to frontend'),
    ('material_id == material_id', 'explicit FK query'),
])

# supply-chain.service.ts: link_type typed
ck('frontend/src/services/supply-chain.service.ts', [
    ('link_type', 'link_type in BOM type'),
    ('getBOMLines', 'getBOMLines method added'),
])

# SubcontractListPage: component preview
ck('frontend/src/modules/procurement/pages/SubcontractListPage.tsx', [
    ('previewLines', 'component preview state'),
    ('loadBomPreview', 'preview loading function'),
    ('Components to be issued', 'preview section label'),
    ('code_match', 'code_match guidance message'),
    ('No active BOM found', 'no-bom guidance'),
])

import sys
if errors:
    print(f'\n{len(errors)} check(s) failed')
    sys.exit(1)
else:
    print('\n✓ All checks passed')
    sys.exit(0)
