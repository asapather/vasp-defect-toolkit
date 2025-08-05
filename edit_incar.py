#!/usr/bin/env python3
"""
edit_incar.py — Batch-edit INCAR files in all subfolders.

Usage:
  ./edit_incar.py --set ENCUT=520 --set ISYM=0
Options:
  --dry-run      Show planned changes but don’t write files
"""

import sys
from pathlib import Path
from pymatgen.io.vasp.inputs import Incar

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Edit INCAR files in subfolders.")
    parser.add_argument('--set', action='append', help='Set INCAR key=value pairs', metavar='KEY=VALUE')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    args = parser.parse_args()

    set_dict = {}
    if args.set:
        for pair in args.set:
            if '=' not in pair:
                parser.error(f"Invalid --set argument: {pair}")
            key, val = pair.split('=', 1)
            try:
                val = eval(val)  # Convert to int/float/bool if possible
            except:
                pass
            set_dict[key.upper()] = val
    return set_dict, args.dry_run

def edit_incar_in_folder(folder, set_dict, dry_run):
    if folder.name.startswith("z"):
        return f"{folder.name:<25} ⏭️ skipped (starts with 'z')"

    incar_path = folder / "INCAR"
    if not incar_path.exists():
        return f"{folder.name:<25} ✗ no INCAR"

    try:
        incar = Incar.from_file(incar_path)
    except Exception as e:
        return f"{folder.name:<25} ✗ failed to parse INCAR: {e}"

    changes = []
    for key, value in set_dict.items():
        old_val = incar.get(key, None)
        incar[key] = value
        changes.append(f"{key}={old_val} → {value}")

    if not dry_run:
        incar.write_file(incar_path)

    change_str = ", ".join(changes) if changes else "✓ no change"
    return f"{folder.name:<25} ✓ {change_str}"

def main():
    set_dict, dry_run = parse_args()

    base = Path(".")
    folders = [f for f in base.iterdir() if f.is_dir()]
    results = []

    for folder in sorted(folders):
        result = edit_incar_in_folder(folder, set_dict, dry_run)
        results.append(result)

    print("\nEditing INCAR files:\n")
    for line in results:
        print(line)
    if dry_run:
        print("\n(DRY RUN: no files written)")

if __name__ == "__main__":
    main()
