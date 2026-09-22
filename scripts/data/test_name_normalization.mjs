import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const auditPath = path.join(root, 'outputs/sweetmeta-name-normalization/name-normalization-audit.json');
const audit = JSON.parse(fs.readFileSync(auditPath, 'utf8'));
const rows = audit.normalized;

assert.equal(rows.length, 1296, 'The audit must contain all 1,296 source records.');
assert.equal(new Set(rows.map((row) => row.compound_id)).size, 1296, 'compound_id values must be unique.');
assert.equal(rows.filter((row) => row.source_name).length, 1296, 'Every original name must be retained.');
assert.equal(audit.stereoConflicts.length, 48, 'The 48 known stereo conflicts must be retained.');
assert.equal(
  audit.stereoConflicts.filter((row) => row.name_status === 'verified').length,
  0,
  'Stereo conflicts must never be auto-verified.',
);

const duplicateGroups = new Set(audit.duplicateNames.map((row) => row.duplicate_group));
assert.equal(duplicateGroups.size, 55, 'All 55 normalized duplicate-name groups must be classified.');
assert.ok(
  audit.duplicateNames.every((row) => row.classification),
  'Every duplicate-name record must have a classification.',
);

const allowedStatuses = new Set(['verified', 'provisional', 'manual_review', 'unresolved']);
assert.ok(rows.every((row) => allowedStatuses.has(row.name_status)), 'All status values must use the fixed vocabulary.');
assert.ok(
  rows.filter((row) => row.name_status === 'verified').every((row) => row.source_external_id && row.query_timestamp),
  'Every verified name must have an external identifier and query timestamp.',
);
assert.ok(
  rows
    .filter((row) => !['matched'].includes(row.pubchem_status) && !['matched'].includes(row.chebi_status) && !['matched'].includes(row.chembl_status))
    .every((row) => row.name_status === 'manual_review' || row.name_status === 'unresolved'),
  'Records without an exact external match may not be auto-verified or provisional.',
);

const evidenceByCompound = new Map();
for (const item of audit.sourceEvidence) {
  if (!evidenceByCompound.has(item.compound_id)) evidenceByCompound.set(item.compound_id, new Set());
  evidenceByCompound.get(item.compound_id).add(item.source);
}
assert.equal(evidenceByCompound.size, 1296, 'Every compound must have source-evidence rows.');
assert.ok(
  [...evidenceByCompound.values()].every((sources) => ['PubChem', 'ChEBI', 'ChEMBL'].every((source) => sources.has(source))),
  'Every compound must preserve a row for each queried authority.',
);

const counts = rows.reduce((acc, row) => {
  acc[row.name_status] = (acc[row.name_status] ?? 0) + 1;
  return acc;
}, {});

console.log(JSON.stringify({
  result: 'PASS',
  records: rows.length,
  statuses: counts,
  stereoConflicts: audit.stereoConflicts.length,
  saltParentConflicts: audit.saltParentConflicts.length,
  duplicateGroups: duplicateGroups.size,
  duplicateRecords: audit.duplicateNames.length,
}, null, 2));
