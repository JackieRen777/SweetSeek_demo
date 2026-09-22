import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import * as XLSX from '../../frontend-react/node_modules/xlsx/xlsx.mjs';

const root = path.resolve(import.meta.dirname, '../..');
const workbookPath = path.resolve(process.argv[2] ?? path.join(root, 'data/sweet_database_source_20260910.xlsx'));
const cachePath = path.resolve(process.argv[3] ?? path.join(root, 'data/chembl_exact_20260916.json'));
const chemblScript = '/Users/jackieren/.codex/plugins/cache/openai-api-curated/life-science-research/1dc19589/skills/chembl-skill/scripts/rest_request.py';
const concurrency = Math.max(1, Math.min(8, Number(process.env.CHEMBL_CONCURRENCY ?? 6)));

XLSX.set_fs(fs);
const workbook = XLSX.readFile(workbookPath, { cellDates: false });
const sheet = workbook.Sheets[workbook.SheetNames[0]];
const rows = XLSX.utils.sheet_to_json(sheet, { defval: null });
const keys = [...new Set(rows.map((row) => row.parent_inchikey).filter((key) => typeof key === 'string' && /^[A-Z]{14}-[A-Z]{10}-[A-Z]$/.test(key)))];
const cache = fs.existsSync(cachePath) ? JSON.parse(fs.readFileSync(cachePath, 'utf8')) : {
  metadata: { sourceWorkbook: path.basename(workbookPath), retrievedAt: null, matchPolicy: 'unique exact full InChIKey' },
  results: {},
};

const request = (inchiKey) => new Promise((resolve, reject) => {
  const payload = {
    base_url: 'https://www.ebi.ac.uk/chembl/api/data',
    path: 'molecule.json',
    params: {
      molecule_structures__standard_inchi_key: inchiKey,
      only: 'molecule_chembl_id,molecule_structures',
      limit: 10,
    },
    record_path: 'molecules',
    max_items: 10,
    timeout_sec: 30,
  };
  const child = spawn('python', [chemblScript], { stdio: ['pipe', 'pipe', 'pipe'] });
  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (chunk) => { stdout += chunk; });
  child.stderr.on('data', (chunk) => { stderr += chunk; });
  child.on('error', reject);
  child.on('close', (code) => {
    if (code !== 0) return reject(new Error(stderr || `ChEMBL helper exited ${code}`));
    try { resolve(JSON.parse(stdout)); } catch { reject(new Error(`Invalid ChEMBL response: ${stdout.slice(0, 300)}`)); }
  });
  child.stdin.end(JSON.stringify(payload));
});

const save = () => {
  cache.metadata.retrievedAt = new Date().toISOString();
  fs.writeFileSync(cachePath, `${JSON.stringify(cache, null, 2)}\n`);
};

const pending = keys.filter((key) => !cache.results[key] || cache.results[key].status === 'error');
let completed = 0;
let cursor = 0;
async function worker() {
  while (cursor < pending.length) {
    const index = cursor++;
    const inchiKey = pending[index];
    try {
      let response;
      for (let attempt = 1; attempt <= 3; attempt += 1) {
        try { response = await request(inchiKey); break; } catch (error) {
          if (attempt === 3) throw error;
          await new Promise((resolve) => setTimeout(resolve, attempt * 700));
        }
      }
      if (!response?.ok) throw new Error(response?.error?.message ?? 'ChEMBL request failed');
      const exact = (response.records ?? []).filter((record) => record?.molecule_structures?.standard_inchi_key === inchiKey);
      cache.results[inchiKey] = exact.length === 1
        ? { status: 'matched', chemblId: exact[0].molecule_chembl_id, matchMethod: 'exact_full_inchikey' }
        : { status: exact.length === 0 ? 'not_found' : 'ambiguous', chemblId: null, matchMethod: 'exact_full_inchikey', exactMatchCount: exact.length };
    } catch (error) {
      cache.results[inchiKey] = { status: 'error', chemblId: null, matchMethod: 'exact_full_inchikey', error: String(error?.message ?? error) };
    }
    completed += 1;
    if (completed % 25 === 0 || completed === pending.length) {
      save();
      console.log(`ChEMBL ${completed}/${pending.length} (cached ${keys.length - pending.length})`);
    }
  }
}

await Promise.all(Array.from({ length: Math.min(concurrency, pending.length || 1) }, () => worker()));
save();
const summary = Object.values(cache.results).reduce((acc, result) => {
  acc[result.status] = (acc[result.status] ?? 0) + 1;
  return acc;
}, {});
console.log(JSON.stringify({ totalRows: rows.length, validUniqueKeys: keys.length, ...summary }));
