# Debug Archive

One-off debugging scripts, diagnostic queries, and testing utilities from development. Archived for reference.

## Purpose

This directory contains scripts created during debugging specific issues. They may be useful for:
- Understanding how issues were debugged
- Reproducing similar issues in the future
- Reference for diagnostic approaches
- Historical context of problems encountered

## Organization

### Temporary Debugging (tmp_*)
Quick scripts created during troubleshooting:
- `tmp_*.py` — Temporary Python debugging scripts
- `tmp_*.json` — Sample request/response payloads
- `tmp_*.txt` — Debug output files

### Database Checks (check_*)
Ad-hoc database validation scripts:
- `check_*.py` — Python-based database checks
- `CHECK_*.sql` — SQL diagnostic queries

### Issue-Specific Debugging (debug_*)
Scripts targeting specific issues:
- `debug_complete_wo.py` — Work order completion debugging
- `debug_subcontract_*.py` — Subcontracting issue debugging
- `debug_operations.py` — Manufacturing operation debugging
- `DEBUG_*.sql` — SQL for specific issues

### Diagnostic Queries
- `DIAGNOSTIC_QUERIES.sql` — Collection of diagnostic SQL
- `VERIFY_*.sql` — Verification and validation queries
- `FIND_*.sql` — Data discovery queries
- `MANUAL_*.sql` — Manual schema fixes

### Documentation
- `DEBUG_401_UNAUTHORIZED.md` — Debugging unauthorized errors
- `DEPLOYMENT_CHECKLIST.md` — Pre-deployment checks

## When to Use

**These scripts are for reference only.** Use them when:
1. Debugging a similar issue
2. Understanding the problem-solving approach used
3. Root cause analysis of past incidents
4. Reference for creating new diagnostic scripts

## Creating New Debug Scripts

**Do not add to this archive.** Instead:
1. Create new debugging scripts in your working directory
2. Name them with `debug_` or `tmp_` prefix
3. Move to this archive only when complete and for reference
4. Document what issue was debugged and the solution

## Important Notes

- These scripts are **not guaranteed to work** in current state
- Database schemas may have changed since creation
- Always verify scripts in non-production environments first
- Use current debugging approaches when possible
- Refer to main application patterns for new scripts

---

**Last Updated:** November 9, 2026
