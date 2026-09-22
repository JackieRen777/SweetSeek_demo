import type { DatabaseCompound } from './types';

export interface SweetMetaPage {
  items: Array<Partial<DatabaseCompound> & {
    id: string;
    name: string | null;
    releaseTier: string | null;
    releaseGap: string | null;
    reviewRequired: number;
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
  compound: Record<string, unknown>;
  release: Record<string, unknown>;
  quality: Record<string, unknown>;
  aliases: Array<Record<string, unknown>>;
  evidence: {
    tasteAssertions: Array<Record<string, unknown>>;
    measurements: Array<Record<string, unknown>>;
    conflicts: Array<Record<string, unknown>>;
  };
  literature: SweetMetaLiteratureRecord[];
  literatureReview?: { candidateCount: number; reviewRequiredCount: number };
  food: { count: number; items: Array<Record<string, unknown>> };
  regulatory: { count: number; items: Array<Record<string, unknown>> };
  receptors: { count: number; items: Array<Record<string, unknown>> };
}

export interface SweetMetaStatistics {
  release: {
    version: string;
    databaseFile: string;
    sha256: string;
    generatedAt: string | null;
    publicCompounds: number;
  };
  kpis: Array<{ key: string; label: string; value: number; detail: string }>;
  readiness: Array<{ key: string; label: string; count: number; percent: number }>;
  literatureTimeline: Array<{ yearFrom: number; yearTo: number; family: string; records: number }>;
  sweetnessDistribution: Array<{ key: string; label: string; minLog10: number | null; maxLog10: number | null; records: number; compounds: number }>;
  domainCoverage: Array<{ key: string; label: string; records: number; compounds: number; percent: number; denominator: number }>;
  foodGroups: Array<{ key: string; label: string; records: number; foods: number; compounds: number; percent: number; denominator: number }>;
  qualityProfile: Array<{ key: string; label: string; verified: number; attention: number; unknown: number; denominator: number }>;
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
  return json<SweetMetaPage>(`/api/sweetmeta/compounds?${search.toString()}`);
};

export const fetchSweetMetaStats = () => json<Record<string, unknown>>('/api/sweetmeta/stats');

export const fetchSweetMetaStatistics = () => json<SweetMetaStatistics>('/api/sweetmeta/statistics');

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
