import { describe, expect, it } from 'vitest';
import bundled from './data/compounds.json';
import { BUNDLED_COMPOUNDS } from './data/compoundData';
import { CHEMICAL_SPACE } from './data/chemicalSpace';
import { DEFAULT_FILTERS, filterAndSortCompounds, getReferenceUrl, getSimilarCompounds, getSweetnessTier, normalizeCompound } from './utils';

describe('Sweetness Database data contract', () => {
  it('contains 56 records with unique CIDs', () => {
    expect(bundled).toHaveLength(56);
    expect(new Set(BUNDLED_COMPOUNDS.map((compound) => compound.cid)).size).toBe(56);
  });

  it('provides deterministic fingerprint-space coordinates for every supported small molecule', () => {
    expect(CHEMICAL_SPACE.points).toHaveLength(49);
    expect(CHEMICAL_SPACE.excluded).toHaveLength(7);
    expect(new Set(CHEMICAL_SPACE.points.map((point) => point.cid)).size).toBe(49);
    expect(CHEMICAL_SPACE.points.every((point) => point.x >= 0 && point.x <= 1 && point.y >= 0 && point.y <= 1)).toBe(true);
    expect(CHEMICAL_SPACE.metadata.distance).toBe('Tanimoto distance');
  });

  it('preserves missing values as null', () => {
    const compound = normalizeCompound({ cid: 1, name: 'Test', mw: '', logp: undefined });
    expect(compound.mw).toBeNull();
    expect(compound.logp).toBeNull();
    expect(compound.category).toBeNull();
  });

  it('does not publish placeholder identifiers as curated chemistry data', () => {
    const compound = normalizeCompound({
      cid: 2,
      name: 'Placeholder test',
      IUPACName: 'Placeholder test IUPAC Name Placeholder',
      InChIKey: 'DUMMYKEY-2-N',
    });
    expect(compound.iupacName).toBeNull();
    expect(compound.inchiKey).toBeNull();
    expect(compound.source.kind).toBe('prototype-workbook');
  });

  it('assigns the requested relative sweetness tiers at explicit boundaries', () => {
    expect(getSweetnessTier(null)).toBe('unknown');
    expect(getSweetnessTier(0.99)).toBe('below-sucrose');
    expect(getSweetnessTier(1)).toBe('low');
    expect(getSweetnessTier(9.99)).toBe('low');
    expect(getSweetnessTier(10)).toBe('medium');
    expect(getSweetnessTier(1000)).toBe('medium');
    expect(getSweetnessTier(1000.01)).toBe('high');
  });

  it('builds DOI links first and falls back to PubMed', () => {
    const reference = {
      title: 'Test paper', authors: [], year: 2026, journal: null, doi: 'https://doi.org/10.1000/example.',
      pubmedId: '12345', excerpt: null, relatedFields: [], relation: 'indexed-mention' as const,
    };
    expect(getReferenceUrl(reference)).toBe('https://doi.org/10.1000/example');
    expect(getReferenceUrl({ ...reference, doi: null })).toBe('https://pubmed.ncbi.nlm.nih.gov/12345/');
  });

  it('searches by name, CID, and formula', () => {
    const search = (query: string) => filterAndSortCompounds(BUNDLED_COMPOUNDS, { ...DEFAULT_FILTERS, query });
    expect(search('Sucrose').some((compound) => compound.cid === 5988)).toBe(true);
    expect(search('5988').some((compound) => compound.name === 'Sucrose')).toBe(true);
    expect(search('C12H22O11').some((compound) => compound.name === 'Sucrose')).toBe(true);
  });

  it('filters ranges and sorts sweetness descending', () => {
    const results = filterAndSortCompounds(BUNDLED_COMPOUNDS, {
      ...DEFAULT_FILTERS,
      sweetnessMin: 100,
      sort: 'sweetness',
      direction: 'desc',
    });
    expect(results.length).toBeGreaterThan(0);
    expect(results.every((compound) => (compound.sweetness ?? 0) >= 100)).toBe(true);
    expect(results[0].sweetness).toBeGreaterThanOrEqual(results.at(-1)?.sweetness ?? 0);
  });

  it('produces deterministic property neighbors with explicit property counts', () => {
    const sucrose = BUNDLED_COMPOUNDS.find((compound) => compound.cid === 5988);
    expect(sucrose).toBeDefined();
    const first = getSimilarCompounds(sucrose!, BUNDLED_COMPOUNDS, 10);
    const second = getSimilarCompounds(sucrose!, BUNDLED_COMPOUNDS, 10);
    expect(first).toHaveLength(10);
    expect(first.map((item) => item.compound.cid)).toEqual(second.map((item) => item.compound.cid));
    expect(first.every((item) => item.sharedProperties >= 3)).toBe(true);
    expect(first.every((item) => item.compound.cid !== 5988)).toBe(true);
  });
});
