print('Verifying Semi-Finished Material Entry UX implementation...\n')

# Check MaterialListPage has all three buttons
ml_page = open('frontend/src/modules/inventory/pages/MaterialListPage.tsx', encoding='utf-8').read()
checks = [
    ('Add Raw Material' in ml_page, 'Raw Material button present'),
    ('Add Semi-Finished' in ml_page, 'Semi-Finished button present'),
    ('Add Finished Good' in ml_page, 'Finished Good button present'),
    ('semi_finished' in ml_page, 'semi_finished preset used'),
    ('Upload Raw Materials' in ml_page, 'Upload button unchanged'),
]

for ok, desc in checks:
    print(f"{'✓' if ok else '✗'} {desc}")

# Check MaterialFormDrawer accepts semi_finished
drawer = open('frontend/src/modules/inventory/components/MaterialFormDrawer.tsx', encoding='utf-8').read()
drawer_checks = [
    ('semi_finished' in drawer and 'presetType?' in drawer, 'presetType type includes semi_finished'),
    ('New Semi-Finished Material' in drawer, 'Semi-Finished title present'),
    ('intermediate products' in drawer, 'Semi-Finished description present'),
]

print()
for ok, desc in drawer_checks:
    print(f"{'✓' if ok else '✗'} {desc}")

all_ok = all(ok for ok, _ in checks + drawer_checks)
print(f"\n{'✅ All checks passed' if all_ok else '❌ Some checks failed'}")
import sys; sys.exit(0 if all_ok else 1)
