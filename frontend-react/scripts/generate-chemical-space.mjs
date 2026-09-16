import fs from 'node:fs';
import path from 'node:path';
import initRDKitModule from '@rdkit/rdkit';
import { UMAP } from 'umap-js';

const root = path.resolve(import.meta.dirname, '..');
const dataPath = path.join(root, 'src/features/database/data/database.generated.json');
const outputPath = path.join(root, 'src/features/database/data/chemicalSpace.json');
const { compounds } = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

const rdkit = await initRDKitModule();
const fingerprintOptions = JSON.stringify({ radius: 2, nBits: 2048 });
const included = [];
const excluded = [];

for (const compound of compounds) {
  const smiles = compound.isomericSmiles ?? compound.canonicalSmiles;
  if (!smiles) {
    excluded.push({ id: compound.id, name: compound.name, reason: 'Structure is not available' });
    continue;
  }

  let molecule;
  try {
    molecule = rdkit.get_mol(smiles);
    if (!molecule?.is_valid()) throw new Error('RDKit could not parse the structure');
    included.push({
      id: compound.id,
      fingerprint: molecule.get_morgan_fp_as_uint8array(fingerprintOptions),
    });
  } catch (error) {
    excluded.push({
      id: compound.id,
      name: compound.name,
      reason: error instanceof Error ? error.message : 'Fingerprint generation failed',
    });
  } finally {
    molecule?.delete();
  }
}

if (included.length < 3) throw new Error('Not enough valid structures for UMAP');

const bytePopcount = Uint8Array.from({ length: 256 }, (_, value) => {
  let current = value;
  let count = 0;
  while (current) {
    current &= current - 1;
    count += 1;
  }
  return count;
});

const tanimotoDistance = (left, right) => {
  let intersection = 0;
  let union = 0;
  for (let index = 0; index < left.length; index += 1) {
    intersection += bytePopcount[left[index] & right[index]];
    union += bytePopcount[left[index] | right[index]];
  }
  return union === 0 ? 0 : 1 - intersection / union;
};

const seededRandom = (seed) => {
  let state = seed;
  return () => {
    state |= 0;
    state = state + 0x6D2B79F5 | 0;
    let value = Math.imul(state ^ state >>> 15, 1 | state);
    value = value + Math.imul(value ^ value >>> 7, 61 | value) ^ value;
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
};

const parameters = {
  nComponents: 2,
  nNeighbors: 20,
  minDist: 0.12,
  spread: 1,
  random: seededRandom(42),
  distanceFn: tanimotoDistance,
};
const embedding = new UMAP(parameters).fit(included.map((record) => record.fingerprint));

const clusterCount = Math.min(8, included.length);
const recordCount = included.length;
const distances = new Float32Array(recordCount * recordCount);
const distanceSums = new Float64Array(recordCount);
const distanceAt = (left, right) => distances[left * recordCount + right];

for (let left = 0; left < recordCount; left += 1) {
  for (let right = left + 1; right < recordCount; right += 1) {
    const distance = tanimotoDistance(included[left].fingerprint, included[right].fingerprint);
    distances[left * recordCount + right] = distance;
    distances[right * recordCount + left] = distance;
    distanceSums[left] += distance;
    distanceSums[right] += distance;
  }
}

const medoids = [distanceSums.reduce((best, sum, index) => sum < distanceSums[best] ? index : best, 0)];
while (medoids.length < clusterCount) {
  let candidate = -1;
  let candidateDistance = -1;
  for (let index = 0; index < recordCount; index += 1) {
    if (medoids.includes(index)) continue;
    const nearestDistance = Math.min(...medoids.map((medoid) => distanceAt(index, medoid)));
    if (nearestDistance > candidateDistance) {
      candidate = index;
      candidateDistance = nearestDistance;
    }
  }
  medoids.push(candidate);
}

const assignClusters = () => Uint8Array.from({ length: recordCount }, (_, index) => {
  let nearestCluster = 0;
  let nearestDistance = distanceAt(index, medoids[0]);
  for (let cluster = 1; cluster < medoids.length; cluster += 1) {
    const distance = distanceAt(index, medoids[cluster]);
    if (distance < nearestDistance) {
      nearestCluster = cluster;
      nearestDistance = distance;
    }
  }
  return nearestCluster;
});

let assignments = assignClusters();
for (let iteration = 0; iteration < 20; iteration += 1) {
  const nextMedoids = medoids.map((medoid, cluster) => {
    const members = Array.from({ length: recordCount }, (_, index) => index)
      .filter((index) => assignments[index] === cluster);
    if (members.length === 0) return medoid;
    return members.reduce((best, candidate) => {
      const candidateSum = members.reduce((sum, member) => sum + distanceAt(candidate, member), 0);
      const bestSum = members.reduce((sum, member) => sum + distanceAt(best, member), 0);
      return candidateSum < bestSum ? candidate : best;
    }, members[0]);
  });
  if (nextMedoids.every((medoid, index) => medoid === medoids[index])) break;
  medoids.splice(0, medoids.length, ...nextMedoids);
  assignments = assignClusters();
}
assignments = assignClusters();

const compoundById = new Map(compounds.map((compound) => [compound.id, compound]));
const clusters = medoids.map((medoid, originalIndex) => ({
  originalIndex,
  medoid,
  size: assignments.reduce((count, assignment) => count + Number(assignment === originalIndex), 0),
})).sort((left, right) => right.size - left.size || left.medoid - right.medoid)
  .map((cluster, index) => ({
    id: `C${index + 1}`,
    label: `Cluster ${index + 1}`,
    size: cluster.size,
    medoidId: included[cluster.medoid].id,
    medoidName: compoundById.get(included[cluster.medoid].id)?.name ?? null,
    originalIndex: cluster.originalIndex,
  }));
const clusterIdByOriginalIndex = new Map(clusters.map((cluster) => [cluster.originalIndex, cluster.id]));

const normalizeAxis = (axis) => {
  const values = embedding.map((point) => point[axis]);
  const min = Math.min(...values);
  const max = Math.max(...values);
  return values.map((value) => (value - min) / (max - min || 1));
};
const xs = normalizeAxis(0);
const ys = normalizeAxis(1);

const output = {
  metadata: {
    method: 'UMAP',
    fingerprint: 'Morgan / ECFP4 (radius 2, 2048 bits)',
    distance: 'Tanimoto distance',
    implementation: `RDKit.js ${rdkit.version()} + umap-js 1.4.0`,
    sourceRecordCount: compounds.length,
    mappedRecordCount: included.length,
    parameters: { nNeighbors: 20, minDist: 0.12, spread: 1, randomSeed: 42 },
    clusterMethod: 'Deterministic k-medoids on ECFP4 Tanimoto distance',
    clusters: clusters.map(({ originalIndex: _originalIndex, ...cluster }) => cluster),
    generatedAt: new Date().toISOString(),
  },
  points: included.map((record, index) => ({
    id: record.id,
    x: Number(xs[index].toFixed(6)),
    y: Number(ys[index].toFixed(6)),
    cluster: clusterIdByOriginalIndex.get(assignments[index]),
  })),
  excluded,
};

fs.writeFileSync(outputPath, `${JSON.stringify(output, null, 2)}\n`);
console.log(`Wrote ${included.length} ECFP4 + UMAP points; excluded ${excluded.length}.`);
