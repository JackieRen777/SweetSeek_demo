import { describe, expect, it } from 'vitest';
import { CHEMICAL_SPACE } from './data/chemicalSpace';
import { DATABASE_COMPOUNDS, DATABASE_METADATA, readable, tierCode } from './data/portalData';

describe('SweetMeta release contract', () => {
  it('uses the 1,296-record source workbook as the sole compound master', () => {
    expect(DATABASE_COMPOUNDS).toHaveLength(1296);
    expect(DATABASE_METADATA.totalRecords).toBe(1296);
    expect(new Set(DATABASE_COMPOUNDS.map((compound) => compound.id)).size).toBe(1296);
    expect(new Set(DATABASE_COMPOUNDS.map((compound) => compound.inchiKey)).size).toBe(1296);
  });

  it('publishes every evidence tier and the complete review count', () => {
    expect(Object.keys(DATABASE_METADATA.tierCounts).some((tier) => tier.startsWith('R1'))).toBe(true);
    expect(Object.keys(DATABASE_METADATA.tierCounts).some((tier) => tier.startsWith('R2'))).toBe(true);
    expect(Object.keys(DATABASE_METADATA.tierCounts).some((tier) => tier.startsWith('R3'))).toBe(true);
    expect(Object.keys(DATABASE_METADATA.tierCounts).some((tier) => tier.startsWith('R4'))).toBe(true);
    expect(DATABASE_COMPOUNDS.filter((compound) => compound.review.required)).toHaveLength(170);
  });

  it('keeps current entity coverage extensible beyond small molecules', () => {
    expect(DATABASE_COMPOUNDS.every((compound) => compound.entityType === 'small-molecule')).toBe(true);
    expect(DATABASE_METADATA.currentEntityCoverage).toHaveProperty('protein', 0);
  });

  it('accepts PubChem enrichment only against an exact InChIKey match', () => {
    const enriched = DATABASE_COMPOUNDS.filter((compound) => compound.pubchem);
    expect(enriched.length).toBe(DATABASE_METADATA.pubchemMatched);
    expect(enriched.every((compound) => compound.pubchem?.inchiKey === compound.inchiKey)).toBe(true);
    expect(enriched.every((compound) => compound.pubchem?.sourceUrl?.startsWith('https://pubchem.ncbi.nlm.nih.gov/compound/'))).toBe(true);
  });

  it('keeps missing quantitative sweetness and literature out of the compound contract', () => {
    expect(DATABASE_COMPOUNDS[0]).not.toHaveProperty('sweetness');
    expect(DATABASE_COMPOUNDS[0]).not.toHaveProperty('references');
  });

  it('formats evidence and data labels consistently', () => {
    expect(tierCode('R3_dataset_supported')).toBe('R3');
    expect(readable('single_dataset_no_reference')).toBe('Single dataset no reference');
    expect(readable(null)).toBe('Not available');
  });

  it('maps every current record into a reproducible ECFP4 UMAP space', () => {
    expect(CHEMICAL_SPACE.metadata.method).toBe('UMAP');
    expect(CHEMICAL_SPACE.metadata.fingerprint).toContain('ECFP4');
    expect(CHEMICAL_SPACE.metadata.distance).toBe('Tanimoto distance');
    expect(CHEMICAL_SPACE.metadata.parameters.randomSeed).toBe(42);
    expect(CHEMICAL_SPACE.points).toHaveLength(DATABASE_METADATA.totalRecords);
    expect(CHEMICAL_SPACE.excluded).toHaveLength(0);
    expect(CHEMICAL_SPACE.points.every((point) => point.x >= 0 && point.x <= 1 && point.y >= 0 && point.y <= 1)).toBe(true);
  });

  it('assigns every mapped molecule to one of eight fingerprint-space clusters', () => {
    const clusterIds = CHEMICAL_SPACE.metadata.clusters.map((cluster) => cluster.id);
    expect(CHEMICAL_SPACE.metadata.clusterMethod).toContain('k-medoids');
    expect(clusterIds).toEqual(['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8']);
    expect(CHEMICAL_SPACE.metadata.clusters.reduce((total, cluster) => total + cluster.size, 0)).toBe(DATABASE_METADATA.totalRecords);
    expect(CHEMICAL_SPACE.points.every((point) => clusterIds.includes(point.cluster))).toBe(true);
  });
});
