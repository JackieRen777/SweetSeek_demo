import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import XLSX from 'xlsx';

const root = path.resolve(import.meta.dirname, '../..');
const defaultWorkbook = path.join(root, 'data/sweet_database_source_20260910.xlsx');
const workbookPath = path.resolve(process.argv[2] ?? defaultWorkbook);
const pubchemPath = process.argv[3] ? path.resolve(process.argv[3]) : null;
const outputDir = path.join(root, 'frontend-react/src/features/database/data');

const workbook = XLSX.readFile(workbookPath, { cellDates: false });
const sheetName = workbook.SheetNames[0];
const sourceRows = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { defval: null });

const pubchemByKey = new Map();
if (pubchemPath && fs.existsSync(pubchemPath)) {
  const stat = fs.statSync(pubchemPath);
  const payloads = stat.isDirectory()
    ? fs.readdirSync(pubchemPath)
      .filter((name) => /^pubchem-batch-\d+\.json$/.test(name))
      .map((name) => JSON.parse(fs.readFileSync(path.join(pubchemPath, name), 'utf8')))
    : [JSON.parse(fs.readFileSync(pubchemPath, 'utf8'))];
  for (const payload of payloads) {
    const records = payload?.records ?? payload?.PropertyTable?.Properties ?? [];
    for (const record of records) {
      if (record.InChIKey) pubchemByKey.set(record.InChIKey, record);
    }
  }
}

const isoDate = new Date().toISOString();
const text = (value) => value === null || value === undefined || value === '' ? null : String(value);
const number = (value) => value === null || value === undefined || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
const formulaKey = (value) => text(value)?.replace(/\s+/g, '') ?? null;

const compounds = sourceRows.map((row) => {
  const inchiKey = text(row.parent_inchikey);
  const pubchem = inchiKey ? pubchemByKey.get(inchiKey) ?? null : null;
  const sourceMw = number(row.molecular_weight);
  const pubchemMw = number(pubchem?.MolecularWeight);
  const validation = pubchem ? {
    inchiKeyMatch: pubchem.InChIKey === inchiKey,
    formulaMatch: formulaKey(pubchem.MolecularFormula) === formulaKey(row.molecular_formula),
    molecularWeightDelta: sourceMw !== null && pubchemMw !== null
      ? Math.abs(sourceMw - pubchemMw) : null,
    heavyAtomMatch: number(row.heavy_atom_count) === null || number(pubchem.HeavyAtomCount) === null
      ? null : number(row.heavy_atom_count) === number(pubchem.HeavyAtomCount),
  } : null;
  const verified = Boolean(validation?.inchiKeyMatch && validation?.formulaMatch
    && validation.molecularWeightDelta !== null && validation.molecularWeightDelta <= 0.1
    && validation.heavyAtomMatch !== false);

  return {
    id: text(row.compound_id),
    entityType: 'small-molecule',
    name: text(row.preferred_name),
    nameSource: text(row.preferred_name_source),
    inchiKey,
    canonicalTautomerInchiKey: text(row.canonical_tautomer_inchikey),
    isomericSmiles: text(row.parent_isomeric_smiles),
    canonicalSmiles: text(row.parent_canonical_smiles),
    formula: text(row.molecular_formula),
    molecularWeight: sourceMw,
    formalCharge: number(row.formal_charge),
    heavyAtomCount: number(row.heavy_atom_count),
    createdAt: text(row.created_at),
    evidence: {
      baselineTier: text(row.baseline_evidence_readiness_tier),
      releaseTier: text(row.release_evidence_readiness_tier),
      baselineGap: text(row.baseline_evidence_gap_type),
      releaseGap: text(row.release_evidence_gap_type),
      priorityScore: number(row.baseline_priority_score),
      acceptedAssertions: number(row.accepted_sweet_assertion_count) ?? 0,
    },
    review: {
      required: Number(row.manual_review_required) === 1,
      identityStatus: text(row.structure_identity_status),
      note: text(row.status_note),
    },
    pubchem: pubchem ? {
      cid: number(pubchem.CID),
      iupacName: text(pubchem.IUPACName),
      molecularFormula: text(pubchem.MolecularFormula),
      molecularWeight: pubchemMw,
      smiles: text(pubchem.SMILES),
      connectivitySmiles: text(pubchem.ConnectivitySMILES),
      inchi: text(pubchem.InChI),
      inchiKey: text(pubchem.InChIKey),
      xlogp: number(pubchem.XLogP),
      tpsa: number(pubchem.TPSA),
      hBondDonorCount: number(pubchem.HBondDonorCount),
      hBondAcceptorCount: number(pubchem.HBondAcceptorCount),
      rotatableBondCount: number(pubchem.RotatableBondCount),
      heavyAtomCount: number(pubchem.HeavyAtomCount),
      charge: number(pubchem.Charge),
      sourceUrl: pubchem.CID ? `https://pubchem.ncbi.nlm.nih.gov/compound/${pubchem.CID}` : null,
      retrievedAt: text(pubchem._retrievedAt) ?? isoDate,
      matchStatus: verified ? 'verified' : 'matched-with-discrepancy',
      validation,
    } : null,
  };
});

const countBy = (items, getter) => items.reduce((acc, item) => {
  const key = getter(item) ?? 'Not available';
  acc[key] = (acc[key] ?? 0) + 1;
  return acc;
}, {});
const missingIds = (getter) => compounds.filter((item) => getter(item) === null).map((item) => item.id);
const reviewIds = compounds.filter((item) => item.review.required).map((item) => item.id);
const pubchemMatched = compounds.filter((item) => item.pubchem).length;
const pubchemVerified = compounds.filter((item) => item.pubchem?.matchStatus === 'verified').length;

const metadata = {
  title: 'SweetSeek Sweet Compounds Database',
  version: path.basename(workbookPath, path.extname(workbookPath)),
  sourceWorkbook: path.basename(workbookPath),
  sourceSheet: sheetName,
  generatedAt: isoDate,
  totalRecords: compounds.length,
  currentEntityCoverage: { 'small-molecule': compounds.length, protein: 0, other: 0 },
  tierCounts: countBy(compounds, (item) => item.evidence.releaseTier),
  gapCounts: countBy(compounds, (item) => item.evidence.releaseGap),
  reviewRequired: reviewIds.length,
  acceptedAssertions: compounds.reduce((sum, item) => sum + item.evidence.acceptedAssertions, 0),
  pubchemMatched,
  pubchemVerified,
};

const quality = {
  metadata,
  missing: {
    canonicalTautomerInchiKey: missingIds((item) => item.canonicalTautomerInchiKey),
    heavyAtomCount: missingIds((item) => item.heavyAtomCount),
    pubchemMatch: missingIds((item) => item.pubchem),
    quantitativeSweetness: compounds.map((item) => item.id),
    evidenceRows: compounds.map((item) => item.id),
    literatureLinks: compounds.map((item) => item.id),
  },
  manualReviewIds: reviewIds,
  notes: [
    'The source workbook contains aggregate evidence readiness and assertion counts, not row-level sensory observations.',
    'Quantitative sweetness, experimental conditions, DOI/PMID links, food applications, safety, and regulatory fields are not present.',
    'Sweet proteins are planned for a later version; the data model does not restrict future entity types.',
  ],
};

fs.mkdirSync(outputDir, { recursive: true });
fs.writeFileSync(path.join(outputDir, 'database.generated.json'), JSON.stringify({ metadata, compounds }));
fs.writeFileSync(path.join(outputDir, 'metadata.generated.json'), JSON.stringify(metadata, null, 2));
fs.writeFileSync(path.join(outputDir, 'quality.generated.json'), JSON.stringify(quality, null, 2));
console.log(JSON.stringify({ records: compounds.length, pubchemMatched, pubchemVerified, reviewRequired: reviewIds.length }));
