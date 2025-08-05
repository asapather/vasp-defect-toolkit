#!/usr/bin/env python3

from pathlib import Path
from pymatgen.io.vasp.inputs import Incar
import math

# === Settings ===
reference_folder = "z_input/reference_incar"
max_columns_per_table = 5
ignore_keys = set()  # Include all tags
dash = "—"

# === Gather folders ===
root = Path.cwd()
folders = [f for f in root.iterdir() if f.is_dir() and (f / "INCAR").exists()]
folders.sort()
folder_names = [f.name for f in folders]

# === Load reference INCAR ===
ref_incar_path = root / reference_folder / "INCAR"
if not ref_incar_path.exists():
    print(f"❌ Reference INCAR not found at {ref_incar_path}")
    exit(1)
ref_incar = Incar.from_file(ref_incar_path)

# === Compare INCARs ===
all_keys = set()
diffs = {}

for folder in folders:
    incar = Incar.from_file(folder / "INCAR")
    diff = {}
    for key in set(ref_incar.keys()).union(set(incar.keys())):
        if key in ignore_keys:
            continue
        val_ref = ref_incar.get(key, None)
        val_cur = incar.get(key, None)
        if val_ref != val_cur:
            diff[key] = val_cur
            all_keys.add(key)
    diffs[folder.name] = diff

# === Format and print table chunks ===
all_keys = sorted(all_keys)
n_chunks = math.ceil(len(all_keys) / max_columns_per_table)

# Determine folder column width dynamically (with padding)
folder_col_width = max(len(name) for name in folder_names) + 4

# Default widths for known long fields
default_widths = {
    "LDAUL": 20,
    "LDAUU": 20,
    "LDAUJ": 20,
    "SYSTEM": 10,
    "MAGMOM" : 20
}

for i in range(n_chunks):
    chunk_keys = all_keys[i * max_columns_per_table : (i + 1) * max_columns_per_table]
    headers = ["FOLDER"] + chunk_keys
    widths = [folder_col_width] + [
        max(len(k), default_widths.get(k.upper(), 8)) for k in chunk_keys
    ]

    # Header
    print("\n" + "  ".join(h.ljust(w) for h, w in zip(headers, widths)))
    print("-" * (sum(widths) + 2 * len(widths)))

    # Rows
    for name in folder_names:
        row = [name.ljust(widths[0])]
        for key, w in zip(chunk_keys, widths[1:]):
            val = diffs.get(name, {}).get(key, dash)
            row.append(str(val).ljust(w))
        print("  ".join(row))
