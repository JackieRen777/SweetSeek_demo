import fs from 'node:fs';
import path from 'node:path';

const repoRoot = path.resolve(import.meta.dirname, '..');
const fingerprintPath = process.argv[2];

if (!fingerprintPath) {
  throw new Error('Usage: node scripts/generate_chemical_space.mjs <pubchem-fingerprint-json>');
}

const compounds = JSON.parse(fs.readFileSync(path.join(repoRoot, 'frontend-react/src/features/database/data/compounds.json'), 'utf8'));
const payload = JSON.parse(fs.readFileSync(fingerprintPath, 'utf8'));
const records = payload?.PropertyTable?.Properties;
if (!Array.isArray(records) || records.length < 3) throw new Error('No PubChem fingerprints found');

const bytesByCid = new Map(records.map((record) => {
  const bytes = Buffer.from(record.Fingerprint2D, 'base64');
  return [Number(record.CID), bytes.subarray(4)]; // PubChem prefixes the 881-bit length header.
}));

const included = compounds.filter((compound) => bytesByCid.has(compound.cid));
const popcount = (byte) => {
  let value = byte;
  let count = 0;
  while (value) { value &= value - 1; count += 1; }
  return count;
};
const tanimotoDistance = (left, right) => {
  let intersection = 0;
  let union = 0;
  for (let i = 0; i < Math.max(left.length, right.length); i += 1) {
    const a = left[i] ?? 0;
    const b = right[i] ?? 0;
    intersection += popcount(a & b);
    union += popcount(a | b);
  }
  return union ? 1 - intersection / union : 0;
};

const distances = included.map((left) => included.map((right) =>
  tanimotoDistance(bytesByCid.get(left.cid), bytesByCid.get(right.cid))));

// Deterministic SMACOF metric MDS. It preserves fingerprint distance without
// introducing the cluster exaggeration and random instability of small-n t-SNE.
let positions = included.map((compound, index) => {
  const angle = index * 2.399963229728653;
  const radius = 1 + ((compound.cid % 997) / 997) * 0.3;
  return [Math.cos(angle) * radius, Math.sin(angle) * radius];
});

for (let iteration = 0; iteration < 500; iteration += 1) {
  const next = positions.map(() => [0, 0]);
  for (let i = 0; i < included.length; i += 1) {
    for (let j = 0; j < included.length; j += 1) {
      if (i === j) continue;
      const dx = positions[i][0] - positions[j][0];
      const dy = positions[i][1] - positions[j][1];
      const current = Math.hypot(dx, dy) || 1e-9;
      const ratio = distances[i][j] / current;
      next[i][0] += positions[j][0] + ratio * dx;
      next[i][1] += positions[j][1] + ratio * dy;
    }
    next[i][0] /= included.length;
    next[i][1] /= included.length;
  }
  const meanX = next.reduce((sum, point) => sum + point[0], 0) / next.length;
  const meanY = next.reduce((sum, point) => sum + point[1], 0) / next.length;
  positions = next.map(([x, y]) => [x - meanX, y - meanY]);
}

const normalizeAxis = (axis) => {
  const values = positions.map((point) => point[axis]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  return values.map((value) => (value - min) / (max - min || 1));
};
const xs = normalizeAxis(0);
const ys = normalizeAxis(1);
const points = included.map((compound, index) => ({
  cid: compound.cid,
  x: Number(xs[index].toFixed(6)),
  y: Number(ys[index].toFixed(6)),
}));
const excluded = compounds.filter((compound) => !bytesByCid.has(compound.cid)).map((compound) => ({
  cid: compound.cid,
  name: compound.name,
  reason: String(compound.smiles).includes('Placeholder') ? 'No small-molecule structure' : 'PubChem fingerprint unavailable',
}));

const output = {
  metadata: {
    method: 'Deterministic metric MDS',
    distance: 'Tanimoto distance',
    fingerprint: 'PubChem CACTVS Substructure Fingerprint (881 bits)',
    source: 'PubChem PUG REST',
    sourceRecordCount: records.length,
    generatedAt: new Date().toISOString(),
  },
  points,
  excluded,
};

const outputPath = path.join(repoRoot, 'frontend-react/src/features/database/data/chemicalSpace.json');
fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`);
console.log(`Wrote ${points.length} chemical-space points; excluded ${excluded.length}.`);
