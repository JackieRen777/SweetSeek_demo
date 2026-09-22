# SweetMeta compound detail acceptance report

Date: 2026-09-16

## Scope accepted

- Compound structure is displayed on the left and core information on the right.
- The structure panel provides a fixed-size `2D | 3D` switch. The 3D view supports orbit rotation and zoom; records without a verified PubChem structure show an explicit unavailable state.
- Core information includes ChEMBL ID, PubChem CID, SMILES, InChIKey, molecular formula, molecular weight, source, and entity type.
- The lower record view contains Overview, Relative Sweetness, Structure & Identifiers, Physicochemical Properties, Similar Compounds, Literature & Evidence, and Data Sources.
- Similar compounds are ranked by ECFP4 (Morgan radius 2, 2,048 bits) Tanimoto similarity, not UMAP screen distance.
- No molecular-structure download action was added. Public database downloads remain disabled.

## Data enrichment result

The source workbook contains 1,296 records. ChEMBL matching used the complete InChIKey only and accepted a result only when exactly one returned structure had the same full key.

| Check | Result |
| --- | ---: |
| Unique exact ChEMBL matches | 143 |
| No exact ChEMBL match | 1,153 |
| Ambiguous exact matches | 0 |
| Request errors after retries | 0 |
| PubChem matches | 878 |
| PubChem fully cross-verified | 877 |
| Workbook manual-review flags | 170 |

The enriched workbook preserves all 21 original columns and appends `chembl_id`, `chembl_match_status`, `chembl_source_url`, `chembl_retrieved_at`, and `chembl_match_method`. ChEMBL enrichment does not change evidence tiers.

## Known missing data

| Missing field group | Records affected |
| --- | ---: |
| Canonical tautomer InChIKey | 1,296 |
| Heavy atom count | 3 |
| PubChem exact match | 418 |
| ChEMBL exact match | 1,153 |
| Quantitative relative sweetness and test conditions | 1,296 |
| Assertion-level evidence rows | 1,296 |
| DOI/PMID literature links | 1,296 |

The complete record ID lists are stored in `frontend-react/src/features/database/data/quality.generated.json`. Missing values are shown as `Not available`; no values were inferred or fabricated.

## Evidence and review status

| Tier | Records |
| --- | ---: |
| R1 high readiness | 189 |
| R2 traceable | 849 |
| R3 dataset supported | 88 |
| R4 high-risk review | 170 |

The 170 manual-review IDs are also listed in `quality.generated.json`. Name and structure correction remains a separate review task, as agreed.

## Verification completed

- Focused interface tests: 12/12 passed.
- ESLint on touched source files: passed.
- TypeScript and production build: passed.
- Desktop browser at 1,440 x 900: no overlap or horizontal overflow; 2D and 3D render correctly.
- Mobile browser at 390 x 844: no page-level horizontal overflow; fixed structure dimensions and stacked information layout verified.
- Trackpad/wheel scrolling: `.sdb-main` moved from 0 to 671 px during browser validation.
- WebGL: a 346 x 280 mobile canvas was present and the molecule rendered with visible non-background atom and bond pixels.
- Missing-identifier state: verified on `IFPUUQMSZGAYIM-UHFFFAOYSA-N`.

## Residual notes

- The production build reports a large database bundle warning. This does not block functionality, but route-level code splitting should be considered as the dataset grows.
- Three.js emits a deprecation warning for its internal clock utility in development; no runtime error was observed.
- The 3D view depends on PubChem conformer availability and network access at viewing time.
