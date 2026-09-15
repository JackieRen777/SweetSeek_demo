export interface LiteratureReference {
  title: string;
  authors: string[];
  year: number | null;
  journal: string | null;
  doi: string | null;
  pubmedId: string | null;
  excerpt: string | null;
  relatedFields: string[];
  relation: 'indexed-mention' | 'curated-evidence' | null;
}

export interface SweetCompound {
  id: number;
  cid: number;
  name: string;
  aliases: string[];
  formula: string | null;
  mw: number | null;
  sweetness: number | null;
  smiles: string | null;
  structure2dUrl: string | null;
  isomericSmiles: string | null;
  inchi: string | null;
  inchiKey: string | null;
  iupacName: string | null;
  logp: number | null;
  tpsa: number | null;
  hbondDonor: number | null;
  hbondAcceptor: number | null;
  rotatableBond: number | null;
  heavyAtom: number | null;
  qed: number | null;
  saScore: number | null;
  lipinski: number | null;
  category: 'natural' | 'artificial' | 'other' | null;
  description: string | null;
  references: LiteratureReference[];
  source: { label: string; kind: string };
}

export type SweetnessTier = 'unknown' | 'below-sucrose' | 'low' | 'medium' | 'high';

export type DatabaseView = 'atlas' | 'list';
export type SortField = 'name' | 'sweetness' | 'mw' | 'logp';

export interface CompoundFilters {
  query: string;
  sweetnessMin: number | null;
  sweetnessMax: number | null;
  mwMin: number | null;
  mwMax: number | null;
  logpMin: number | null;
  logpMax: number | null;
  sort: SortField;
  direction: 'asc' | 'desc';
}

export interface SimilarCompound {
  compound: SweetCompound;
  propertySimilarity: number;
  sweetnessProximity: number | null;
  sharedProperties: number;
}

export type DatabaseSection = 'overview' | 'compounds' | 'evidence' | 'literature' | 'statistics' | 'downloads' | 'guide';

export interface PubChemValidation {
  inchiKeyMatch: boolean;
  formulaMatch: boolean;
  molecularWeightDelta: number | null;
  heavyAtomMatch: boolean | null;
}

export interface PubChemEnrichment {
  cid: number | null;
  iupacName: string | null;
  molecularFormula: string | null;
  molecularWeight: number | null;
  smiles: string | null;
  connectivitySmiles: string | null;
  inchi: string | null;
  inchiKey: string | null;
  xlogp: number | null;
  tpsa: number | null;
  hBondDonorCount: number | null;
  hBondAcceptorCount: number | null;
  rotatableBondCount: number | null;
  heavyAtomCount: number | null;
  charge: number | null;
  sourceUrl: string | null;
  retrievedAt: string;
  matchStatus: 'verified' | 'matched-with-discrepancy';
  validation: PubChemValidation;
}

export interface DatabaseCompound {
  id: string;
  entityType: 'small-molecule' | 'protein' | 'other';
  name: string;
  nameSource: string | null;
  inchiKey: string | null;
  canonicalTautomerInchiKey: string | null;
  isomericSmiles: string | null;
  canonicalSmiles: string | null;
  formula: string | null;
  molecularWeight: number | null;
  formalCharge: number | null;
  heavyAtomCount: number | null;
  createdAt: string | null;
  evidence: {
    baselineTier: string | null;
    releaseTier: string | null;
    baselineGap: string | null;
    releaseGap: string | null;
    priorityScore: number | null;
    acceptedAssertions: number;
  };
  review: {
    required: boolean;
    identityStatus: string | null;
    note: string | null;
  };
  pubchem: PubChemEnrichment | null;
}

export interface DatabaseMetadata {
  title: string;
  version: string;
  sourceWorkbook: string;
  sourceSheet: string;
  generatedAt: string;
  totalRecords: number;
  currentEntityCoverage: Record<string, number>;
  tierCounts: Record<string, number>;
  gapCounts: Record<string, number>;
  reviewRequired: number;
  acceptedAssertions: number;
  pubchemMatched: number;
  pubchemVerified: number;
}
