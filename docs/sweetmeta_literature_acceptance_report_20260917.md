# SweetMeta Literature Navigation v1 Acceptance Report

Date: 2026-09-17

## Release decision

Accepted for local visual review. The release is intentionally conservative: only traceable high-confidence links are public. Candidate and background-only matches remain in the review workbook and do not affect public literature counts or the existing R1-R4 evidence tier.

## Input coverage

- Local SweetSeek papers: 1,314 / 1,314 scanned.
- Indexed PDF text: 1,314 papers and 56,455 chunks available to the pipeline.
- SweetMeta compounds: 1,296 / 1,296 included in identity-dictionary construction.
- Same-name identity ambiguities: 55 normalized names. Automated prose matching uses one quality-ranked representative because the paper text cannot distinguish unresolved stereochemistry.

## Public release results

- Public compound-paper links: 208.
- Linked papers: 172.
- Linked compounds: 40.
- Unlinked compounds: 1,256.
- DOI coverage: 154 / 172 papers (89.5%).
- Exact PMID coverage: 125 / 172 papers (72.7%).
- DOI-bearing papers without an exact PubMed match: 29.
- Papers without DOI: 18.
- Manual-review candidates: 5,980.

Relationship distribution:

- `primary_subject`: 107
- `tested_sweetener`: 41
- `receptor_ligand`: 47
- `synthesis_production`: 2
- `comparator_control`: 11

`background_mention` is not published in v1; it remains a review category.

## Precision audit

A deterministic, relationship-stratified sample of 100 public links was manually reviewed across common sugars, artificial sweeteners, natural sweeteners and lower-frequency molecules.

- Initial review: 98 / 100 links had both the correct compound association and relationship label.
- Two mixture-design records were over-classified as `comparator_control` because the first rule treated `mixture` and `binary` as comparator terms.
- The generic terms were removed; only explicit comparison/control language now creates comparator links.
- Final re-check: 100 / 100 sampled links retained correct compound association and acceptable relationship classification.

Specific false-positive controls were verified for Sucrose, Glucose and Aspartame. Public counts are 78, 9 and 12 respectively; repeated background mentions, glucose metabolic endpoints, filenames-only matches, amino-acid residue mentions and “steviol glycosides” identity confusion are excluded from automatic publication.

## Identifier and consistency checks

- DOI values are normalized to bare `10.*` identifiers and website links use `https://doi.org/{doi}`.
- PMID is accepted only from a PubMed DOI `[AID]` exact query when the returned record contains the same DOI.
- No public link has a missing compound or paper identifier.
- Duplicate local PDFs resolving to the same DOI are deduplicated by `compound_id + paper_id`.
- At least one paper links to multiple compounds while preserving a distinct relationship row for each compound.
- Records without DOI or PMID remain visible with an explicit unavailable state.

## Interface acceptance

- Global Literature page includes metrics, compound/title/DOI/PMID/journal search, relationship/year/status filters, pagination and expandable evidence.
- Compound, DOI and PMID navigation targets are active and open the expected record or authoritative external source.
- Compound detail defaults to Core evidence and separates Comparators, Synthesis & production and Background mentions.
- Empty categories show an explicit state and never use review candidates as formal evidence.
- Literature JSON loads at runtime only when the Literature page or compound detail literature section is mounted.
- Desktop and mobile layouts preserve readable labels, identifiers and evidence expansion without overlap.

## Known data gaps

- Only 40 compounds have sufficiently strong local-corpus evidence under the v1 precision policy.
- 1,256 compounds have no accepted local paper link; this is an evidence-coverage gap, not proof of no literature.
- 5,980 candidate relations require human acceptance/rejection, with evidence sentence and PDF page retained where available.
- 55 same-name records require identity curation before literature can be safely distributed across stereochemical variants.
- Authoritative aliases are sparse for many low-frequency compounds; v1 uses preferred names, verified PubChem IUPAC names and a small controlled alias set.
- Some older PDFs have malformed catalog titles or noisy OCR. These are reviewable but not elevated solely from filename or mention count.
- Sweet proteins are not included in the current compound release and can be added without changing the literature data contract.

## Verification

- Data-contract tests: passed.
- Frontend component tests: passed (53 / 53).
- Targeted lint for modified database files: passed.
- Production build: passed.
- Full-repository lint: not clean due to 11 pre-existing errors outside the files changed for this release.
- Review workbook: four sheets rendered and visually inspected; formula-error scan returned zero matches.
