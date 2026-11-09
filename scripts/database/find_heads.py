"""Find all alembic file heads."""
import re, os, glob

files = glob.glob('alembic/versions/*.py')
revisions = {}
for f in files:
    with open(f, encoding='utf-8') as fh:
        content = fh.read()
    rev_m = re.search(r"revision\s*(?::\s*str)?\s*=\s*[\"'](.*?)[\"']", content)
    down_m = re.search(r"down_revision\s*=\s*([^\n]+)", content)
    if rev_m and down_m:
        rid = rev_m.group(1).strip()
        d = down_m.group(1).strip()
        revisions[rid] = {'file': os.path.basename(f), 'down': d}

all_revs = set(revisions.keys())
pointed_to = set()
for r, info in revisions.items():
    d = info['down']
    # Extract all quoted strings from down_revision value
    for x in re.findall(r"[\"']([\w]+)[\"']", d):
        pointed_to.add(x)

heads = all_revs - pointed_to
print("Heads (not pointed to by anything):", sorted(heads))
print()
print("DB has:", ['add_default_price_list_to_clients','add_notification_retention',
                  'gap4_so_status_enum_and_constraint','normalize_material_type_001',
                  'p1_op_wf_states','p2_inv_reservation'])
