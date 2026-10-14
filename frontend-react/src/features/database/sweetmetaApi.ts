import type { DatabaseCompound } from './types';

export interface SweetMetaPage {
  items: Array<Partial<DatabaseCompound> & {
    id: string;
    displayId: string | null;
    casNumbers: string[];
    pubchemCid: string | null;
    chemicalClass: string | null;
    sourceNames: string[];
    name: string | null;
    releaseTier: string | null;
    releaseGap: string | null;
    reviewRequired: number;
    sweetClassLevel1: string;
    sweetClassLevel2: string;
    evidenceGrade: 'E1' | 'E2' | 'E3';
    sourceCollection: string;
    reviewedSourceNames: string[];
    molecularWeight: number;
    clogp: number;
    tpsa: number;
    rotatableBonds: number;
    hba: number;
    hbd: number;
  }>;
  page: number;
  pageSize: number;
  pageCount: number;
  total: number;
}

export interface SweetMetaLiteratureRecord {
  record_id: string;
  title: string;
  authors: string | null;
  first_author: string | null;
  year: number | null;
  journal: string | null;
  doi: string | null;
  pmid: string | null;
  article_type: string | null;
  study_domain: string | null;
  research_theme: string | null;
  compound_family?: string | null;
  data_value_tier: string | null;
  source_url: string | null;
  fulltext_quality_tier: string | null;
  manual_review_required: number;
  quality_status?: string | null;
  accepted_link_count?: number;
  reviewed_link_count?: number;
  candidate_link_count?: number;
  relation_type?: string | null;
  matched_text?: string | null;
  evidence_excerpt?: string | null;
  confidence?: number | null;
}

export interface SweetMetaCompoundDetail {
  compound: SweetMetaCompoundRecord;
  identity: SweetMetaIdentity;
  release: SweetMetaReleaseStatus;
  quality: SweetMetaQuality;
  aliases: SweetMetaAlias[];
  externalIds: SweetMetaExternalId[];
  classification: SweetMetaClassification | null;
  provenance: SweetMetaProvenance | null;
  physicochemical: SweetMetaPhysicochemical | null;
  projections: SweetMetaProjection[];
  stereoReview: SweetMetaDataRecord | null;
  evidence: {
    tasteAssertions: SweetMetaDataRecord[];
    measurements: SweetMetaDataRecord[];
    conflicts: SweetMetaDataRecord[];
  };
  literature: SweetMetaLiteratureRecord[];
  literatureReview?: { candidateCount: number; reviewRequiredCount: number };
  food: { count: number; items: SweetMetaDataRecord[] };
  regulatory: { count: number; items: SweetMetaDataRecord[] };
  receptors: { count: number; items: SweetMetaDataRecord[] };
  modules: { sweetness: number; literature: number; food: number; receptors: number; regulatory: number; conflicts: number };
}

export type SweetMetaDataValue = string | number | boolean | null | undefined;
export type SweetMetaDataRecord = Record<string, SweetMetaDataValue>;

export interface SweetMetaCompoundRecord extends SweetMetaDataRecord {
  compound_id: string;
  display_id: string | null;
  preferred_name: string | null;
  preferred_name_source: string | null;
  parent_inchikey: string;
  parent_isomeric_smiles: string;
  parent_canonical_smiles: string;
  molecular_formula: string | null;
  molecular_weight: number | null;
  formal_charge: number | null;
  heavy_atom_count: number | null;
}

export interface SweetMetaIdentity {
  stableId: string;
  displayId: string | null;
  preferredName: string | null;
  preferredNameSource: string | null;
  aliases: SweetMetaAlias[];
  externalIds: SweetMetaExternalId[];
}

export interface SweetMetaAlias extends SweetMetaDataRecord {
  alias: string;
  source_id: string;
  source_record_id: string | null;
}

export interface SweetMetaExternalId extends SweetMetaDataRecord {
  namespace: string;
  external_id: string;
  source_id: string;
  source_record_id: string | null;
}

export interface SweetMetaClassification extends SweetMetaDataRecord {
  level1: string;
  level2: string;
}

export interface SweetMetaProvenance extends SweetMetaDataRecord {
  source_collection: string;
  source_names: string;
  evidence_grade: 'E1' | 'E2' | 'E3';
  evidence_tier: string | null;
  evidence_lineage_status: string | null;
}

export interface SweetMetaPhysicochemical extends SweetMetaDataRecord {
  molecular_weight: number;
  clogp: number;
  tpsa: number;
  rotatable_bonds: number;
  hba: number;
  hbd: number;
  bertz_complexity: number;
  fraction_csp3: number;
  heavy_atom_count: number;
}

export interface SweetMetaQuality extends SweetMetaDataRecord {
  structure_verified?: string | null;
  stereochemistry_verified?: string | null;
  form_verified?: string | null;
  qc_training_use_status?: string | null;
  qc_manual_review_required?: string | null;
  qc_notes?: string | null;
}

export interface SweetMetaReleaseStatus extends SweetMetaDataRecord {
  release_tier: string | null;
  release_gap: string | null;
  manual_review_required: number | string | null;
  status_note: string | null;
}

export interface SweetMetaProjection extends SweetMetaDataRecord {
  method: 'umap' | 'pca';
  x: number;
  y: number;
  fingerprint: string;
  metric: string;
  random_seed: number;
}

export interface SweetMetaProjectionContext {
  compoundId: string;
  family: string;
  subclass: string;
  points: Array<{ id: string; method: 'umap' | 'pca'; x: number; y: number; name: string; sweetClassLevel1: string; sweetClassLevel2: string; selected: number }>;
}

export interface SweetMetaStatistics {
  release: {
    version: string;
    databaseFile: string;
    sha256: string;
    generatedAt: string | null;
    publicCompounds: number;
    reviewDate?: string;
  };
  kpis: Array<{ key: string; label: string; value: number; detail: string }>;
  readiness: Array<{ key: string; label: string; count: number; percent: number }>;
  literatureTimeline: Array<{ yearFrom: number; yearTo: number; family: string; records: number }>;
  sweetnessDistribution: Array<{ key: string; label: string; minLog10: number | null; maxLog10: number | null; records: number; compounds: number }>;
  domainCoverage: Array<{ key: string; label: string; records: number; compounds: number; percent: number; denominator: number }>;
  foodGroups: Array<{ key: string; label: string; records: number; foods: number; compounds: number; percent: number; denominator: number }>;
  qualityProfile: Array<{ key: string; label: string; verified: number; attention: number; unknown: number; denominator: number }>;
  composition: {
    level1: Array<{ key: string; label: string; count: number; percent: number }>;
    level2: Array<{ parent: string; key: string; label: string; count: number; parentTotal: number; percentWithinParent: number; percentOverall: number }>;
  };
  chemicalSpace: Array<{
    id: string; method: 'umap' | 'pca'; x: number; y: number; name: string;
    formula: string | null; molecularWeight: number; sweetClassLevel1: string;
    sweetClassLevel2: string; evidenceGrade: 'E1' | 'E2' | 'E3';
    sourceCollection: string; sourceNames: string; releaseTier: string;
    fingerprint: string; metric: string; randomSeed: number;
  }>;
  evidenceCoverage: {
    sourceToGrade: Array<{ source: string; target: string; count: number }>;
    gradeToFamily: Array<{ source: string; target: string; count: number }>;
    paths: Array<{ source: string; grade: 'E1' | 'E2' | 'E3'; family: string; count: number }>;
    familyGrades: Array<{ family: string; grade: string; count: number; total: number; percent: number }>;
    modules: Array<{ module: string; displayMetric: string; nativeGrain: string; count: number; color: string }>;
  };
  properties: Array<{ key: string; label: string; unit: string; axisPrecision: number; groups: Array<{ family: string; n: number; min: number; q1: number; median: number; q3: number; max: number; density: Array<{ value: number; density: number }> }> }>;
  featureCoverageComparison: Array<{ resource: string; entryScope: string; snapshot: string; features: Record<string, number> }>;
  benchmark: {
    splits: Array<{ split: string; negative: number; positive: number; total: number }>;
    models: Array<{ model: string; displayModel: string; split: string; seed: string; n: number; threshold: number; rocAuc: number; prAuc: number; balancedAccuracy: number; mcc: number; brier: number }>;
  };
}

export interface SweetMetaDownloads {
  version: string;
  reviewDate: string;
  recordCount: number;
  items: Array<{ key: string; label: string; filename: string; bytes: number; sha256: string; url: string }>;
}

const json = async <T>(url: string): Promise<T> => {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`SweetMeta API request failed (${response.status})`);
  const payload = await response.json() as { success?: boolean; error?: string; data?: T };
  if (payload.success === false) throw new Error(payload.error ?? 'SweetMeta API request failed');
  if (payload.data === undefined) throw new Error('SweetMeta API returned an invalid payload');
  return payload.data as T;
};

export const fetchSweetMetaCompounds = (params: {
  query?: string;
  page?: number;
  pageSize?: number;
  tier?: string;
  review?: string;
  domain?: string;
  foodGroup?: string;
  sweetnessMinLog10?: number;
  sweetnessMaxLog10?: number;
  qualityMetric?: string;
  qualityState?: string;
  sweetClassL1?: string;
  sweetClassL2?: string;
  evidenceGrade?: string;
  sourceCollection?: string;
  mwMin?: number;
  mwMax?: number;
  clogpMin?: number;
  clogpMax?: number;
  tpsaMin?: number;
  tpsaMax?: number;
}) => {
  const search = new URLSearchParams();
  if (params.query) search.set('q', params.query);
  search.set('page', String(params.page ?? 1));
  search.set('pageSize', String(params.pageSize ?? 25));
  if (params.tier && params.tier !== 'all') search.set('tier', params.tier);
  if (params.review && params.review !== 'all') search.set('review', params.review);
  if (params.domain) search.set('domain', params.domain);
  if (params.foodGroup) search.set('foodGroup', params.foodGroup);
  if (params.sweetnessMinLog10 !== undefined) search.set('sweetnessMinLog10', String(params.sweetnessMinLog10));
  if (params.sweetnessMaxLog10 !== undefined) search.set('sweetnessMaxLog10', String(params.sweetnessMaxLog10));
  if (params.qualityMetric) search.set('qualityMetric', params.qualityMetric);
  if (params.qualityState) search.set('qualityState', params.qualityState);
  if (params.sweetClassL1) search.set('sweetClassL1', params.sweetClassL1);
  if (params.sweetClassL2) search.set('sweetClassL2', params.sweetClassL2);
  if (params.evidenceGrade) search.set('evidenceGrade', params.evidenceGrade);
  if (params.sourceCollection) search.set('sourceCollection', params.sourceCollection);
  (['mwMin', 'mwMax', 'clogpMin', 'clogpMax', 'tpsaMin', 'tpsaMax'] as const).forEach((key) => {
    if (params[key] !== undefined) search.set(key, String(params[key]));
  });
  return json<SweetMetaPage>(`/api/sweetmeta/compounds?${search.toString()}`);
};

export const fetchSweetMetaStats = () => json<Record<string, unknown>>('/api/sweetmeta/stats');

export const fetchSweetMetaStatistics = () => json<SweetMetaStatistics>('/api/sweetmeta/statistics');
export const fetchSweetMetaProjectionContext = async (compoundId: string): Promise<SweetMetaProjectionContext> => {
  try {
    return await json<SweetMetaProjectionContext>(`/api/sweetmeta/compounds/${encodeURIComponent(compoundId)}/projection-context`);
  } catch (endpointError) {
    const statistics = await fetchSweetMetaStatistics();
    const selected = statistics.chemicalSpace.find((point) => point.id === compoundId);
    if (!selected) throw endpointError;
    return {
      compoundId,
      family: selected.sweetClassLevel1,
      subclass: selected.sweetClassLevel2,
      points: statistics.chemicalSpace
        .filter((point) => point.sweetClassLevel1 === selected.sweetClassLevel1)
        .map((point) => ({
          id: point.id,
          method: point.method,
          x: point.x,
          y: point.y,
          name: point.name,
          sweetClassLevel1: point.sweetClassLevel1,
          sweetClassLevel2: point.sweetClassLevel2,
          selected: point.id === compoundId ? 1 : 0,
        })),
    };
  }
};

export const fetchSweetMetaCompound = (id: string) => json<SweetMetaCompoundDetail>(`/api/sweetmeta/compounds/${encodeURIComponent(id)}`);

export const fetchSweetMetaLiterature = (params: { query?: string; page?: number; pageSize?: number; year?: string; yearFrom?: number; yearTo?: number; pmidOnly?: boolean; doiOnly?: boolean; reviewStatus?: string; relationType?: string; compoundId?: string; compoundFamily?: string }) => {
  const search = new URLSearchParams();
  if (params.query) search.set('q', params.query);
  search.set('page', String(params.page ?? 1));
  search.set('pageSize', String(params.pageSize ?? 25));
  if (params.year && params.year !== 'all') search.set('year', params.year);
  if (params.yearFrom) search.set('yearFrom', String(params.yearFrom));
  if (params.yearTo) search.set('yearTo', String(params.yearTo));
  if (params.pmidOnly) search.set('pmidOnly', 'true');
  if (params.doiOnly) search.set('doiOnly', 'true');
  if (params.reviewStatus && params.reviewStatus !== 'all') search.set('reviewStatus', params.reviewStatus);
  if (params.relationType && params.relationType !== 'all') search.set('relationType', params.relationType);
  if (params.compoundId) search.set('compoundId', params.compoundId);
  if (params.compoundFamily && params.compoundFamily !== 'all') search.set('compoundFamily', params.compoundFamily);
  return json<{ items: SweetMetaLiteratureRecord[]; page: number; pageSize: number; pageCount: number; total: number }>(`/api/sweetmeta/literature?${search.toString()}`);
};

export const fetchSweetMetaLiteratureDetail = (id: string) => json<Record<string, unknown>>(`/api/sweetmeta/literature/${encodeURIComponent(id)}`);

export const fetchSweetMetaDownloads = () => json<SweetMetaDownloads>('/api/sweetmeta/downloads');
