import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import * as XLSX from '../../frontend-react/node_modules/xlsx/xlsx.mjs';

const root = path.resolve(import.meta.dirname, '../..');
const sourceWorkbook = path.resolve(process.argv[2] ?? path.join(root, 'outputs/sweetmeta-chembl-20260916/sweet_database_source_20260910_chembl_enriched.xlsx'));
const outputDirectory = path.resolve(process.argv[3] ?? path.join(root, 'outputs/sweetmeta-name-normalization'));
const cacheDirectory = path.join(outputDirectory, 'cache');
const rawDirectory = path.join(cacheDirectory, 'raw');
const pluginRoot = '/Users/jackieren/.codex/plugins/cache/openai-api-curated/life-science-research/1dc19589/skills';
const helpers = {
  pubchem: path.join(pluginRoot, 'pubchem-pug-skill/scripts/rest_request.py'),
  chebi: path.join(pluginRoot, 'chebi-skill/scripts/rest_request.py'),
  chembl: path.join(pluginRoot, 'chembl-skill/scripts/rest_request.py'),
};
const concurrency = Math.max(1, Math.min(8, Number(process.env.NAME_NORMALIZATION_CONCURRENCY ?? 6)));
const online = process.env.NAME_NORMALIZATION_OFFLINE !== '1';

fs.mkdirSync(rawDirectory, { recursive: true });
XLSX.set_fs(fs);
const workbook = XLSX.readFile(sourceWorkbook, { cellDates: false });
const sheetName = workbook.SheetNames.find((name) => name === 'current_sweet_compounds_1296') ?? workbook.SheetNames[0];
const rows = XLSX.utils.sheet_to_json(workbook.Sheets[sheetName], { defval: null });
const existingPubchem = JSON.parse(fs.readFileSync(path.join(root, 'data/pubchem_enrichment_20260910.json'), 'utf8')).records ?? [];
const existingChembl = JSON.parse(fs.readFileSync(path.join(root, 'data/chembl_exact_20260916.json'), 'utf8'));
const literaturePath = path.join(root, 'frontend-react/public/database-data/literature.generated.json');
const literature = fs.existsSync(literaturePath)
  ? JSON.parse(fs.readFileSync(literaturePath, 'utf8'))
  : { metadata: {}, papers: {}, links: [] };
const pubchemByKey = new Map(existingPubchem.map((record) => [record.InChIKey, record]));

const cachePaths = Object.fromEntries(['pubchem', 'pubchemSynonyms', 'chebi', 'chembl'].map((source) => [source, path.join(cacheDirectory, source + '-names.json')]));
const caches = Object.fromEntries(Object.entries(cachePaths).map(([source, file]) => [source, fs.existsSync(file)
  ? JSON.parse(fs.readFileSync(file, 'utf8'))
  : { metadata: { source, createdAt: new Date().toISOString() }, results: {} }]));
const saveCache = (source) => {
  caches[source].metadata.updatedAt = new Date().toISOString();
  fs.writeFileSync(cachePaths[source], JSON.stringify(caches[source], null, 2) + '\n');
};

const request = (source, payload) => new Promise((resolve, reject) => {
  const child = spawn('python', [helpers[source]], { stdio: ['pipe', 'pipe', 'pipe'] });
  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (chunk) => { stdout += chunk; });
  child.stderr.on('data', (chunk) => { stderr += chunk; });
  child.on('error', reject);
  child.on('close', (code) => {
    if (code !== 0) return reject(new Error(stderr || stdout || 'Helper failed'));
    try { resolve(JSON.parse(stdout)); } catch { reject(new Error('Invalid helper response: ' + stdout.slice(0, 300))); }
  });
  child.stdin.end(JSON.stringify(payload));
});
const retry = async (callback) => {
  let lastError;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try { return await callback(); } catch (error) {
      lastError = error;
      if (attempt < 3) await new Promise((resolve) => setTimeout(resolve, attempt * 750));
    }
  }
  throw lastError;
};
async function runWorkers(items, source, callback) {
  let cursor = 0;
  let completed = 0;
  async function worker() {
    while (cursor < items.length) {
      const item = items[cursor++];
      await callback(item);
      completed += 1;
      if (completed % 25 === 0 || completed === items.length) {
        saveCache(source);
        console.log(source + ' ' + completed + '/' + items.length);
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length || 1) }, () => worker()));
}

const clean = (value) => String(value ?? '').normalize('NFKC').replace(/[‐‑‒–—−]/g, '-').replace(/\s+/g, ' ').trim();
const nameKey = (value) => clean(value).toLocaleLowerCase('en').replace(/[\s_-]+/g, ' ').replace(/[^\p{L}\p{N}]+/gu, '').trim();
const formulaKey = (value) => clean(value).replace(/\s+/g, '');
const unique = (values) => [...new Set(values.map(clean).filter(Boolean))];
const searchName = (value) => clean(value).replace(/_/g, ' ').replace(/^\([^)]*[+-][^)]*\)\s*/, '').slice(0, 180);
const stereoClaim = (name) => /\(\s*[+-]\s*\)|\b(?:\d+[RS](?:,\s*\d+[RS])*)\b|\([EZ]\)|\b(?:alpha|beta|cis|trans)\b|[αβ]/i.test(name);
const stereoUndefined = (key) => /-UHFFFAOYSA-/.test(key ?? '');
const saltPattern = /\b(?:monosodium|disodium|trisodium|sodium|monopotassium|dipotassium|potassium|calcium|magnesium|ammonium|hydrochloride|salt|hydrate|solvate)\b/i;
const internalPattern = /^(?:asp|p)\s*\d+$|\b(?:isomer\s+[ivx]+|analogue\s+\d+|analog\s+\d+)\b|^[A-Z]{1,4}\d+[a-z]?$/i;

if (rows.some((row) => !/^[A-Z]{14}-[A-Z]{10}-[A-Z]$/.test(row.parent_inchikey ?? ''))) {
  throw new Error('Every source record must have a valid full InChIKey.');
}

if (online) {
  const pending = rows.filter((row) => !caches.pubchem.results[row.parent_inchikey]);
  const batches = Array.from({ length: Math.ceil(pending.length / 50) }, (_, index) => pending.slice(index * 50, index * 50 + 50));
  await runWorkers(batches, 'pubchem', async (batch) => {
    const rawFile = path.join(rawDirectory, 'pubchem-' + batch[0].parent_inchikey.slice(0, 14) + '.json');
    try {
      const response = await retry(() => request('pubchem', {
        base_url: 'https://pubchem.ncbi.nlm.nih.gov/rest/pug',
        path: 'compound/inchikey/property/Title,IUPACName,IsomericSMILES,CanonicalSMILES,InChIKey,MolecularFormula/JSON',
        method: 'POST',
        form_body: { inchikey: batch.map((row) => row.parent_inchikey).join(',') },
        record_path: 'PropertyTable.Properties',
        max_items: 500,
        max_depth: 8,
        timeout_sec: 60,
        save_raw: true,
        raw_output_path: rawFile,
      }));
      if (!response.ok) throw new Error(response.error?.message ?? 'PubChem request failed');
      const records = JSON.parse(fs.readFileSync(rawFile, 'utf8'))?.PropertyTable?.Properties ?? [];
      for (const row of batch) {
        const candidates = records.filter((record) => record.InChIKey === row.parent_inchikey);
        const existing = pubchemByKey.get(row.parent_inchikey);
        const selectedByCid = candidates.find((record) => Number(record.CID) === Number(existing?.CID));
        const formulaMatches = candidates.filter((record) => formulaKey(record.MolecularFormula) === formulaKey(row.molecular_formula));
        const selected = selectedByCid ?? (formulaMatches.length === 1 ? formulaMatches[0] : null);
        caches.pubchem.results[row.parent_inchikey] = {
          status: selected ? 'matched' : candidates.length ? 'ambiguous' : 'not_found',
          queriedAt: new Date().toISOString(),
          queryKey: row.parent_inchikey,
          candidateCount: candidates.length,
          selected: selected ?? null,
          candidates,
          rawFile: path.relative(outputDirectory, rawFile),
        };
      }
    } catch (error) {
      for (const row of batch) caches.pubchem.results[row.parent_inchikey] = {
        status: 'error', queriedAt: new Date().toISOString(), queryKey: row.parent_inchikey, error: String(error?.message ?? error),
      };
    }
  });

  const synonymRows = rows.filter((row) => {
    const match = caches.pubchem.results[row.parent_inchikey];
    return match?.status === 'matched' && match.selected?.CID && !caches.pubchemSynonyms.results[row.parent_inchikey];
  });
  await runWorkers(synonymRows, 'pubchemSynonyms', async (row) => {
    const match = caches.pubchem.results[row.parent_inchikey];
    const cid = match.selected.CID;
    const rawFile = path.join(rawDirectory, 'pubchem-synonyms-' + cid + '.json');
    try {
      const response = await request('pubchem', {
        base_url: 'https://pubchem.ncbi.nlm.nih.gov/rest/pug',
        path: 'compound/cid/' + cid + '/synonyms/JSON',
        record_path: 'InformationList.Information',
        max_items: 2,
        max_depth: 8,
        timeout_sec: 30,
        save_raw: true,
        raw_output_path: rawFile,
      });
      if (!response.ok) throw new Error(response.error?.message ?? 'PubChem synonym request failed');
      const record = JSON.parse(fs.readFileSync(rawFile, 'utf8'))?.InformationList?.Information?.[0];
      caches.pubchemSynonyms.results[row.parent_inchikey] = {
        status: Array.isArray(record?.Synonym) ? 'matched' : 'not_found',
        queriedAt: new Date().toISOString(),
        queryKey: row.parent_inchikey,
        cid,
        synonyms: Array.isArray(record?.Synonym) ? record.Synonym.slice(0, 50) : [],
        rawFile: path.relative(outputDirectory, rawFile),
      };
    } catch (error) {
      caches.pubchemSynonyms.results[row.parent_inchikey] = {
        status: 'not_found', queriedAt: new Date().toISOString(), queryKey: row.parent_inchikey, cid, synonyms: [],
        error: String(error?.message ?? error),
      };
    }
  });

  const chemblRows = rows.filter((row) => existingChembl.results[row.parent_inchikey]?.status === 'matched' && !caches.chembl.results[row.parent_inchikey]);
  await runWorkers(chemblRows, 'chembl', async (row) => {
    const chemblId = existingChembl.results[row.parent_inchikey].chemblId;
    const rawFile = path.join(rawDirectory, 'chembl-' + chemblId + '.json');
    try {
      const response = await retry(() => request('chembl', {
        base_url: 'https://www.ebi.ac.uk/chembl/api/data',
        path: 'molecule/' + chemblId + '.json',
        max_depth: 10,
        timeout_sec: 45,
        save_raw: true,
        raw_output_path: rawFile,
      }));
      if (!response.ok) throw new Error(response.error?.message ?? 'ChEMBL request failed');
      const record = JSON.parse(fs.readFileSync(rawFile, 'utf8'));
      const exact = record?.molecule_structures?.standard_inchi_key === row.parent_inchikey;
      caches.chembl.results[row.parent_inchikey] = {
        status: exact ? 'matched' : 'identity_conflict',
        queriedAt: new Date().toISOString(),
        queryKey: row.parent_inchikey,
        chemblId,
        prefName: record?.pref_name ?? null,
        moleculeType: record?.molecule_type ?? null,
        parentChemblId: record?.molecule_hierarchy?.parent_chembl_id ?? null,
        rawFile: path.relative(outputDirectory, rawFile),
      };
    } catch (error) {
      caches.chembl.results[row.parent_inchikey] = {
        status: 'error', queriedAt: new Date().toISOString(), queryKey: row.parent_inchikey, chemblId, error: String(error?.message ?? error),
      };
    }
  });

  const chebiRows = rows.filter((row) => !caches.chebi.results[row.parent_inchikey]);
  await runWorkers(chebiRows, 'chebi', async (row) => {
    try {
      const query = searchName(row.preferred_name);
      const response = await retry(() => request('chebi', {
        base_url: 'https://www.ebi.ac.uk',
        path: 'chebi/backend/api/public/es_search/',
        params: { query, size: 20 },
        record_path: 'results',
        max_items: 20,
        max_depth: 8,
        timeout_sec: 45,
      }));
      if (!response.ok) throw new Error(response.error?.message ?? 'ChEBI request failed');
      const exact = (response.records ?? []).map((item) => item?._source ?? item).filter((item) => item?.inchikey === row.parent_inchikey);
      caches.chebi.results[row.parent_inchikey] = {
        status: exact.length === 1 ? 'matched' : exact.length > 1 ? 'ambiguous' : 'not_found',
        queriedAt: new Date().toISOString(),
        queryKey: row.parent_inchikey,
        queryText: query,
        candidateCount: exact.length,
        selected: exact.length === 1 ? {
          chebiId: exact[0].chebi_accession, name: exact[0].name, asciiName: exact[0].ascii_name,
          formula: exact[0].formula, smiles: exact[0].smiles, inchiKey: exact[0].inchikey, stars: exact[0].stars,
        } : null,
      };
    } catch (error) {
      caches.chebi.results[row.parent_inchikey] = {
        status: 'error', queriedAt: new Date().toISOString(), queryKey: row.parent_inchikey, error: String(error?.message ?? error),
      };
    }
  });
}

for (const source of Object.keys(caches)) saveCache(source);

const groups = new Map();
for (const row of rows) {
  const key = nameKey(row.preferred_name);
  if (!groups.has(key)) groups.set(key, []);
  groups.get(key).push(row);
}
const duplicateGroups = [...groups.entries()].filter(([, group]) => group.length > 1);
const duplicateById = new Map();
for (const [key, group] of duplicateGroups) {
  const fullKeys = new Set(group.map((row) => row.parent_inchikey));
  const connectivity = new Set(group.map((row) => row.parent_inchikey.slice(0, 14)));
  const classification = fullKeys.size === 1 ? 'exact_duplicate_name_and_identity'
    : connectivity.size === 1 ? 'same_connectivity_different_stereo_or_protonation' : 'same_name_different_identity';
  for (const row of group) duplicateById.set(row.compound_id, {
    key, size: group.length, classification, members: group.map((item) => item.compound_id),
  });
}

const normalized = rows.map((row) => {
  const key = row.parent_inchikey;
  const pubchem = caches.pubchem.results[key] ?? { status: 'not_queried' };
  const pubchemSynonyms = caches.pubchemSynonyms.results[key] ?? { status: 'not_queried', synonyms: [] };
  const chebi = caches.chebi.results[key] ?? { status: 'not_queried' };
  const chembl = caches.chembl.results[key]
    ?? (existingChembl.results[key]?.status === 'not_found' ? { status: 'not_found' } : { status: 'not_queried' });
  const sourceName = clean(row.preferred_name);
  const cleanedSourceName = clean(sourceName.replace(/_/g, ' '));
  const stereoConflict = stereoClaim(sourceName) && stereoUndefined(key);
  const duplicate = duplicateById.get(row.compound_id) ?? null;
  const saltClaim = saltPattern.test(sourceName);
  const structureSalt = /\./.test(row.parent_isomeric_smiles ?? row.parent_canonical_smiles ?? '');
  const saltConflict = saltClaim && !structureSalt;
  const reasons = [];
  if (stereoConflict) reasons.push('name_claims_stereochemistry_but_structure_is_undefined');
  if (saltConflict) reasons.push('name_claims_salt_but_structure_has_no_separate_counterion');
  if (duplicate) reasons.push(duplicate.classification);
  if (pubchem.status === 'ambiguous' || chebi.status === 'ambiguous' || chembl.status === 'identity_conflict') {
    reasons.push('external_database_identity_or_representation_conflict');
  }
  if (internalPattern.test(sourceName)) reasons.push('internal_or_dataset_style_name');
  if (sourceName.includes('_')) reasons.push('source_name_contains_underscore');
  if (sourceName.length > 100) reasons.push('source_name_over_100_characters');

  const candidates = [
    chebi.status === 'matched' ? { name: chebi.selected.name, source: 'ChEBI recommended name', id: chebi.selected.chebiId } : null,
    pubchem.status === 'matched' ? { name: pubchem.selected.Title, source: 'PubChem Title', id: pubchem.selected.CID } : null,
    chembl.status === 'matched' && chembl.prefName ? { name: chembl.prefName, source: 'ChEMBL pref_name', id: chembl.chemblId } : null,
    { name: cleanedSourceName, source: row.preferred_name_source ?? 'source workbook', id: row.compound_id },
    pubchem.status === 'matched' ? { name: pubchem.selected.IUPACName, source: 'PubChem IUPAC name', id: pubchem.selected.CID } : null,
  ].filter((candidate) => candidate?.name);
  const selected = candidates[0] ?? null;
  const exactExternal = pubchem.status === 'matched' || chebi.status === 'matched' || chembl.status === 'matched';
  const status = reasons.length ? 'manual_review' : selected && exactExternal ? 'verified' : 'unresolved';
  const synonyms = unique([
    sourceName, cleanedSourceName, pubchem.selected?.Title, pubchem.selected?.IUPACName,
    chebi.selected?.name, chebi.selected?.asciiName, chembl.prefName, ...(pubchemSynonyms.synonyms ?? []),
  ]).filter((name) => nameKey(name) !== nameKey(selected?.name));
  const timestamps = [pubchem.queriedAt, chebi.queriedAt, chembl.queriedAt].filter(Boolean).sort();
  return {
    compound_id: row.compound_id,
    full_inchikey: key,
    connectivity_inchikey: key.slice(0, 14),
    molecular_formula: row.molecular_formula,
    isomeric_smiles: row.parent_isomeric_smiles,
    source_name: sourceName,
    preferred_name_candidate: selected?.name ?? sourceName,
    systematic_name: pubchem.selected?.IUPACName ?? null,
    synonyms: synonyms.join(' | '),
    name_source: selected?.source ?? row.preferred_name_source,
    source_external_id: selected?.id ?? row.compound_id,
    name_status: status,
    stereo_status: stereoConflict ? 'conflicting' : stereoUndefined(key) ? 'undefined' : 'defined_or_partial',
    salt_form: saltConflict ? 'conflicting' : saltClaim || structureSalt ? 'salt_or_multicomponent' : 'parent_or_neutral',
    review_reason: unique(reasons).join(' | '),
    duplicate_group: duplicate?.key ?? null,
    duplicate_classification: duplicate?.classification ?? null,
    pubchem_status: pubchem.status,
    pubchem_cid: pubchem.selected?.CID ?? null,
    pubchem_title: pubchem.selected?.Title ?? null,
    pubchem_iupac_name: pubchem.selected?.IUPACName ?? null,
    pubchem_candidate_count: pubchem.candidateCount ?? 0,
    pubchem_synonym_status: pubchemSynonyms.status,
    pubchem_synonym_count: pubchemSynonyms.synonyms?.length ?? 0,
    chebi_status: chebi.status,
    chebi_id: chebi.selected?.chebiId ?? null,
    chebi_name: chebi.selected?.name ?? null,
    chembl_status: chembl.status,
    chembl_id: chembl.chemblId ?? row.chembl_id ?? null,
    chembl_pref_name: chembl.prefName ?? null,
    query_timestamp: timestamps.at(-1) ?? null,
    review_decision: '',
    reviewer_edit: '',
    reviewer_note: '',
  };
});

const authorityEvidence = normalized.flatMap((row) => [
  { compound_id: row.compound_id, source: 'PubChem', query_key: row.full_inchikey, status: row.pubchem_status, external_id: row.pubchem_cid, preferred_name: row.pubchem_title, systematic_name: row.pubchem_iupac_name, source_url: row.pubchem_cid ? 'https://pubchem.ncbi.nlm.nih.gov/compound/' + row.pubchem_cid : '', queried_at: row.query_timestamp },
  { compound_id: row.compound_id, source: 'ChEBI', query_key: row.full_inchikey, status: row.chebi_status, external_id: row.chebi_id, preferred_name: row.chebi_name, systematic_name: '', source_url: row.chebi_id ? 'https://www.ebi.ac.uk/chebi/searchId.do?chebiId=' + row.chebi_id : '', queried_at: row.query_timestamp },
  { compound_id: row.compound_id, source: 'ChEMBL', query_key: row.full_inchikey, status: row.chembl_status, external_id: row.chembl_id, preferred_name: row.chembl_pref_name, systematic_name: '', source_url: row.chembl_id ? 'https://www.ebi.ac.uk/chembl/explore/compound/' + row.chembl_id : '', queried_at: row.query_timestamp },
]);
const reviewStatusByCompound = new Map(normalized.map((row) => [row.compound_id, row.name_status]));
const literatureEvidence = (literature.links ?? []).flatMap((link) => {
  if (reviewStatusByCompound.get(link.compoundId) === 'verified') return [];
  const paper = literature.papers?.[link.paperId];
  if (!paper) return [];
  return [{
    compound_id: link.compoundId,
    source: 'SweetSeek local literature',
    query_key: link.matchedAlias ?? '',
    status: link.reviewStatus,
    external_id: link.paperId,
    preferred_name: link.matchedAlias ?? '',
    systematic_name: '',
    source_url: paper.doi ? 'https://doi.org/' + paper.doi : paper.pmid ? 'https://pubmed.ncbi.nlm.nih.gov/' + paper.pmid + '/' : '',
    queried_at: literature.metadata?.generatedAt ?? null,
    doi: paper.doi ?? '',
    pmid: paper.pmid ?? '',
    evidence_excerpt: link.evidenceExcerpt ?? '',
    page_number: link.pageNumber ?? '',
    match_method: link.matchMethod ?? '',
  }];
});
const sourceEvidence = [...authorityEvidence, ...literatureEvidence];
const changeLog = normalized.map((row) => ({
  compound_id: row.compound_id,
  field_name: 'preferred_name',
  original_value: row.source_name,
  candidate_value: row.preferred_name_candidate,
  changed: nameKey(row.source_name) !== nameKey(row.preferred_name_candidate) ? 'yes' : 'no',
  decision: '',
  evidence_source: row.name_source,
  review_status: row.name_status,
  review_note: '',
}));
const duplicateRows = duplicateGroups.flatMap(([groupKey, group]) => group.map((row) => ({
  duplicate_group: groupKey,
  classification: duplicateById.get(row.compound_id).classification,
  group_size: group.length,
  compound_id: row.compound_id,
  source_name: row.preferred_name,
  full_inchikey: row.parent_inchikey,
  connectivity_inchikey: row.parent_inchikey.slice(0, 14),
  molecular_formula: row.molecular_formula,
})));

const artifact = {
  metadata: {
    generatedAt: new Date().toISOString(),
    sourceWorkbook: path.basename(sourceWorkbook),
    sourceSheet: sheetName,
    recordCount: rows.length,
    policy: 'Exact full-InChIKey identity; no fuzzy-name auto-acceptance; source workbook is unchanged.',
  },
  normalized,
  stereoConflicts: normalized.filter((row) => row.stereo_status === 'conflicting'),
  saltParentConflicts: normalized.filter((row) => row.salt_form === 'conflicting'),
  duplicateNames: duplicateRows,
  unresolved: normalized.filter((row) => row.name_status === 'unresolved' || row.name_status === 'manual_review'),
  sourceEvidence,
  changeLog,
};
fs.writeFileSync(path.join(outputDirectory, 'name-normalization-audit.json'), JSON.stringify(artifact, null, 2) + '\n');
const statusCounts = normalized.reduce((acc, row) => {
  acc[row.name_status] = (acc[row.name_status] ?? 0) + 1;
  return acc;
}, {});
console.log(JSON.stringify({
  records: rows.length,
  statuses: statusCounts,
  stereoConflicts: artifact.stereoConflicts.length,
  saltParentConflicts: artifact.saltParentConflicts.length,
  duplicateGroups: duplicateGroups.length,
  duplicateRecords: duplicateRows.length,
}, null, 2));
