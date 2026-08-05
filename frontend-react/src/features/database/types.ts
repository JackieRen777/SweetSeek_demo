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
