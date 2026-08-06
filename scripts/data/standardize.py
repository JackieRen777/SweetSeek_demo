"""SMILES standardization utilities.

Day 1 only defines the functions; adapters call them on Day 2 when we
generate canonical SMILES + InChIKey for the merged master table.

Pipeline (`standardize`):
    raw SMILES
        -> RDKit Mol
        -> remove standard salt fragments (SaltRemover)
        -> if multi-component remains, keep largest fragment
        -> neutralize charges (Uncharger)
        -> canonical tautomer (TautomerEnumerator.Canonicalize)
        -> canonical SMILES + InChI + InChIKey

Returns a dict; on failure, returns {"valid": False, "reason": str}.
"""

from __future__ import annotations

from typing import Optional

from rdkit import Chem, RDLogger
from rdkit.Chem import AllChem, Descriptors
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.SaltRemover import SaltRemover

# Suppress noisy RDKit warnings on bad SMILES; we surface them via .get('reason')
RDLogger.DisableLog("rdApp.*")

_SALT_REMOVER = SaltRemover()
_UNCHARGER = rdMolStandardize.Uncharger()
_TAUTOMER = rdMolStandardize.TautomerEnumerator()

ALLOWED_ATOMS = {"H", "C", "N", "O", "P", "S", "F", "Cl", "Br", "I"}


def parse_smiles(smiles: str) -> Optional[Chem.Mol]:
    """Parse SMILES to Mol; return None on failure or empty input."""
    if not smiles or not isinstance(smiles, str):
        return None
    return Chem.MolFromSmiles(smiles.strip())


def remove_salts(mol: Chem.Mol) -> Optional[Chem.Mol]:
    """Strip common counter-ions; if multi-component remains, keep largest."""
    stripped = _SALT_REMOVER.StripMol(mol, dontRemoveEverything=True)
    if stripped is None or stripped.GetNumAtoms() == 0:
        return None
    frags = Chem.GetMolFrags(stripped, asMols=True, sanitizeFrags=False)
    if len(frags) > 1:
        stripped = max(frags, key=lambda m: m.GetNumHeavyAtoms())
    return stripped


def neutralize_charges(mol: Chem.Mol) -> Optional[Chem.Mol]:
    """Neutralize formal charges where chemically sensible."""
    try:
        return _UNCHARGER.uncharge(mol)
    except Exception:
        return None


def canonical_tautomer(mol: Chem.Mol) -> Optional[Chem.Mol]:
    """Pick the canonical tautomer for cross-source consistency."""
    try:
        return _TAUTOMER.Canonicalize(mol)
    except Exception:
        return mol  # fall back to input rather than dropping the row


def has_only_allowed_atoms(mol: Chem.Mol) -> bool:
    return all(atom.GetSymbol() in ALLOWED_ATOMS for atom in mol.GetAtoms())


def to_canonical_smiles(mol: Chem.Mol) -> str:
    return Chem.MolToSmiles(mol, canonical=True)


def to_inchi_key(mol: Chem.Mol) -> str:
    return Chem.MolToInchiKey(mol)


def to_inchi(mol: Chem.Mol) -> str:
    return Chem.MolToInchi(mol)


def standardize(smiles_raw: str) -> dict:
    """Full pipeline. Returns dict with canonical fields, or failure reason.

    Success keys: valid=True, smiles_canonical, inchi, inchi_key, mw,
                  n_heavy_atoms.
    Failure keys: valid=False, reason.
    """
    mol = parse_smiles(smiles_raw)
    if mol is None:
        return {"valid": False, "reason": "parse_failed"}

    mol = remove_salts(mol)
    if mol is None:
        return {"valid": False, "reason": "all_atoms_stripped"}

    mol = neutralize_charges(mol)
    if mol is None:
        return {"valid": False, "reason": "neutralize_failed"}

    mol = canonical_tautomer(mol)
    if mol is None:
        return {"valid": False, "reason": "tautomer_failed"}

    if not has_only_allowed_atoms(mol):
        bad = sorted({a.GetSymbol() for a in mol.GetAtoms()
                      if a.GetSymbol() not in ALLOWED_ATOMS})
        return {"valid": False, "reason": f"disallowed_atoms:{','.join(bad)}"}

    try:
        Chem.SanitizeMol(mol)
    except Exception as e:
        return {"valid": False, "reason": f"sanitize_failed:{type(e).__name__}"}

    inchi_key = to_inchi_key(mol)
    if not inchi_key:
        return {"valid": False, "reason": "inchikey_failed"}

    return {
        "valid": True,
        "smiles_canonical": to_canonical_smiles(mol),
        "inchi": to_inchi(mol),
        "inchi_key": inchi_key,
        "mw": float(Descriptors.MolWt(mol)),
        "n_heavy_atoms": int(mol.GetNumHeavyAtoms()),
    }


if __name__ == "__main__":
    # Smoke test: aspirin sodium salt, sucrose, broken SMILES
    cases = [
        ("aspirin sodium", "CC(=O)Oc1ccccc1C(=O)[O-].[Na+]"),
        ("sucrose", "OC[C@H]1O[C@@](CO)(O[C@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)[C@@H](O)[C@@H]1O"),
        ("broken", "this_is_not_smiles"),
        ("empty", ""),
    ]
    for name, smi in cases:
        out = standardize(smi)
        print(f"[{name}]", out if not out.get("valid") else
              f"OK  ik={out['inchi_key']}  mw={out['mw']:.1f}  smi={out['smiles_canonical'][:60]}")
