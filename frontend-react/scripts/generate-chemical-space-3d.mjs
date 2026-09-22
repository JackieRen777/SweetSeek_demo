import fs from 'node:fs';
import path from 'node:path';
import initRDKitModule from '@rdkit/rdkit';
import { UMAP } from 'umap-js';

const root = path.resolve(import.meta.dirname, '..');
const { compounds } = JSON.parse(fs.readFileSync(path.join(root, 'src/features/database/data/database.generated.json'), 'utf8'));
const rdkit = await initRDKitModule();
const included = [];
const options = JSON.stringify({ radius: 2, nBits: 2048 });
for (const compound of compounds) {
  const smiles = compound.isomericSmiles ?? compound.canonicalSmiles;
  if (!smiles) continue;
  let molecule;
  try {
    molecule = rdkit.get_mol(smiles);
    if (molecule?.is_valid()) included.push({ id: compound.id, fingerprint: molecule.get_morgan_fp_as_uint8array(options) });
  } catch {
    // Invalid structures remain excluded as in the 2D release.
  } finally {
    molecule?.delete();
  }
}

const popcount = Uint8Array.from({ length: 256 }, (_, value) => {
  let count = 0;
  while (value) { value &= value - 1; count += 1; }
  return count;
});
const distanceFn = (left, right) => {
  let intersection = 0;
  let union = 0;
  for (let index = 0; index < left.length; index += 1) {
    intersection += popcount[left[index] & right[index]];
    union += popcount[left[index] | right[index]];
  }
  return union === 0 ? 0 : 1 - intersection / union;
};
let state = 42;
const random = () => {
  state |= 0;
  state = state + 0x6D2B79F5 | 0;
  let value = Math.imul(state ^ state >>> 15, 1 | state);
  value = value + Math.imul(value ^ value >>> 7, 61 | value) ^ value;
  return ((value ^ value >>> 14) >>> 0) / 4294967296;
};
const embedding = new UMAP({ nComponents: 3, nNeighbors: 20, minDist: 0.12, spread: 1, random, distanceFn })
  .fit(included.map((record) => record.fingerprint));
const axes = [0, 1, 2].map((axis) => {
  const values = embedding.map((point) => point[axis]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  return values.map((value) => Number(((value - min) / (max - min || 1)).toFixed(6)));
});
const output = {
  metadata: { method: 'UMAP', dimensions: 3, fingerprint: 'Morgan / ECFP4 (radius 2, 2048 bits)', distance: 'Tanimoto distance', parameters: { nNeighbors: 20, minDist: 0.12, spread: 1, randomSeed: 42 }, mappedRecordCount: included.length },
  points: included.map((record, index) => ({ id: record.id, x: axes[0][index], y: axes[1][index], z: axes[2][index] })),
};
fs.writeFileSync(path.join(root, 'public/database-data/chemical-space-3d.json'), `${JSON.stringify(output)}\n`);
console.log(`Wrote ${included.length} 3D UMAP points`);
