import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const outputDirectory = path.join(root, 'outputs/sweetmeta-name-normalization');
const audit = JSON.parse(fs.readFileSync(path.join(outputDirectory, 'name-normalization-audit.json'), 'utf8'));
const verified = audit.normalized.filter((row) => row.name_status === 'verified');

const categoryOf = (row) => {
  const names = `${row.source_name} ${row.preferred_name_candidate} ${row.synonyms}`.toLowerCase();
  if (/\b(?:sucrose|glucose|fructose|maltose|lactose|trehalose|xylitol|erythritol|sorbitol|mannitol)\b/.test(names)) {
    return 'common_sugars_and_polyols';
  }
  if (/\b(?:aspartame|acesulfame|saccharin|sucralose|cyclamate|neotame|advantame|alitame)\b/.test(names)) {
    return 'artificial_intense_sweeteners';
  }
  if (/\b(?:stevioside|rebaudioside|mogroside|glycyrrhizin|phyllodulcin|hernandulcin|rubusoside|steviol)\b/.test(names)) {
    return 'natural_high_intensity_sweeteners';
  }
  return 'other_low_frequency_compounds';
};

const categorized = new Map();
for (const row of verified) {
  const category = categoryOf(row);
  if (!categorized.has(category)) categorized.set(category, []);
  categorized.get(category).push(row);
}
for (const rows of categorized.values()) rows.sort((a, b) => a.compound_id.localeCompare(b.compound_id));

const targets = new Map([
  ['common_sugars_and_polyols', 20],
  ['artificial_intense_sweeteners', 15],
  ['natural_high_intensity_sweeteners', 20],
  ['other_low_frequency_compounds', 45],
]);
const selected = [];
const selectedIds = new Set();
for (const [category, target] of targets) {
  for (const row of (categorized.get(category) ?? []).slice(0, target)) {
    selected.push({ category, ...row });
    selectedIds.add(row.compound_id);
  }
}
for (const row of verified) {
  if (selected.length >= 100) break;
  if (selectedIds.has(row.compound_id)) continue;
  selected.push({ category: categoryOf(row), ...row });
  selectedIds.add(row.compound_id);
}

if (selected.length !== 100) throw new Error(`Expected 100 validation records, received ${selected.length}.`);

const records = selected.map((row, index) => ({
  sample_number: index + 1,
  category: row.category,
  compound_id: row.compound_id,
  full_inchikey: row.full_inchikey,
  source_name: row.source_name,
  preferred_name_candidate: row.preferred_name_candidate,
  systematic_name: row.systematic_name,
  name_source: row.name_source,
  source_external_id: row.source_external_id,
  query_timestamp: row.query_timestamp,
  identity_trace_check: row.full_inchikey && row.source_external_id && row.query_timestamp ? 'pass' : 'fail',
  human_name_decision: 'pending',
  human_review_note: '',
}));
const categoryCounts = records.reduce((counts, row) => {
  counts[row.category] = (counts[row.category] ?? 0) + 1;
  return counts;
}, {});
const output = {
  metadata: {
    generatedAt: new Date().toISOString(),
    sampleSize: records.length,
    sourcePopulation: verified.length,
    selection: 'Deterministic category-first sample from auto-verified records; remainder filled by compound_id order.',
    humanAccuracyStatus: 'pending',
  },
  categoryCounts,
  records,
};
fs.writeFileSync(path.join(outputDirectory, 'name-normalization-validation-sample-100.json'), JSON.stringify(output, null, 2) + '\n');
console.log(JSON.stringify({ sampleSize: records.length, categoryCounts }, null, 2));
