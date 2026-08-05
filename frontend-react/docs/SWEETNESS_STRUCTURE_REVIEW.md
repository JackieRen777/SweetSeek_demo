# Sweetness structure review workflow

No molecule structure is considered verified only because an image rendered.
Rendering proves syntax/processability, not that the structure belongs to the
named compound or the cited PubChem CID.

## Required checks

1. Parse and standardize the stored SMILES with one pinned RDKit version.
2. Retrieve the PubChem record for the stored CID and compare standardized
   connectivity, stereochemistry, formula, and InChIKey.
3. Reject placeholder identifiers and flag name/CID/SMILES disagreements.
4. Generate the 2D depiction and 3D conformer from the approved standardized
   structure, then visually inspect stereochemistry, charge, counterions, and
   tautomer/protonation state.
5. Record reviewer, review date, tool versions, source accession, and notes.

## Status contract

- `pending`: not yet checked by a curator; this is the current status for all
  V1 test records.
- `verified`: automated identity checks and curator review both passed.
- `mismatch`: at least one identity field disagrees; structure views should be
  suppressed until corrected.
- `not_applicable`: non-small-molecule records such as sweet proteins require a
  separate sequence/structure workflow.

The frontend may display 2D/3D previews for `pending` records only when the
status is visible beside the viewer. It must never label these previews as
verified evidence.
