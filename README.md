# VASP Defect Workflow Toolkit

This repository contains a collection of command-line Python tools located in `~/bin/vasptools/`, developed to automate and streamline high-throughput defect calculations using VASP.

## 🔧 Script Overview

All scripts are stored in:
```
~/bin/vasptools/
```

You execute them from the directory where your calculations are located. Example working directory structure:

```
your_calculation_folder/
├── la/
├── mo/
├── o_plus_2/
├── z_no_defect/               # Contains reference CONTCAR
├── z_defect_log/
│   └── defect_modifications.json
└── [other defect folders...]
```

### 📜 Included Scripts

#### `apply_defects.py`
- Copies `z_no_defect/CONTCAR` into each defect folder
- Applies atomic substitutions or removals based on `defect_modifications.json`
- Adjusts `NELECT` in each folder’s INCAR based on POTCAR and charge

#### `edit_incar.py`
- Batch edits specified INCAR tags across all subfolders
- Supports value setting, deletion, and string/numeric replacement

#### `diff_incar.py`
- Compares all INCAR files against `z_no_defect/INCAR`
- Shows changes grouped by unique differences
- Ignores globally identical modifications and the `SYSTEM` tag

#### `check_inputs.py`
- Validates that essential VASP input files exist in each folder
- Can optionally check for syntax completeness or warnings

---

## 📁 Input Files

- `z_defect_log/defect_modifications.json`: Defines how each folder should be modified structurally and electronically.

Example format:
```json
{
  "la": {
    "delta": {"Pb": -1, "La": 1},
    "charge": 0
  },
  ...
}
```

---

## 🧩 Planned Features

This toolkit is modular and will be expanded to include:
- Automated folder creation from templates
- POTCAR auto-compilation per folder
- Band structure and DOS plotting
- Job submission helpers (e.g., SLURM templates)

---

## ✅ Usage

In your working folder, run:
```bash
apply_defects.py
diff_incar.py
edit_incar.py KPAR=2
check_inputs.py
```

Ensure your environment includes `pymatgen`, `numpy`, and Python ≥3.8.
