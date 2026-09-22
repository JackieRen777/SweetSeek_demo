export type LiteratureRelationship =
  | 'primary_subject'
  | 'tested_sweetener'
  | 'receptor_ligand'
  | 'synthesis_production'
  | 'comparator_control'
  | 'background_mention';

export interface LiteraturePaper {
  paperId: string;
  title: string;
  authors: string[];
  journal: string | null;
  year: number | null;
  family?: string | null;
  doi: string | null;
  pmid: string | null;
  sourceFile: string;
}

export interface CompoundPaperLink {
  linkId: string;
  compoundId: string;
  paperId: string;
  relationshipType: LiteratureRelationship;
  isPrimary: boolean;
  evidenceExcerpt: string;
  pageNumber: string | null;
  matchMethod: string;
  matchedAlias: string;
  mentionCount: number;
  confidence: number;
  reviewStatus: 'auto_high_confidence';
  reviewReason: string | null;
}

export interface LiteratureData {
  metadata: {
    generatedAt: string;
    sourcePaperCount: number;
    indexedPaperCount: number;
    sourceCompoundCount: number;
    linkedPaperCount: number;
    linkedCompoundCount: number;
    publicLinkCount: number;
    reviewCandidateCount: number;
    doiCount: number;
    pmidCount: number;
    relationshipCounts: Partial<Record<LiteratureRelationship, number>>;
    identityAmbiguityCount: number;
    policy: string;
  };
  papers: Record<string, LiteraturePaper>;
  links: CompoundPaperLink[];
}

let request: Promise<LiteratureData> | null = null;

export const loadLiteratureData = () => {
  if (!request) {
    request = fetch('/database-data/literature.generated.json')
      .then((response) => {
        if (!response.ok) throw new Error(`Literature data request failed (${response.status})`);
        return response.json() as Promise<LiteratureData>;
      })
      .catch((error) => {
        request = null;
        throw error;
      });
  }
  return request;
};

export const RELATIONSHIP_LABELS: Record<LiteratureRelationship, string> = {
  primary_subject: 'Primary subject',
  tested_sweetener: 'Tested sweetener',
  receptor_ligand: 'Receptor / ligand',
  synthesis_production: 'Synthesis & production',
  comparator_control: 'Comparator / control',
  background_mention: 'Background mention',
};
