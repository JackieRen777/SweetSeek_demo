import type { CompoundFilters, LiteratureReference, SimilarCompound, SortField, SweetCompound, SweetnessTier } from './types';

const numericFields = [
  'mw', 'logp', 'tpsa', 'hbondDonor', 'hbondAcceptor', 'rotatableBond', 'heavyAtom',
] as const;

const asNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const asText = (value: unknown): string | null => {
  if (typeof value !== 'string') return value == null ? null : String(value);
  return value.trim() || null;
};

const asCuratedText = (value: unknown): string | null => {
  const text = asText(value);
  if (!text || /placeholder|dummykey/i.test(text) || /^(?:n\/?a|not available|null|none|-)$/i.test(text)) return null;
  return text;
};

const normalizeReference = (raw: unknown): LiteratureReference | null => {
  if (!raw || typeof raw !== 'object') return null;
  const reference = raw as Record<string, unknown>;
  const title = asText(reference.title);
  if (!title) return null;
  const relation = reference.relation === 'indexed-mention' || reference.relation === 'curated-evidence'
    ? reference.relation : null;
  return {
    title,
    authors: Array.isArray(reference.authors)
      ? reference.authors.filter((author): author is string => typeof author === 'string' && Boolean(author.trim()))
      : [],
    year: asNumber(reference.year),
    journal: asText(reference.journal),
    doi: asText(reference.doi),
    pubmedId: asText(reference.pubmedId ?? reference.pubmed_id ?? reference.pmid),
    excerpt: asText(reference.excerpt),
    relatedFields: Array.isArray(reference.relatedFields)
      ? reference.relatedFields.filter((field): field is string => typeof field === 'string' && Boolean(field.trim()))
      : [],
    relation,
  };
};

export const normalizeCompound = (raw: Record<string, unknown>, index = 0): SweetCompound => {
  const cid = asNumber(raw.cid ?? raw['PubChem CID']) ?? index + 1;
  const hasPrototypePlaceholders = [raw.iupacName, raw.iupac_name, raw.IUPACName, raw.inchiKey, raw.inchikey, raw.InChIKey]
    .some((value) => typeof value === 'string' && /placeholder|dummykey/i.test(value));
  const rawReferences = Array.isArray(raw.references) ? raw.references : [];
  const rawAliases = Array.isArray(raw.aliases) ? raw.aliases : [];
  const rawSource = raw.source && typeof raw.source === 'object'
    ? raw.source as Record<string, unknown>
    : null;
  return {
    id: asNumber(raw.id) ?? cid,
    cid,
    name: asText(raw.name ?? raw.common_name ?? raw['Compound Name']) ?? `Compound ${cid}`,
    aliases: rawAliases.filter((alias): alias is string => typeof alias === 'string'),
    formula: asText(raw.formula ?? raw.molecular_formula ?? raw.MolecularFormula),
    mw: asNumber(raw.mw ?? raw.molecular_weight ?? raw.MolecularWeight),
    sweetness: asNumber(raw.sweetness ?? raw.sweetness_potency ?? raw.Relative_Sweetness),
    smiles: asCuratedText(raw.smiles ?? raw.canonical_smiles ?? raw.CanonicalSMILES),
    structure2dUrl: asText(raw.structure2dUrl ?? raw.structure_2d_url),
    isomericSmiles: asCuratedText(raw.isomericSmiles ?? raw.isomeric_smiles ?? raw.IsomericSMILES),
    inchi: asCuratedText(raw.inchi ?? raw.InChI),
    inchiKey: asCuratedText(raw.inchiKey ?? raw.inchikey ?? raw.InChIKey),
    iupacName: asCuratedText(raw.iupacName ?? raw.iupac_name ?? raw.IUPACName),
    logp: asNumber(raw.logp ?? raw.xlogp ?? raw.XLogP),
    tpsa: asNumber(raw.tpsa ?? raw.TPSA),
    hbondDonor: asNumber(raw.hbondDonor ?? raw.hbond_donor ?? raw.HBondDonorCount),
    hbondAcceptor: asNumber(raw.hbondAcceptor ?? raw.hbond_acceptor ?? raw.HBondAcceptorCount),
    rotatableBond: asNumber(raw.rotatableBond ?? raw.rotatable_bond ?? raw.RotatableBondCount),
    heavyAtom: asNumber(raw.heavyAtom ?? raw.heavy_atom ?? raw.HeavyAtomCount),
    qed: asNumber(raw.qed ?? raw.QED_Value),
    saScore: asNumber(raw.saScore ?? raw.sa_score ?? raw.SA_Score),
    lipinski: asNumber(raw.lipinski ?? raw.Lipinski),
    category: raw.category === 'natural' || raw.category === 'artificial' || raw.category === 'other'
      ? raw.category : null,
    description: asText(raw.description),
    references: rawReferences.map(normalizeReference).filter((reference): reference is LiteratureReference => reference !== null),
    source: {
      label: hasPrototypePlaceholders ? 'SweetSeek prototype workbook' : asText(rawSource?.label ?? raw.match_source) ?? 'SweetSeek database',
      kind: hasPrototypePlaceholders ? 'prototype-workbook' : asText(rawSource?.kind) ?? 'database',
    },
  };
};

export const getSweetnessTier = (value: number | null): SweetnessTier => {
  if (value === null || !Number.isFinite(value)) return 'unknown';
  if (value < 1) return 'below-sucrose';
  if (value < 10) return 'low';
  if (value <= 1000) return 'medium';
  return 'high';
};

export const getReferenceUrl = (reference: LiteratureReference): string | null => {
  const doi = reference.doi
    ?.normalize('NFKC')
    .replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '')
    .replace(/^doi\s*:\s*/i, '')
    .replace(/[.,;\s]+$/g, '');
  if (doi && !/^(?:n\/?a|not available|null|none|-)$/i.test(doi)) return `https://doi.org/${encodeURI(doi)}`;
  return reference.pubmedId ? `https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(reference.pubmedId)}/` : null;
};

export const DEFAULT_FILTERS: CompoundFilters = {
  query: '', sweetnessMin: null, sweetnessMax: null, mwMin: null, mwMax: null,
  logpMin: null, logpMax: null, sort: 'name', direction: 'asc',
};

const inRange = (value: number | null, min: number | null, max: number | null) => {
  if (min === null && max === null) return true;
  if (value === null) return false;
  return (min === null || value >= min) && (max === null || value <= max);
};

export const filterAndSortCompounds = (compounds: SweetCompound[], filters: CompoundFilters) => {
  const query = filters.query.trim().toLowerCase();
  const filtered = compounds.filter((compound) => {
    const searchable = [compound.name, compound.cid, compound.formula, ...compound.aliases]
      .filter(Boolean).join(' ').toLowerCase();
    return (!query || searchable.includes(query))
      && inRange(compound.sweetness, filters.sweetnessMin, filters.sweetnessMax)
      && inRange(compound.mw, filters.mwMin, filters.mwMax)
      && inRange(compound.logp, filters.logpMin, filters.logpMax);
  });
  return [...filtered].sort((a, b) => {
    const field: SortField = filters.sort;
    const av = a[field];
    const bv = b[field];
    if (av === null) return 1;
    if (bv === null) return -1;
    const comparison = typeof av === 'string' ? av.localeCompare(String(bv)) : av - Number(bv);
    return filters.direction === 'asc' ? comparison : -comparison;
  });
};

export const getSimilarCompounds = (
  target: SweetCompound,
  compounds: SweetCompound[],
  limit = 12,
): SimilarCompound[] => {
  const stats = Object.fromEntries(numericFields.map((field) => {
    const values = compounds.map((item) => item[field]).filter((value): value is number => value !== null);
    const mean = values.reduce((sum, value) => sum + value, 0) / Math.max(values.length, 1);
    const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / Math.max(values.length, 1);
    return [field, { mean, sd: Math.sqrt(variance) || 1 }];
  })) as Record<(typeof numericFields)[number], { mean: number; sd: number }>;

  return compounds.filter((candidate) => candidate.cid !== target.cid).map((candidate) => {
    const comparable = numericFields.filter((field) => target[field] !== null && candidate[field] !== null);
    if (comparable.length < 3) return null;
    const squaredDistance = comparable.reduce((sum, field) => {
      const delta = ((target[field] as number) - (candidate[field] as number)) / stats[field].sd;
      return sum + delta ** 2;
    }, 0) / comparable.length;
    const sweetnessProximity = target.sweetness && candidate.sweetness && target.sweetness > 0 && candidate.sweetness > 0
      ? Math.exp(-Math.abs(Math.log10(target.sweetness) - Math.log10(candidate.sweetness)))
      : null;
    return {
      compound: candidate,
      propertySimilarity: Math.exp(-Math.sqrt(squaredDistance)),
      sweetnessProximity,
      sharedProperties: comparable.length,
    };
  }).filter((item): item is SimilarCompound => item !== null)
    .sort((a, b) => b.propertySimilarity - a.propertySimilarity)
    .slice(0, limit);
};

export const formatValue = (value: number | string | null, digits = 2) => {
  if (value === null || value === '') return 'Not available';
  if (typeof value === 'number') return value.toLocaleString(undefined, { maximumFractionDigits: digits });
  return value;
};
