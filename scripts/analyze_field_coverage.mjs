#!/usr/bin/env node

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dbPath = join(__dirname, '../frontend-react/src/features/database/data/database.generated.json');

const data = JSON.parse(readFileSync(dbPath, 'utf-8'));
const compounds = data.compounds;
const total = compounds.length;

console.log(`\n📊 SweetMeta Field Coverage Analysis`);
console.log(`Total compounds: ${total}\n`);

// Helper to check if value is meaningful
const isPresent = (value) => {
  if (value === null || value === undefined || value === '') return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === 'object') return Object.keys(value).length > 0;
  return true;
};

// Analyze top-level fields
const fieldStats = {
  // Identity fields
  'displayId': 0,
  'casNumbers': 0,
  'browsePubchemCid': 0,
  'chemicalClass': 0,
  'sourceNames': 0,
  'reviewedSourceNames': 0,
  'sourceCollection': 0,
  'sweetClassLevel1': 0,
  'sweetClassLevel2': 0,
  'evidenceGrade': 0,

  // Structure fields
  'inchiKey': 0,
  'isomericSmiles': 0,
  'canonicalSmiles': 0,
  'formula': 0,
  'molecularWeight': 0,

  // Properties
  'reviewedProperties.clogp': 0,
  'reviewedProperties.tpsa': 0,
  'reviewedProperties.rotatableBonds': 0,
  'reviewedProperties.hba': 0,
  'reviewedProperties.hbd': 0,

  // External enrichment
  'pubchem': 0,
  'pubchem.verified': 0,
  'chembl': 0,

  // Evidence
  'evidence.acceptedAssertions > 0': 0,
  'review.required': 0,
};

compounds.forEach(compound => {
  if (isPresent(compound.displayId)) fieldStats.displayId++;
  if (isPresent(compound.casNumbers)) fieldStats.casNumbers++;
  if (isPresent(compound.browsePubchemCid)) fieldStats.browsePubchemCid++;
  if (isPresent(compound.chemicalClass)) fieldStats.chemicalClass++;
  if (isPresent(compound.sourceNames)) fieldStats.sourceNames++;
  if (isPresent(compound.reviewedSourceNames)) fieldStats.reviewedSourceNames++;
  if (isPresent(compound.sourceCollection)) fieldStats.sourceCollection++;
  if (isPresent(compound.sweetClassLevel1)) fieldStats.sweetClassLevel1++;
  if (isPresent(compound.sweetClassLevel2)) fieldStats.sweetClassLevel2++;
  if (isPresent(compound.evidenceGrade)) fieldStats.evidenceGrade++;

  if (isPresent(compound.inchiKey)) fieldStats.inchiKey++;
  if (isPresent(compound.isomericSmiles)) fieldStats.isomericSmiles++;
  if (isPresent(compound.canonicalSmiles)) fieldStats.canonicalSmiles++;
  if (isPresent(compound.formula)) fieldStats.formula++;
  if (isPresent(compound.molecularWeight)) fieldStats.molecularWeight++;

  if (compound.reviewedProperties?.clogp !== null && compound.reviewedProperties?.clogp !== undefined) {
    fieldStats['reviewedProperties.clogp']++;
  }
  if (compound.reviewedProperties?.tpsa !== null && compound.reviewedProperties?.tpsa !== undefined) {
    fieldStats['reviewedProperties.tpsa']++;
  }
  if (compound.reviewedProperties?.rotatableBonds !== null && compound.reviewedProperties?.rotatableBonds !== undefined) {
    fieldStats['reviewedProperties.rotatableBonds']++;
  }
  if (compound.reviewedProperties?.hba !== null && compound.reviewedProperties?.hba !== undefined) {
    fieldStats['reviewedProperties.hba']++;
  }
  if (compound.reviewedProperties?.hbd !== null && compound.reviewedProperties?.hbd !== undefined) {
    fieldStats['reviewedProperties.hbd']++;
  }

  if (isPresent(compound.pubchem)) fieldStats.pubchem++;
  if (compound.pubchem?.matchStatus === 'verified') fieldStats['pubchem.verified']++;
  if (isPresent(compound.chembl)) fieldStats.chembl++;

  if (compound.evidence?.acceptedAssertions > 0) fieldStats['evidence.acceptedAssertions > 0']++;
  if (compound.review?.required) fieldStats['review.required']++;
});

// Print results grouped by category
console.log('## Core Identity Fields');
console.log('Field                    │ Present │  Coverage');
console.log('─────────────────────────┼─────────┼──────────');
[
  'displayId',
  'sourceCollection',
  'evidenceGrade',
  'sweetClassLevel1',
  'sweetClassLevel2',
].forEach(field => {
  const count = fieldStats[field];
  const pct = (count / total * 100).toFixed(1);
  const status = count === total ? '✓' : count > total * 0.8 ? '⚠' : '✗';
  console.log(`${field.padEnd(24)} │ ${String(count).padStart(7)} │ ${pct.padStart(5)}% ${status}`);
});

console.log('\n## Structure & Properties');
console.log('Field                    │ Present │  Coverage');
console.log('─────────────────────────┼─────────┼──────────');
[
  'formula',
  'molecularWeight',
  'inchiKey',
  'isomericSmiles',
  'canonicalSmiles',
  'reviewedProperties.clogp',
  'reviewedProperties.tpsa',
  'reviewedProperties.rotatableBonds',
].forEach(field => {
  const count = fieldStats[field];
  const pct = (count / total * 100).toFixed(1);
  const status = count === total ? '✓' : count > total * 0.8 ? '⚠' : '✗';
  console.log(`${field.padEnd(24)} │ ${String(count).padStart(7)} │ ${pct.padStart(5)}% ${status}`);
});

console.log('\n## External Enrichment');
console.log('Field                    │ Present │  Coverage');
console.log('─────────────────────────┼─────────┼──────────');
[
  'casNumbers',
  'browsePubchemCid',
  'pubchem',
  'pubchem.verified',
  'chembl',
].forEach(field => {
  const count = fieldStats[field];
  const pct = (count / total * 100).toFixed(1);
  const status = count === total ? '✓' : count > total * 0.5 ? '⚠' : '✗';
  console.log(`${field.padEnd(24)} │ ${String(count).padStart(7)} │ ${pct.padStart(5)}% ${status}`);
});

console.log('\n## Evidence & Review');
console.log('Field                         │ Present │  Coverage');
console.log('──────────────────────────────┼─────────┼──────────');
[
  'evidence.acceptedAssertions > 0',
  'review.required',
].forEach(field => {
  const count = fieldStats[field];
  const pct = (count / total * 100).toFixed(1);
  console.log(`${field.padEnd(29)} │ ${String(count).padStart(7)} │ ${pct.padStart(5)}%`);
});

// Legend
console.log('\n✓ = 100% coverage  ⚠ = Partial (>50-80%)  ✗ = Sparse (<50%)\n');
