import { describe, expect, it } from 'vitest';
import { DATABASE_COMPOUNDS, DATABASE_METADATA, readable, tierCode } from './data/portalData';

describe('Sweet Database release contract', () => {
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
});
