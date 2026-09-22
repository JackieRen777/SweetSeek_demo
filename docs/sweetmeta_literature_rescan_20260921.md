# SweetMeta literature-compound rescan

## Result

The v1 rescan processed all 1,735 SweetMeta literature records against the PDF
library at `/Users/jackieren/Desktop/library`.

- 1,735 primary PDFs mapped by exact SQLite filename and record ID.
- 18 alternate `other-v2` PDFs were retained as fallback copies.
- 1,733 PDFs supplied sufficient extractable text.
- 2 PDFs require OCR; PubMed metadata/abstract XML was cached for both records.
- 1,296 public compounds and 3,093 controlled aliases were searched.
- 20,249 unique literature-compound candidate pairs were produced.
- 25 links met the corrected conservative automatic-acceptance rule.
- 6,261 links remain candidates and 13,963 require review.
- All 162 legacy accepted pairs were reproduced by the scan.

The 100-record gold standard is complete (49 positive and 51 negative records).
All 25 automatic predictions in the sample were true positives, for 100%
precision. Recall was 34.72%, reflecting the deliberate precision-first policy.
Automatic relation-type accuracy was 88%; three reviewed relation types were
corrected from the gold standard during publication.

## Manual gold review

The completed review is stored in
`outputs/sweetmeta-literature-rescan/gold_standard_review_100.csv` with:

- `gold_has_specific_compound`: `yes` or `no`.
- `gold_compound_ids`: semicolon-separated public `compound_id` values; leave
  empty only when the answer above is `no`.
- `gold_relation_types`: semicolon-separated relationship types in the same
  order as the compound IDs.
- `reviewer_notes`: the reason for confirmation or conservative rejection.

The sample contains all 25 auto-accepted links plus stratified multi-compound,
no-specific-compound, ambiguous, low-quality/complex, and supplement records.

## Publish v1.0.6

The reproducible publication command is:

```bash
python scripts/data/finalize_sweetmeta_v106.py
```

The command refuses to publish if:

- any gold row is incomplete;
- not all available automatic predictions (up to 30) were audited; or
- measured precision is below 98%.

The gate passed and the command created
`outputs/sweetmeta-literature-rescan/SweetDatabase_v1.0.6_20260921.sqlite`,
preserves all legacy accepted links, inserts the rescan candidates with their
review states, records the rescan provenance, and writes
`v106_release_report.json`.

The published database contains 180 accepted links, 6,180 candidate links, and
14,319 needs-review links after uniqueness constraints are applied. SQLite
integrity and foreign-key checks pass, and the active API release is v1.0.6.

## Important interpretation

`compound_family` remains a literature classification derived from
`literature_records.sweetener_class`. The current SQLite does not contain a
source-backed compound-level family assignment, so the controlled compound
dictionary marks that field as `unclassified` rather than inventing values.
