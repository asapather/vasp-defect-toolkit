#!/usr/bin/env python3
"""
check_inputs.py — Summarize VASP input folders with NELECT, ΔQ, atom count, composition, job status, and missing files.
"""

import os
import sys
import warnings
from pathlib import Path
from pymatgen.io.vasp.inputs import Incar, Poscar, Potcar

warnings.filterwarnings("ignore", category=UserWarning, module="pymatgen.io.vasp.inputs")

REQUIRED_FILES = ["INCAR", "POSCAR", "KPOINTS", "POTCAR", "job.justhpc"]

def detect_job_status(folder):
    outcar = folder / "OUTCAR"
    if not outcar.exists():
        return "not started"
    try:
        with open(outcar, "r", errors="ignore") as f:
            content = f.read()
            if "Voluntary context switches" in content:
                return "finished"
            elif "General timing and accounting" in content:
                return "failed"
            else:
                return "running"
    except:
        return "unreadable"

def get_total_charge(nelect, poscar, potcar):
    if nelect is None or isinstance(nelect, str):
        return "—"
    try:
        poscar_symbols = poscar.site_symbols
        atom_counts = poscar.natoms

        # Normalize POTCAR symbols (e.g. La_GW → La)
        potcar_entries = [(p.symbol.split("_")[0], p.zval) for p in potcar]
        zval_map = dict(potcar_entries)

        total = 0
        for symbol, count in zip(poscar_symbols, atom_counts):
            if symbol not in zval_map:
                return "err"
            total += zval_map[symbol] * count

        delta_q = total - nelect
        if abs(delta_q) < 1e-2:
            delta_q = 0.0
        return f"{delta_q:+.2f}"
    except Exception:
        return "err"

def check_folder(folder):
    files_present = [f.name for f in folder.iterdir() if f.is_file()]
    missing = [f for f in REQUIRED_FILES if f not in files_present]

    if len(missing) >= 3:
        return None  # Skip folders with too many missing files

    incar = None
    poscar = None
    potcar = None
    nelect = None

    incar_path = folder / "INCAR"
    poscar_path = folder / "POSCAR"
    potcar_path = folder / "POTCAR"

    if incar_path.exists():
        try:
            incar = Incar.from_file(incar_path)
            nelect = incar.get("NELECT", "—")
        except:
            nelect = "err"

    atoms = "✗"
    formula = "✗"
    if poscar_path.exists():
        try:
            poscar = Poscar.from_file(poscar_path)
            atoms = len(poscar.structure)
            composition = poscar.structure.composition.get_el_amt_dict()
            formula = " ".join(f"{el}{int(n)}" for el, n in composition.items())
        except:
            atoms = formula = "err"

    if potcar_path.exists():
        try:
            potcar = Potcar.from_file(potcar_path)
        except:
            potcar = None

    charge = "—"
    if isinstance(nelect, (int, float)) and poscar and potcar:
        charge = get_total_charge(nelect, poscar, potcar)

    status = detect_job_status(folder)

    return {
        "Folder": folder.name,
        "NELECT": nelect,
        "Charge": charge,
        "Atoms": atoms,
        "Composition": formula,
        "Status": status,
        "Missing": ", ".join(missing) if missing else "✓"
    }

def main():
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    folders = [f for f in base.iterdir() if f.is_dir()]
    results = []

    for folder in sorted(folders):
        info = check_folder(folder)
        if info:
            results.append(info)

    print("\nSummary of VASP input folders:\n")
    print("{:<25} {:<14} {:<6} {:<30} {:<15} {}".format(
        "FOLDER", "NELECT (ΔQ)", "Atoms", "Composition", "JOB STATUS", "FILES MISSING"
    ))
    print("-" * 120)
    for r in results:
        nelect_str = f"{r['NELECT']} ({r['Charge']})" if r["NELECT"] != "—" else "—"
        print("{:<25} {:<14} {:<6} {:<30} {:<15} {}".format(
            r["Folder"], nelect_str, str(r["Atoms"]), str(r["Composition"]),
            r["Status"], r["Missing"]
        ))

if __name__ == "__main__":
    main()
