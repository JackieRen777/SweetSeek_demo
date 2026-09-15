# Sweet Database update workflow

## Data authority

The newest SweetSeek workbook is the compound master. External annotations never replace `compound_id`, `preferred_name`, source structure strings, evidence tiers, or review flags. PubChem data is joined by exact `parent_inchikey` and stored as a separate enrichment layer.

The current portal is entity-extensible. The 2026-09-10 release contains small molecules, but the product and data model are not limited to small molecules. Sweet proteins can be added in a later release with protein-specific identifiers and fields.

## Update sequence

1. Place the new workbook in `data/` and retain the same flat-table conventions.
2. Build a source-only portal dataset to validate row count, IDs, and required columns:

   ```bash
   cd frontend-react
   npm run data:build -- ../data/<new_workbook>.xlsx
   ```

3. Use `scripts/data/fetch_pubchem_batches.py` with a new, release-specific output directory. The script accepts the generated `database.generated.json`, queries PubChem in rate-limited batches, retries transient errors, and records no-match batches explicitly. A PubChem REST client path is passed with `--rest-client` so every request remains auditable.
4. Consolidate accepted PubChem records into a versioned `data/pubchem_enrichment_<release>.json` file. Never reuse a batch cache from a different workbook release.
5. Rebuild the portal with the workbook and enrichment file:

   ```bash
   cd frontend-react
   npm run data:build -- ../data/<new_workbook>.xlsx ../data/pubchem_enrichment_<release>.json
   npm test -- --run
   npm run build
   ```

6. Review every `matched-with-discrepancy` record before correcting the source workbook. Do not copy the external preferred name into the source without resolving the underlying identity.

## Required invariants

- `compound_id` is non-empty and unique.
- The current small-molecule release has a non-empty, unique `parent_inchikey` for each row.
- All R1-R4 evidence tiers remain public and filterable.
- `manual_review_required=1` is always visible in the portal and quality report.
- Quantitative sweetness, literature, safety, application, and receptor values remain unavailable until supplied as traceable rows.
- Public download controls remain disabled until the download policy changes.

## Future sweet-protein extension

Add an `entity_type` discriminator and a protein master keyed by a stable protein identifier. Protein sequence, organism, isoform, sweetness evidence, literature relationships, and structure references should live in protein-specific columns or linked tables; do not force protein records into InChIKey/SMILES fields.
