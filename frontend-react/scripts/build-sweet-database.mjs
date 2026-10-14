import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { execFileSync } from 'node:child_process';
import XLSX from 'xlsx';

const root = path.resolve(import.meta.dirname, '../..');
const defaultWorkbook = path.join(root, 'data/sweetmeta_reviewed_20261005/compound_master_1296.csv');
const workbookPath = path.resolve(process.argv[2] ?? defaultWorkbook);
const pubchemPath = process.argv[3] ? path.resolve(process.argv[3]) : null;
const outputDir = path.join(root, 'frontend-react/src/features/database/data');

const workbook = XLSX.readFile(workbookPath, { cellDates: false });
const sheetName = workbook.SheetNames[0];
const sourceRows = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { defval: null });
const existingDatabasePath = path.join(outputDir, 'database.generated.json');
let existingCompounds = fs.existsSync(existingDatabasePath)
  ? JSON.parse(fs.readFileSync(existingDatabasePath, 'utf8')).compounds ?? [] : [];
if (!existingCompounds.some((compound) => compound.pubchem?.cid)) {
  try {
    const repositoryPath = 'frontend-react/src/features/database/data/database.generated.json';
    existingCompounds = JSON.parse(execFileSync('git', ['show', `HEAD:${repositoryPath}`], { cwd: root, encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 })).compounds ?? [];
  } catch {
    // A first build may not have a historical snapshot; reviewed core data still builds without enrichment.
  }
}
const existingById = new Map(existingCompounds.map((compound) => [compound.id, compound]));

const readRelatedCsv = (name) => {
  const file = path.join(path.dirname(workbookPath), name);
  if (!fs.existsSync(file)) return new Map();
  const book = XLSX.readFile(file, { cellDates: false });
  const rows = XLSX.utils.sheet_to_json(book.Sheets[book.SheetNames[0]], { defval: null });
  return new Map(rows.map((row) => [String(row.compound_id), row]));
};
const taxonomyById = readRelatedCsv('sweetclass_taxonomy_1296.csv');
const provenanceById = readRelatedCsv('compound_provenance_1296.csv');
const propertiesById = readRelatedCsv('physicochemical_descriptors_1296.csv');

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
const dateText = (value) => typeof value === 'number'
  ? new Date(Date.UTC(1899, 11, 30) + value * 86_400_000).toISOString()
  : text(value);

const compounds = sourceRows.map((row) => {
  const existing = existingById.get(text(row.compound_id)) ?? {};
  const taxonomy = taxonomyById.get(text(row.compound_id)) ?? {};
  const provenance = provenanceById.get(text(row.compound_id)) ?? {};
  const properties = propertiesById.get(text(row.compound_id)) ?? {};
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
  const chemblId = text(row.chembl_id);

  return {
    id: text(row.compound_id),
    entityType: 'small-molecule',
    name: text(row.preferred_name),
    nameSource: text(row.preferred_name_source) ?? existing.nameSource ?? 'reviewed master 2026-10-05',
    inchiKey,
    canonicalTautomerInchiKey: text(row.canonical_tautomer_inchikey) ?? existing.canonicalTautomerInchiKey ?? null,
    isomericSmiles: text(row.parent_isomeric_smiles),
    canonicalSmiles: text(row.parent_canonical_smiles),
    formula: text(row.molecular_formula),
    molecularWeight: sourceMw,
    formalCharge: number(row.formal_charge) ?? existing.formalCharge ?? null,
    heavyAtomCount: number(properties.heavy_atom_count) ?? existing.heavyAtomCount ?? null,
    createdAt: text(row.created_at) ?? existing.createdAt ?? null,
    sweetClassLevel1: text(taxonomy.sweetclass_level1),
    sweetClassLevel2: text(taxonomy.sweetclass_level2),
    evidenceGrade: text(provenance.evidence_short),
    sourceCollection: text(provenance.source_collection),
    reviewedSourceNames: text(provenance.source_names)?.split(';') ?? [],
    reviewedProperties: {
      clogp: number(properties.clogp), tpsa: number(properties.tpsa),
      rotatableBonds: number(properties.rotatable_bonds), hba: number(properties.hba),
      hbd: number(properties.hbd),
    },
    evidence: {
      baselineTier: text(row.baseline_evidence_readiness_tier) ?? existing.evidence?.baselineTier ?? null,
      releaseTier: text(row.release_evidence_readiness_tier) ?? existing.evidence?.releaseTier ?? null,
      baselineGap: text(row.baseline_evidence_gap_type) ?? existing.evidence?.baselineGap ?? null,
      releaseGap: text(row.release_evidence_gap_type) ?? existing.evidence?.releaseGap ?? null,
      priorityScore: number(row.baseline_priority_score) ?? existing.evidence?.priorityScore ?? null,
      acceptedAssertions: number(row.accepted_sweet_assertion_count) ?? 0,
    },
    review: {
      required: row.manual_review_required === null || row.manual_review_required === undefined ? Boolean(existing.review?.required) : Number(row.manual_review_required) === 1,
      identityStatus: text(row.structure_identity_status) ?? existing.review?.identityStatus ?? null,
      note: text(row.status_note) ?? existing.review?.note ?? null,
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
    } : existing.pubchem ?? null,
    chembl: chemblId && text(row.chembl_match_status) === 'matched' ? {
      id: chemblId,
      matchStatus: 'matched',
      sourceUrl: text(row.chembl_source_url) ?? `https://www.ebi.ac.uk/chembl/explore/compound/${chemblId}`,
      retrievedAt: dateText(row.chembl_retrieved_at) ?? isoDate,
      matchMethod: 'exact_full_inchikey',
    } : existing.chembl ?? null,
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
const chemblMatched = compounds.filter((item) => item.chembl).length;

const metadata = {
  title: 'SweetMeta',
  version: 'SweetMeta v1.0.7 (2026-10-05 reviewed snapshot)',
  sourceWorkbook: path.basename(workbookPath),
  sourceSheet: sheetName,
  generatedAt: isoDate,
  reviewDate: '2026-10-05',
  totalRecords: compounds.length,
  currentEntityCoverage: { 'small-molecule': compounds.length, protein: 0, other: 0 },
  tierCounts: countBy(compounds, (item) => item.evidence.releaseTier),
  gapCounts: countBy(compounds, (item) => item.evidence.releaseGap),
  reviewRequired: reviewIds.length,
  acceptedAssertions: compounds.reduce((sum, item) => sum + item.evidence.acceptedAssertions, 0),
  pubchemMatched,
  pubchemVerified,
  chemblMatched,
};

const quality = {
  metadata,
  missing: {
    canonicalTautomerInchiKey: missingIds((item) => item.canonicalTautomerInchiKey),
    heavyAtomCount: missingIds((item) => item.heavyAtomCount),
    pubchemMatch: missingIds((item) => item.pubchem),
    chemblMatch: missingIds((item) => item.chembl),
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
console.log(JSON.stringify({ records: compounds.length, pubchemMatched, pubchemVerified, chemblMatched, reviewRequired: reviewIds.length }));
