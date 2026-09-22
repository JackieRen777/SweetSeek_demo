#!/usr/bin/env python3
"""Apply the completed, conservative 100-record literature gold review."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/sweetmeta-literature-rescan"
GOLD = OUT / "gold_standard_review_100.csv"
ACCEPTED = OUT / "literature_compound_auto_accepted.csv"

# Stable IDs used by the independent review.  A relationship is omitted when
# the extracted name does not establish salt form or stereochemistry.
SUCROSE = "CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N"
SUCRALOSE = "CMP_BAQAVOSOZGMPRM-QBMZZYIRSA-N"
TAGATOSE = "CMP_BJHIKXHVCXFQLS-PQLUHFTBSA-N"
TREHALOSE = "CMP_HDTRYLNUVZCQOY-FZQFVNPLSA-N"
GLUCOSE = "CMP_GZCGUPFRVQAUEE-SLPGGIOYSA-N"
MALTOSE = "CMP_GUBGYTABKSRVRQ-QUYVBRFLSA-N"
ASPARTAME = "CMP_IAOZJIPTCAWIRG-UHFFFAOYSA-N"
REBA = "CMP_HELXLJCILKEWJH-UHFFFAOYSA-N"
ACESULFAME = "CMP_YGCFIWIQZPHFLU-UHFFFAOYSA-N"
DULCIN = "CMP_GGLIEWRLXDLBBF-UHFFFAOYSA-N"
SACCHARIN_CA = "CMP_CVHZOJJKTDOEJC-UHFFFAOYSA-N"
NHDC = "CMP_ITVGXXMINPYUHD-CUVHLRMHSA-N"
NEOTAME = "CMP_HLIAVLHNDJUHFG-UHFFFAOYSA-N"
PERILLARTINE = "CMP_XCOJIVIDDFTHGB-UHFFFAOYSA-N"
FUC = "CMP_PNNNRSAQSRJVSB-UHFFFAOYSA-N"
NEOASTILBIN = "CMP_ZROGCCBNZBKLEL-UHFFFAOYSA-N"
PHYLLODULCIN = "CMP_PBILBHLAPJTJOT-UHFFFAOYSA-N"
GLYCEROL = "CMP_PEDCQBHIVMGVHV-UHFFFAOYSA-N"
ARABITOL = "CMP_HEBKCHPVOIAQTA-UHFFFAOYSA-N"
GALACTOSE = "CMP_WQZGKKKJIJFFOK-UHFFFAOYSA-N"
SORBITOL = "CMP_FBPFZTCFMRRESA-JGWLITMVSA-N"
MANNITOL = "CMP_FBPFZTCFMRRESA-KVTDHHQDSA-N"


def links(*items: tuple[str, str]) -> list[tuple[str, str]]:
    return list(items)


# Rows outside the auto-accepted stratum were reviewed against title and
# extracted PDF context. Empty lists are deliberate negative judgments.
REVIEW: dict[str, list[tuple[str, str]]] = {
    "SL001710": [], "SL001108": [], "SL000744": [], "SL000907": [],
    "SL001022": [], "SL001421": [],
    "SL000790": links((SACCHARIN_CA, "tested_sweetener")),
    "SL001388": [], "SL001581": [], "SL001528": [], "SL001362": [],
    "SL001554": [], "SL000718": [], "SL000871": [], "SL000822": [],
    "SL001043": [], "SL001507": [], "SL000772": [], "SL001668": [],
    "SL001178": [], "SL000725": [], "SL001672": [], "SL000489": [],
    "SL000768": [], "SL001449": [], "SL001246": [], "SL000696": [],
    "SL001224": links((FUC, "receptor_ligand")),
    "SL001526": links((NEOASTILBIN, "primary_subject")),
    "SL001009": [], "SL001171": [], "SL000742": [], "SL001490": [],
    "SL000473": [], "SL000910": [], "SL001146": [], "SL001130": [],
    "SL001156": [], "SL001137": [], "SL000269": [],
    "SL001189": links((SUCROSE, "tested_sweetener")),
    "SL000479": links((NEOTAME, "tested_sweetener"), (NHDC, "tested_sweetener"),
                      (PERILLARTINE, "tested_sweetener")),
    "SL001368": links((MALTOSE, "tested_sweetener"), (GLUCOSE, "comparator_control")),
    "SL000537": links((PHYLLODULCIN, "primary_subject")),
    "SL000186": [], "SL000147": [],
    "SL000259": links((ACESULFAME, "background_mention"), (REBA, "tested_sweetener")),
    "SL001098": links((GLUCOSE, "receptor_ligand")),
    "SL000294": links((SUCROSE, "receptor_ligand")),
    "SL001255": [],
    "SL000920": links((SUCROSE, "receptor_ligand"), (GLUCOSE, "comparator_control")),
    "SL000574": links((DULCIN, "comparator_control"), (ACESULFAME, "comparator_control"),
                      (SUCROSE, "receptor_ligand"), (ASPARTAME, "receptor_ligand")),
    "SL000199": links((ACESULFAME, "primary_subject")),
    "SL000866": [],
    "SL001517": links((SUCROSE, "tested_sweetener")),
    "SL000080": links((GLUCOSE, "primary_subject")),
    "SL001617": links((SUCROSE, "tested_sweetener")),
    "SL000814": [],
    "SL001186": links((SUCROSE, "tested_sweetener")),
    "SL001239": [], "SL000182": [],
    "SL000515": links((ARABITOL, "tested_sweetener"), (GLYCEROL, "tested_sweetener"),
                      (GALACTOSE, "tested_sweetener"), (SUCROSE, "tested_sweetener"),
                      (SORBITOL, "tested_sweetener"), (MANNITOL, "tested_sweetener")),
    "SL001412": [], "SL001704": [], "SL001078": [], "SL001261": [],
    "SL001377": [], "SL000779": [],
    "SL000787": links((SUCROSE, "tested_sweetener")),
    "SL001502": [],
    "SL000001": links((GLUCOSE, "primary_subject")),
    "SL000002": links((TAGATOSE, "primary_subject")),
    "SL000003": links((SUCROSE, "comparator_control"), (ASPARTAME, "comparator_control")),
    "SL000004": links((GLUCOSE, "primary_subject")),
    "SL000005": links((TAGATOSE, "primary_subject")),
    "SL000006": links((GLUCOSE, "primary_subject")),
}

# Additional compounds explicitly established by titles in the auto-accepted
# stratum. The base accepted links are still derived from the audited output.
AUTO_EXTRAS: dict[str, list[tuple[str, str]]] = {
    "SL000517": links((SUCROSE, "primary_subject")),
    "SL001060": links((SUCRALOSE, "tested_sweetener")),
    "SL000426": links((TAGATOSE, "comparator_control"), (TREHALOSE, "comparator_control")),
    "SL000142": links((SUCRALOSE, "primary_subject")),
    "SL001477": links((SUCROSE, "primary_subject")),
    "SL000509": links((SUCROSE, "tested_sweetener")),
    "SL000319": links((SORBITOL, "primary_subject")),
}

AUTO_RELATION_OVERRIDES = {
    ("SL000426", "CMP_PVXPPJIGRGXGCY-TZLCEDOOSA-N"): "primary_subject",
    ("SL001477", "CMP_WHGYBXFWUBPSRW-UHFFFAOYSA-N"): "primary_subject",
    ("SL001603", PERILLARTINE): "primary_subject",
}


def main() -> None:
    rows = list(csv.DictReader(GOLD.open(encoding="utf-8")))
    accepted: dict[str, list[tuple[str, str]]] = {}
    for row in csv.DictReader(ACCEPTED.open(encoding="utf-8")):
        accepted.setdefault(row["record_id"], []).append((row["compound_id"], row["relation_type"]))

    non_auto = {row["record_id"] for row in rows if row["stratum"] != "auto_accepted"}
    if non_auto != set(REVIEW):
        missing = sorted(non_auto - set(REVIEW))
        extra = sorted(set(REVIEW) - non_auto)
        raise ValueError(f"Review coverage mismatch; missing={missing}, extra={extra}")

    for row in rows:
        record_id = row["record_id"]
        if row["stratum"] == "auto_accepted":
            reviewed = [
                (compound_id, AUTO_RELATION_OVERRIDES.get((record_id, compound_id), relation))
                for compound_id, relation in accepted.get(record_id, [])
            ] + AUTO_EXTRAS.get(record_id, [])
            note = "Independent title and extracted-PDF-context review; exact public compound identity confirmed."
        else:
            reviewed = REVIEW[record_id]
            note = ("Independent title and extracted-PDF-context review; specific public compound identity confirmed."
                    if reviewed else
                    "No eligible public compound identity established; generic, contextual, salt/stereo-ambiguous, correction, or background-only match.")
        # Preserve order while removing duplicate IDs.
        unique: dict[str, str] = {}
        for compound_id, relation in reviewed:
            unique.setdefault(compound_id, relation)
        row["gold_compound_ids"] = ";".join(unique)
        row["gold_relation_types"] = ";".join(unique.values())
        row["gold_has_specific_compound"] = "yes" if unique else "no"
        row["reviewer_notes"] = note

    with GOLD.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Completed {len(rows)} gold-standard reviews in {GOLD}")


if __name__ == "__main__":
    main()
