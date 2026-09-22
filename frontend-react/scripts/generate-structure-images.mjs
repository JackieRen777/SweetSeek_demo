import fs from 'node:fs';
import path from 'node:path';
import initRDKitModule from '@rdkit/rdkit';

const root = path.resolve(import.meta.dirname, '..');
const dataPath = path.join(root, 'src/features/database/data/database.generated.json');
const outputDirectory = path.join(root, 'public/database-data/structures-2d');
const { compounds } = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

fs.mkdirSync(outputDirectory, { recursive: true });
const rdkit = await initRDKitModule();
let generated = 0;
let excluded = 0;

for (const compound of compounds) {
  const smiles = compound.pubchem?.smiles ?? compound.isomericSmiles ?? compound.canonicalSmiles;
  if (!smiles || !/^[A-Za-z0-9_-]+$/.test(compound.id)) {
    excluded += 1;
    continue;
  }

  let molecule;
  try {
    molecule = rdkit.get_mol(smiles);
    if (!molecule?.is_valid()) throw new Error('RDKit could not parse the structure');
    const svg = molecule.get_svg(500, 500).replace("encoding='iso-8859-1'", "encoding='UTF-8'");
    fs.writeFileSync(path.join(outputDirectory, `${compound.id}.svg`), svg);
    generated += 1;
  } catch {
    excluded += 1;
  } finally {
    molecule?.delete();
  }
}

console.log(`Wrote ${generated} local 2D structure SVGs; excluded ${excluded}.`);
