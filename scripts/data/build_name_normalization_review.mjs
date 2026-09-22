import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const root = process.cwd();
const outputDirectory = path.join(root, 'outputs/sweetmeta-name-normalization');
const auditPath = path.join(outputDirectory, 'name-normalization-audit.json');
const outputPath = path.join(outputDirectory, 'sweetmeta_name_normalization_review.xlsx');
const previewDirectory = path.join(outputDirectory, 'previews');
const audit = JSON.parse(await fs.readFile(auditPath, 'utf8'));

const COLORS = {
  navy: '#123B5D',
  blue: '#1677C8',
  paleBlue: '#EAF4FB',
  border: '#D7E3EC',
  text: '#243746',
  muted: '#5F7180',
  verified: '#DDF3E5',
  manual: '#FCE7E7',
  unresolved: '#FFF2CC',
};

const workbook = Workbook.create();
workbook.comments.setSelf({ displayName: 'User' });

const normalizeValue = (value) => {
  if (value === null || value === undefined) return '';
  if (Array.isArray(value)) return value.join(' | ');
  if (typeof value === 'object') return JSON.stringify(value);
  return value;
};

const columnName = (index) => {
  let value = index + 1;
  let output = '';
  while (value > 0) {
    const remainder = (value - 1) % 26;
    output = String.fromCharCode(65 + remainder) + output;
    value = Math.floor((value - 1) / 26);
  }
  return output;
};

const normalizedColumns = [
  ['compound_id', 'Compound ID', 27], ['source_name', 'Source name', 28],
  ['preferred_name_candidate', 'Preferred name candidate', 34], ['systematic_name', 'Systematic name', 42],
  ['synonyms', 'Synonyms', 48], ['name_source', 'Name source', 25],
  ['source_external_id', 'Source external ID', 20], ['name_status', 'Name status', 16],
  ['stereo_status', 'Stereo status', 18], ['salt_form', 'Salt form', 23],
  ['review_reason', 'Review reason', 42], ['review_decision', 'Review decision', 18],
  ['reviewer_edit', 'Reviewer edit', 34], ['reviewer_note', 'Reviewer note', 34],
  ['full_inchikey', 'Full InChIKey', 30], ['connectivity_inchikey', 'Connectivity InChIKey', 22],
  ['molecular_formula', 'Molecular formula', 18], ['isomeric_smiles', 'Isomeric SMILES', 44],
  ['duplicate_group', 'Duplicate group', 24], ['duplicate_classification', 'Duplicate classification', 34],
  ['pubchem_status', 'PubChem status', 17], ['pubchem_cid', 'PubChem CID', 15],
  ['pubchem_title', 'PubChem title', 34], ['pubchem_iupac_name', 'PubChem IUPAC name', 42],
  ['pubchem_candidate_count', 'PubChem candidate count', 22],
  ['pubchem_synonym_status', 'PubChem synonym status', 22],
  ['pubchem_synonym_count', 'PubChem synonym count', 22],
  ['chebi_status', 'ChEBI status', 16], ['chebi_id', 'ChEBI ID', 15], ['chebi_name', 'ChEBI name', 28],
  ['chembl_status', 'ChEMBL status', 17], ['chembl_id', 'ChEMBL ID', 16],
  ['chembl_pref_name', 'ChEMBL preferred name', 30], ['query_timestamp', 'Query timestamp', 25],
];

const conflictColumns = [
  ['compound_id', 'Compound ID', 27], ['source_name', 'Source name', 30],
  ['preferred_name_candidate', 'Preferred name candidate', 38], ['name_status', 'Name status', 16],
  ['full_inchikey', 'Full InChIKey', 30], ['molecular_formula', 'Molecular formula', 18],
  ['isomeric_smiles', 'Isomeric SMILES', 46], ['stereo_status', 'Stereo status', 18],
  ['salt_form', 'Salt form', 23], ['review_reason', 'Review reason', 46],
  ['name_source', 'Name source', 24], ['source_external_id', 'Source external ID', 20],
  ['review_decision', 'Review decision', 18], ['reviewer_edit', 'Reviewer edit', 34],
  ['reviewer_note', 'Reviewer note', 34],
];

const duplicateColumns = [
  ['duplicate_group', 'Duplicate group', 28], ['classification', 'Classification', 40],
  ['group_size', 'Group size', 13], ['compound_id', 'Compound ID', 27],
  ['source_name', 'Source name', 32], ['full_inchikey', 'Full InChIKey', 30],
  ['connectivity_inchikey', 'Connectivity InChIKey', 22], ['molecular_formula', 'Molecular formula', 18],
  ['review_decision', 'Review decision', 18], ['reviewer_edit', 'Reviewer edit', 34],
  ['reviewer_note', 'Reviewer note', 34],
];

const evidenceColumns = [
  ['compound_id', 'Compound ID', 27], ['source', 'Source', 13], ['query_key', 'Full InChIKey query key', 30],
  ['status', 'Match status', 16], ['external_id', 'External ID', 17],
  ['preferred_name', 'Preferred name', 34], ['systematic_name', 'Systematic name', 42],
  ['doi', 'DOI', 30], ['pmid', 'PMID', 16], ['evidence_excerpt', 'Evidence excerpt', 52],
  ['page_number', 'PDF page', 13], ['match_method', 'Match method', 24],
  ['source_url', 'Source URL', 52], ['queried_at', 'Queried at', 25],
];

const changeColumns = [
  ['compound_id', 'Compound ID', 27], ['field_name', 'Field', 18], ['original_value', 'Original value', 34],
  ['candidate_value', 'Candidate value', 38], ['changed', 'Changed', 12], ['decision', 'Decision', 18],
  ['evidence_source', 'Evidence source', 24], ['review_status', 'Review status', 18],
  ['review_note', 'Review note', 36],
];

function prepareReviewRows(rows, fields) {
  return rows.map((row) => {
    const copy = { ...row };
    for (const field of fields) if (!copy[field]) copy[field] = 'pending';
    return copy;
  });
}

function styleStatusColumn(sheet, range, fieldNames) {
  const index = fieldNames.findIndex((field) => field === 'name_status' || field === 'review_status');
  if (index < 0) return;
  const statusRange = sheet.getRange(`${columnName(index)}6:${columnName(index)}${range.endRow}`);
  statusRange.conditionalFormats.add('containsText', { text: 'verified', format: { fill: COLORS.verified, font: { color: '#17633A' } } });
  statusRange.conditionalFormats.add('containsText', { text: 'manual_review', format: { fill: COLORS.manual, font: { color: '#9B1C1C' } } });
  statusRange.conditionalFormats.add('containsText', { text: 'unresolved', format: { fill: COLORS.unresolved, font: { color: '#7A4D00' } } });
}

function addDataSheet({ name, description, rows, columns, reviewFields = [], tableName }) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const endColumn = columnName(columns.length - 1);
  const endRow = rows.length + 5;

  sheet.getRange(`A1:${endColumn}1`).format.fill = COLORS.navy;
  sheet.getRange('A1').values = [[name]];
  sheet.getRange('A1').format = { font: { bold: true, color: '#FFFFFF', size: 16 }, rowHeight: 28 };
  sheet.getRange('A2').values = [[description]];
  sheet.getRange(`A2:${endColumn}2`).format = { fill: COLORS.paleBlue, font: { color: COLORS.text, italic: true }, rowHeight: 30 };
  sheet.getRange('A3:D3').values = [['Records', rows.length, 'Generated (UTC)', audit.metadata.generatedAt]];
  sheet.getRange('A3:D3').format = { font: { color: COLORS.muted }, rowHeight: 20 };
  sheet.getRange('D3').format.numberFormat = 'yyyy-mm-dd hh:mm:ss';

  const headers = columns.map(([, label]) => label);
  sheet.getRange(`A5:${endColumn}5`).values = [headers];
  sheet.getRange(`A5:${endColumn}5`).format = {
    fill: COLORS.blue,
    font: { bold: true, color: '#FFFFFF', size: 10 },
    wrapText: true,
    verticalAlignment: 'center',
    rowHeight: 34,
    borders: { bottom: { style: 'medium', color: COLORS.navy } },
  };

  if (rows.length) {
    const values = rows.map((row) => columns.map(([key]) => normalizeValue(row[key])));
    sheet.getRange(`A6:${endColumn}${endRow}`).values = values;
    sheet.getRange(`A6:${endColumn}${endRow}`).format = {
      font: { color: COLORS.text, size: 9 },
      verticalAlignment: 'top',
      rowHeight: 28,
    };
    const table = sheet.tables.add(`A5:${endColumn}${endRow}`, true, tableName);
    table.style = 'TableStyleMedium2';
    table.showBandedRows = true;
    table.showFilterButton = true;
  }

  columns.forEach(([, , width], index) => {
    const letter = columnName(index);
    sheet.getRange(`${letter}1:${letter}${Math.max(endRow, 6)}`).format.columnWidth = width;
  });

  const wrapKeys = new Set(['source_name', 'preferred_name_candidate', 'systematic_name', 'synonyms', 'review_reason', 'reviewer_edit', 'reviewer_note', 'isomeric_smiles', 'preferred_name', 'source_url', 'evidence_excerpt', 'original_value', 'candidate_value', 'review_note']);
  columns.forEach(([key], index) => {
    if (wrapKeys.has(key) && rows.length) {
      const letter = columnName(index);
      sheet.getRange(`${letter}6:${letter}${endRow}`).format.wrapText = true;
    }
    if ((key === 'query_timestamp' || key === 'queried_at') && rows.length) {
      const letter = columnName(index);
      sheet.getRange(`${letter}6:${letter}${endRow}`).format.numberFormat = 'yyyy-mm-dd hh:mm:ss';
    }
  });

  for (const reviewField of reviewFields) {
    const index = columns.findIndex(([key]) => key === reviewField);
    if (index >= 0 && rows.length) {
      const letter = columnName(index);
      sheet.getRange(`${letter}6:${letter}${endRow}`).dataValidation = {
        rule: { type: 'list', values: ['pending', 'accept', 'reject', 'edit'] },
      };
    }
  }

  styleStatusColumn(sheet, { endRow }, columns.map(([key]) => key));
  sheet.freezePanes.freezeRows(5);
  sheet.freezePanes.freezeColumns(Math.min(3, columns.length));
  return { sheet, endColumn, endRow };
}

const normalizedRows = prepareReviewRows(audit.normalized, ['review_decision']);
const stereoRows = prepareReviewRows(audit.stereoConflicts, ['review_decision']);
const saltRows = prepareReviewRows(audit.saltParentConflicts, ['review_decision']);
const duplicateRows = prepareReviewRows(audit.duplicateNames, ['review_decision']);
const unresolvedRows = prepareReviewRows(audit.unresolved, ['review_decision']);
const changeRows = prepareReviewRows(audit.changeLog, ['decision']);

addDataSheet({
  name: 'Normalized Names',
  description: 'All 1,296 records. Review decision is editable; source names remain unchanged in the source workbook.',
  rows: normalizedRows,
  columns: normalizedColumns,
  reviewFields: ['review_decision'],
  tableName: 'NormalizedNamesTable',
});
addDataSheet({
  name: 'Stereo Conflicts',
  description: 'Names claiming stereochemistry where the stored structure does not define the same stereochemical identity.',
  rows: stereoRows,
  columns: conflictColumns,
  reviewFields: ['review_decision'],
  tableName: 'StereoConflictsTable',
});
addDataSheet({
  name: 'Salt Parent Conflicts',
  description: 'Names claiming a salt form while the stored structure lacks a separate counterion or equivalent representation.',
  rows: saltRows,
  columns: conflictColumns,
  reviewFields: ['review_decision'],
  tableName: 'SaltParentConflictsTable',
});
addDataSheet({
  name: 'Duplicate Names',
  description: 'The 55 normalized duplicate-name groups classified by exact identity, connectivity, stereochemistry, or distinct identity.',
  rows: duplicateRows,
  columns: duplicateColumns,
  reviewFields: ['review_decision'],
  tableName: 'DuplicateNamesTable',
});
addDataSheet({
  name: 'Unresolved Records',
  description: 'Records requiring manual review or lacking an exact external identity match. Weak candidates are not auto-adopted.',
  rows: unresolvedRows,
  columns: normalizedColumns,
  reviewFields: ['review_decision'],
  tableName: 'UnresolvedRecordsTable',
});
addDataSheet({
  name: 'Source Evidence',
  description: 'One auditable row per compound and authority, including the exact query key, match status, timestamp, and source URL.',
  rows: audit.sourceEvidence,
  columns: evidenceColumns,
  tableName: 'SourceEvidenceTable',
});
addDataSheet({
  name: 'Change Log',
  description: 'Proposed preferred-name changes only. No source workbook or website value has been overwritten.',
  rows: changeRows,
  columns: changeColumns,
  reviewFields: ['decision'],
  tableName: 'ChangeLogTable',
});

await fs.mkdir(outputDirectory, { recursive: true });
await fs.mkdir(previewDirectory, { recursive: true });

const checks = [];
for (const sheetName of ['Normalized Names', 'Stereo Conflicts', 'Salt Parent Conflicts', 'Duplicate Names', 'Unresolved Records', 'Source Evidence', 'Change Log']) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const used = sheet.getUsedRange(true);
  const preview = await workbook.render({ sheetName, range: `A1:${columnName(Math.min(used.columnCount - 1, 11))}20`, scale: 1.2, format: 'png' });
  const previewPath = path.join(previewDirectory, `${sheetName.toLowerCase().replaceAll(' ', '-')}.png`);
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));
  checks.push({ sheetName, previewPath });
}

const inspection = await workbook.inspect({
  kind: 'table',
  range: 'Normalized Names!A1:N12',
  include: 'values,formulas',
  tableMaxRows: 12,
  tableMaxCols: 14,
  maxChars: 12000,
});
const formulaErrors = await workbook.inspect({
  kind: 'match',
  searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A',
  options: { useRegex: true, maxResults: 300 },
  summary: 'final formula error scan',
  maxChars: 4000,
});

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, previews: checks, inspection: inspection.ndjson, formulaErrors: formulaErrors.ndjson }, null, 2));
