import fs from 'node:fs/promises';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const root = '/Users/jackieren/Desktop/FCN_SweetSeek';
const publicData = JSON.parse(await fs.readFile(`${root}/frontend-react/public/database-data/literature.generated.json`, 'utf8'));
const reviewData = JSON.parse(await fs.readFile(`${root}/data/literature_link_review_20260917.json`, 'utf8'));
const compounds = JSON.parse(await fs.readFile(`${root}/frontend-react/src/features/database/data/database.generated.json`, 'utf8')).compounds;
const compoundNames = new Map(compounds.map((item) => [item.id, item.name]));
const outputDir = `${root}/outputs/sweetmeta-literature-20260917`;

const workbook = Workbook.create();
const summary = workbook.worksheets.add('Summary');
const publicSheet = workbook.worksheets.add('Public Links');
const reviewSheet = workbook.worksheets.add('Review Candidates');
const method = workbook.worksheets.add('Method');

const navy = '#173D5F';
const blue = '#2F75BD';
const pale = '#EAF3FB';
const green = '#DCEFE7';
const amber = '#FFF0D5';
const line = '#DCE5EB';
const muted = '#5E6E7E';
const clean = (value) => typeof value === 'string'
  ? value.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]/g, ' ').replace(/\s+/g, ' ').trim()
  : value;

function titleBand(sheet, range, title, subtitle) {
  sheet.getRange(range).merge();
  const anchor = range.split(':')[0];
  sheet.getRange(anchor).values = [[`${title}\n${subtitle}`]];
  sheet.getRange(range).format = {
    fill: navy,
    font: { bold: true, color: '#FFFFFF', size: 16 },
    wrapText: true,
    verticalAlignment: 'center',
  };
  sheet.getRange(range).format.rowHeight = 54;
}

function formatTable(sheet, address, headerAddress, widths) {
  sheet.getRange(headerAddress).format = {
    fill: blue,
    font: { bold: true, color: '#FFFFFF' },
    wrapText: true,
    verticalAlignment: 'center',
  };
  sheet.getRange(address).format.borders = {
    insideHorizontal: { style: 'thin', color: line },
    bottom: { style: 'thin', color: line },
  };
  widths.forEach(([column, width]) => { sheet.getRange(column).format.columnWidth = width; });
  sheet.freezePanes.freezeRows(Number(headerAddress.match(/\d+/)[0]));
  sheet.showGridLines = false;
}

titleBand(summary, 'A1:H2', 'SweetMeta Literature Review', 'Auditable compound-paper associations generated from the local SweetSeek corpus');
summary.getRange('A4:B11').values = [
  ['Metric', 'Value'],
  ['Source papers', publicData.metadata.sourcePaperCount],
  ['Indexed papers', publicData.metadata.indexedPaperCount],
  ['Source compounds', publicData.metadata.sourceCompoundCount],
  ['Public links', null],
  ['Linked papers', publicData.metadata.linkedPaperCount],
  ['Linked compounds', publicData.metadata.linkedCompoundCount],
  ['Review candidates', null],
];
summary.getRange('B8').formulas = [[`=COUNTA('Public Links'!$A$2:$A$${publicData.links.length + 1})`]];
summary.getRange('B11').formulas = [[`=COUNTA('Review Candidates'!$A$2:$A$${reviewData.candidates.length + 1})`]];
summary.getRange('D4:E10').values = [
  ['Coverage', 'Value'],
  ['Public papers with DOI', publicData.metadata.doiCount],
  ['Public papers with PMID', publicData.metadata.pmidCount],
  ['DOI coverage', null],
  ['PMID coverage', null],
  ['Same-name identity ambiguities', publicData.metadata.identityAmbiguityCount],
  ['Generated at', publicData.metadata.generatedAt],
];
summary.getRange('E7').formulas = [[`=E5/B9`]];
summary.getRange('E8').formulas = [[`=E6/B9`]];
summary.getRange('E7:E8').format.numberFormat = '0.0%';
summary.getRange('G4:H7').values = [
  ['Review decisions', 'Count'],
  ['Accepted', null],
  ['Rejected', null],
  ['Pending', null],
];
summary.getRange('H5').formulas = [[`=COUNTIF('Review Candidates'!$R$2:$R$${reviewData.candidates.length + 1},"accept")`]];
summary.getRange('H6').formulas = [[`=COUNTIF('Review Candidates'!$R$2:$R$${reviewData.candidates.length + 1},"reject")`]];
summary.getRange('H7').formulas = [[`=COUNTIF('Review Candidates'!$R$2:$R$${reviewData.candidates.length + 1},"pending")`]];
summary.getRange('A13:H13').merge();
summary.getRange('A13').values = [[`Public policy: ${publicData.metadata.policy}`]];
summary.getRange('A13:H13').format = { fill: pale, font: { color: navy, bold: true }, wrapText: true };
summary.getRange('A15:H18').merge();
summary.getRange('A15').values = [['Important: automated literature linkage does not modify the existing R1-R4 evidence tier. Same-name records with unresolved stereochemical identity are linked only to one representative record and are listed as identity ambiguities for later curation.']];
summary.getRange('A15:H18').format = { fill: amber, font: { color: '#6E4B10' }, wrapText: true, verticalAlignment: 'center' };
for (const header of ['A4:B4', 'D4:E4', 'G4:H4']) summary.getRange(header).format = { fill: blue, font: { bold: true, color: '#FFFFFF' } };
summary.getRange('A4:B11').format.borders = { preset: 'outside', style: 'thin', color: line };
summary.getRange('D4:E10').format.borders = { preset: 'outside', style: 'thin', color: line };
summary.getRange('G4:H7').format.borders = { preset: 'outside', style: 'thin', color: line };
['A:A', 'D:D', 'G:G'].forEach((column) => { summary.getRange(column).format.columnWidth = 28; });
['B:B', 'E:E', 'H:H'].forEach((column) => { summary.getRange(column).format.columnWidth = 20; });
summary.freezePanes.freezeRows(2);
summary.showGridLines = false;

const publicHeaders = ['Link ID', 'Compound ID', 'Compound', 'Relationship', 'Primary', 'Paper ID', 'Article title', 'Authors', 'Journal', 'Year', 'DOI', 'PubMed ID', 'Evidence excerpt', 'PDF page', 'Match method', 'Matched alias', 'Confidence', 'Review status', 'DOI URL', 'PubMed URL'];
const publicRows = publicData.links.map((link) => {
  const paper = publicData.papers[link.paperId];
  return [link.linkId, link.compoundId, compoundNames.get(link.compoundId) ?? '', link.relationshipType, link.isPrimary, link.paperId, paper.title, (paper.authors ?? []).join('; '), paper.journal ?? '', paper.year ?? null, paper.doi ?? '', paper.pmid ?? '', link.evidenceExcerpt ?? '', link.pageNumber ?? '', link.matchMethod, link.matchedAlias, link.confidence, link.reviewStatus, paper.doi ? `https://doi.org/${paper.doi}` : '', paper.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/` : ''].map(clean);
});
publicSheet.getRangeByIndexes(0, 0, publicRows.length + 1, publicHeaders.length).values = [publicHeaders, ...publicRows];
formatTable(publicSheet, `A1:T${publicRows.length + 1}`, 'A1:T1', [['A:B', 22], ['C:C', 20], ['D:D', 18], ['E:F', 18], ['G:G', 48], ['H:H', 34], ['I:I', 22], ['J:L', 13], ['M:M', 60], ['N:R', 17], ['S:T', 38]]);
publicSheet.getRange(`M2:M${publicRows.length + 1}`).format.wrapText = true;
publicSheet.getRange(`Q2:Q${publicRows.length + 1}`).format.numberFormat = '0.00';
publicSheet.tables.add(`A1:T${publicRows.length + 1}`, true, 'PublicLinksTable');

const reviewHeaders = ['Link ID', 'Compound ID', 'Compound', 'Paper ID', 'Article title', 'Journal', 'Year', 'DOI', 'Relationship candidate', 'Evidence excerpt', 'PDF page', 'Match method', 'Matched alias', 'Mention count', 'Confidence', 'Review reason', 'Evidence status', 'Review decision', 'Review note', 'DOI URL'];
const reviewRows = reviewData.candidates.map((item) => [item.linkId, item.compoundId, item.compoundName, item.paperId, item.paperTitle, item.journal ?? '', Number(item.year) || null, item.doi ?? '', item.relationshipType, item.evidenceExcerpt ?? '', item.pageNumber ?? '', item.matchMethod, item.matchedAlias, item.mentionCount, item.confidence, item.reviewReason ?? '', item.reviewStatus, item.reviewDecision, item.reviewNote, item.doi ? `https://doi.org/${item.doi}` : ''].map(clean));
reviewSheet.getRangeByIndexes(0, 0, reviewRows.length + 1, reviewHeaders.length).values = [reviewHeaders, ...reviewRows];
formatTable(reviewSheet, `A1:T${reviewRows.length + 1}`, 'A1:T1', [['A:B', 22], ['C:C', 20], ['D:D', 22], ['E:E', 48], ['F:F', 24], ['G:H', 15], ['I:I', 19], ['J:J', 60], ['K:M', 16], ['N:O', 14], ['P:P', 45], ['Q:R', 18], ['S:S', 34], ['T:T', 38]]);
reviewSheet.getRange(`J2:J${reviewRows.length + 1}`).format.wrapText = true;
reviewSheet.getRange(`P2:P${reviewRows.length + 1}`).format.wrapText = true;
reviewSheet.getRange(`O2:O${reviewRows.length + 1}`).format.numberFormat = '0.00';
reviewSheet.getRange(`R2:R${reviewRows.length + 1}`).dataValidation = { rule: { type: 'list', values: ['pending', 'accept', 'reject'] } };
reviewSheet.getRange(`R2:R${reviewRows.length + 1}`).conditionalFormats.add('containsText', { text: 'accept', format: { fill: green, font: { color: '#276749', bold: true } } });
reviewSheet.getRange(`R2:R${reviewRows.length + 1}`).conditionalFormats.add('containsText', { text: 'reject', format: { fill: '#FBE3E3', font: { color: '#9B2C2C', bold: true } } });
reviewSheet.tables.add(`A1:T${reviewRows.length + 1}`, true, 'ReviewCandidatesTable');

titleBand(method, 'A1:H2', 'Method and Review Protocol', 'SweetMeta literature navigation v1');
const methodRows = [
  ['Step', 'Rule', 'Review implication'],
  ['Identity', 'compound_id + InChIKey remains the database identity. When multiple structures share the same normalized name, automated prose matching uses one quality-ranked representative.', 'Inspect the identity ambiguity list in the JSON before redistributing a paper to stereochemical records.'],
  ['Matching', 'Preferred name, verified PubChem IUPAC name and a small controlled alias set; strict token boundaries and Unicode/hyphen normalization.', 'Do not accept acronym-only or ambiguous common-word matches without direct evidence.'],
  ['Public rule', 'Valid exact title match, or a self-contained sentence containing both an experimental action and sweet/taste/receptor context. High-frequency names require two supported excerpts unless present in the title.', 'Public rows are auto-high-confidence, but scientific acceptance still requires the 100-row audit.'],
  ['Excluded', 'Reference-list hits, one-off background mentions, malformed titles and excerpts without direct experimental context.', 'These remain candidates and do not inflate website counts.'],
  ['PMID', 'Resolved only from exact DOI [AID] PubMed searches and accepted only when PubMed returns the same DOI.', 'Blank PMID means no exact result; do not infer from similar titles.'],
  ['Evidence tier', 'Literature association is independent of SweetMeta R1-R4.', 'Never change R1-R4 solely because a link was generated or accepted.'],
  ['Decision', 'Set Review decision to accept or reject and record the scientific reason in Review note.', 'Only accepted candidate rows should enter a future public release.'],
];
method.getRange(`A4:C${methodRows.length + 3}`).values = methodRows;
method.getRange('A4:C4').format = { fill: blue, font: { bold: true, color: '#FFFFFF' } };
method.getRange(`A5:C${methodRows.length + 3}`).format = { wrapText: true, verticalAlignment: 'top' };
method.getRange('A:A').format.columnWidth = 20;
method.getRange('B:C').format.columnWidth = 58;
method.getRange(`A4:C${methodRows.length + 3}`).format.borders = { insideHorizontal: { style: 'thin', color: line }, bottom: { style: 'thin', color: line } };
method.freezePanes.freezeRows(4);
method.showGridLines = false;

await fs.mkdir(outputDir, { recursive: true });
const checks = [];
checks.push((await workbook.inspect({ kind: 'table', range: 'Summary!A1:H18', include: 'values,formulas', tableMaxRows: 20, tableMaxCols: 10 })).ndjson);
checks.push((await workbook.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A', options: { useRegex: true, maxResults: 100 }, summary: 'final formula error scan' })).ndjson);
for (const [sheetName, range] of [['Summary', 'A1:H18'], ['Public Links', 'A1:T22'], ['Review Candidates', 'A1:T22'], ['Method', 'A1:C12']]) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: 'png' });
  await fs.writeFile(`${outputDir}/${sheetName.toLowerCase().replaceAll(' ', '-')}.png`, new Uint8Array(await preview.arrayBuffer()));
}
try {
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(`${outputDir}/sweetmeta_literature_review_20260917.xlsx`);
  console.log(checks.join('\n'));
} catch (error) {
  console.error(`WORKBOOK_EXPORT_ERROR: ${error?.message ?? String(error)}`);
  process.exitCode = 1;
}
