#!/usr/bin/env python3

import json
import shutil
import argparse
from pathlib import Path
from pymatgen.core import Element, Structure
from pymatgen.io.vasp import Poscar, Incar, Potcar
from phonopy import Phonopy
from phonopy.structure.atoms import PhonopyAtoms
import warnings
import numpy as np

# === Suppress SHA256 warnings ===
original_warn = warnings.warn
def custom_warn(*args, **kwargs):
    msg = str(args[0]) if args else ""
    if "SHA256" not in msg:
        original_warn(*args, **kwargs)
warnings.warn = custom_warn

# === CLI ===
parser = argparse.ArgumentParser(description="Build phonopy supercell and apply defect modifications")
parser.add_argument('--supercell', nargs=3, type=int, metavar=('X', 'Y', 'Z'), default=[2, 2, 4],
                    help="Supercell size (default: 2 2 4)")
args = parser.parse_args()
supercell_size = tuple(args.supercell)

# === Paths ===
base_dir = Path.cwd()
unitcell_path = base_dir / "z_unit_cell" / "CONTCAR"
defect_json = base_dir / "z_input" / "defect_modifications.json"
input_root = base_dir / "z_input"

# === Load files ===
try:
    unitcell_structure = Structure.from_file(unitcell_path)
except Exception as e:
    print(f"❌ Could not read {unitcell_path}: {e}")
    exit(1)

try:
    with open(defect_json) as f:
        defect_data = json.load(f)
except Exception as e:
    print(f"❌ Could not read JSON from {defect_json}: {e}")
    exit(1)

# === Helpers ===
canonical_order = ["La", "Y", "Mo", "Pb", "W", "O"]

def structure_to_phonopy(structure):
    return PhonopyAtoms(symbols=[site.specie.symbol for site in structure],
                        cell=structure.lattice.matrix,
                        scaled_positions=[site.frac_coords for site in structure])

def phonopy_to_structure(phonopy_atoms):
    from pymatgen.core import Lattice
    lattice = Lattice(phonopy_atoms.cell)
    return Structure(lattice, phonopy_atoms.symbols, phonopy_atoms.scaled_positions)

def build_supercell_with_phonopy(structure, supercell_matrix):
    unitcell = structure_to_phonopy(structure)
    phonon = Phonopy(unitcell, supercell_matrix)
    sc = phonon.get_supercell()
    return phonopy_to_structure(sc)

def find_empty_sites(structure, min_distance=1.5):
    """Find fractional coords not too close to existing atoms."""
    coords = np.array([s.frac_coords for s in structure])
    candidates = []
    grid_size = 10
    for x in np.linspace(0, 1, grid_size, endpoint=False):
        for y in np.linspace(0, 1, grid_size, endpoint=False):
            for z in np.linspace(0, 1, grid_size, endpoint=False):
                trial = np.array([x, y, z])
                dists = structure.lattice.get_all_distances(trial, coords)
                if np.all(dists > min_distance):
                    candidates.append(trial)
    return candidates

def apply_defect(structure: Structure, delta: dict) -> Structure:
    mod_structure = structure.copy()
    removed_coords = []

    for elem, change in delta.items():
        if change < 0:
            indices = [i for i, site in enumerate(mod_structure) if site.specie.symbol == elem]
            if len(indices) < abs(change):
                raise ValueError(f"Not enough {elem} atoms to remove")
            for i in sorted(indices[:abs(change)], reverse=True):
                removed_coords.append(mod_structure[i].frac_coords)
                mod_structure.remove_sites([i])

    for elem, change in delta.items():
        if change > 0:
            added = 0

            # Use coordinates of removed atoms first
            for coord in removed_coords:
                mod_structure.append(species=Element(elem), coords=coord, coords_are_cartesian=False)
                added += 1
                if added == change:
                    break

            # Then find empty space
            if added < change:
                empty_sites = find_empty_sites(mod_structure)
                for coord in empty_sites:
                    mod_structure.append(species=Element(elem), coords=coord, coords_are_cartesian=False)
                    added += 1
                    if added == change:
                        break

            if added < change:
                raise ValueError(f"Could only add {added} of {change} requested {elem} atoms (not enough free space)")

    return mod_structure

def get_valence_electrons(structure, potcar_path):
    potcar = Potcar.from_file(potcar_path)
    zval = {p.element: p.zval for p in potcar}
    total = 0
    for site in structure:
        sym = site.specie.symbol
        if sym not in zval:
            raise ValueError(f"Element {sym} not in POTCAR")
        total += zval[sym]
    return total

def get_template_folder(delta):
    elements_added = [k for k, v in delta.items() if v > 0]
    if "La" in elements_added:
        return "La_Pb_W_O"
    elif "Y" in elements_added:
        return "Y_Pb_W_O"
    elif "Mo" in elements_added:
        return "Mo_Pb_W_O"
    else:
        return "Pb_W_O"

# === Main loop ===
for name, spec in defect_data.items():
    if name.startswith("z"):
        print(f"⏭️  Skipping {name}")
        continue

    try:
        folder = base_dir / name
        folder.mkdir(exist_ok=True)

        structure = build_supercell_with_phonopy(unitcell_structure, supercell_size)
        structure = apply_defect(structure, spec.get("delta", {}))
        structure = structure.get_sorted_structure(key=lambda s: canonical_order.index(s.specie.symbol) if s.specie.symbol in canonical_order else 999)

        Poscar(structure).write_file(folder / "POSCAR")

        template_name = get_template_folder(spec["delta"])
        template = input_root / template_name

        if not (template / "POTCAR").exists():
            raise FileNotFoundError(f"Missing POTCAR in {template}")
        if not (input_root / "KPOINTS").exists():
            raise FileNotFoundError("Missing shared KPOINTS in z_input")

        shutil.copy(template / "INCAR", folder / "INCAR")
        shutil.copy(template / "POTCAR", folder / "POTCAR")
        shutil.copy(input_root / "KPOINTS", folder / "KPOINTS")

        incar = Incar.from_file(folder / "INCAR")
        nelect = round(get_valence_electrons(structure, folder / "POTCAR")) + spec.get("charge", 0)
        incar["NELECT"] = nelect
        incar.write_file(folder / "INCAR")

        job_lines = (input_root / "job.justhpc").read_text().splitlines()
        with open(folder / "job.justhpc", "w") as f:
            for line in job_lines:
                if line.strip().startswith("#SBATCH --job-name="):
                    f.write(f"#SBATCH --job-name={name}\n")
                else:
                    f.write(line + "\n")

        print(f"✅ {name}: done (NELECT = {nelect})")

    except Exception as e:
        print(f"❌ {name}: {e}")
