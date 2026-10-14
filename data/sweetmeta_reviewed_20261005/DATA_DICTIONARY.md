# SweetMeta v1.0.7 reviewed data dictionary

Reviewed snapshot date: 2026-10-05. Public compound denominator: 1,296.

## Identity and classification

- `compound_id`: stable SweetMeta compound identifier and cross-table join key.
- `preferred_name`, `parent_inchikey`, `parent_isomeric_smiles`, `parent_canonical_smiles`, `molecular_formula`, `molecular_weight`: reviewed parent-normalized identity fields.
- `sweetclass_level1`: one of seven broad structural sweetener families.
- `sweetclass_level2`: one of 28 structural subfamilies.
- `analysis_chemical_class` and `classyfire_*`: retained structural taxonomy. These fields do not imply sweetness mechanism, safety, regulation, or evidence quality.

## Evidence systems

- `evidence_short` (`E1`, `E2`, `E3`): provenance grade for the sweetness claim. E1 is primary entity-specific evidence, E2 is traceable secondary evidence, and E3 is database-curated evidence.
- `evidence_tier`: full provenance-grade label.
- `evidence_lineage_status`: reason or route used to assign the provenance grade.
- `release_evidence_readiness_tier` (`R1`-`R4`): operational release readiness from the retained SweetMeta release database. It is separate from E1-E3 and must not be relabeled as provenance grade.

## Physicochemical properties

Values were calculated from parent-normalized structures with RDKit and reviewed with the 2026-10-05 package.

- `molecular_weight`: molecular weight in Da.
- `clogp`: RDKit Crippen cLogP.
- `tpsa`: topological polar surface area in square angstroms.
- `rotatable_bonds`, `hba`, `hbd`, `heavy_atom_count`: integer structure counts.
- `bertz_complexity`, `log10_bertz_complexity`, `fraction_csp3`: calculated structural descriptors.

PubChem properties remain external comparison values and do not overwrite reviewed values.

## Projection coordinates

- `umap_coordinates_1296.csv`: reviewed ECFP4 UMAP coordinates using Jaccard distance, 20 neighbors, minimum distance 0.60, and seed 20260825. Source columns are named `PC1` and `PC2` for historical reasons; the website presents them as UMAP 1 and UMAP 2.
- `pca_coordinates_1296.csv`: reviewed two-component PCA coordinates for the same 2,048-bit radius-2 ECFP4 matrix.

Projection axes are dimensionless. Local proximity represents fingerprint similarity and is not a sweetness-intensity or mechanistic axis.

## Missing values and review fields

The 1,296 reviewed classification, projection, provenance, and physicochemical rows are complete. Huan stereo-review fields apply to ten Telosmoside records only; blanks for other compounds mean not applicable. Candidate 2R/2S structures remain review evidence and are not published as preferred structures.
