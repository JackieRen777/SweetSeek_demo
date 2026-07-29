export interface EvidenceChunk {
  chunk_id: string;
  page: number | null;
  text: string;
  score: number;
  rank: number;
}

export interface EncapsulationReference {
  ref_id: string;
  title: string;
  authors: string[];
  journal: string;
  year: string;
  volume: string;
  issue: string;
  pages: string;
  doi: string;
  filename: string;
  citation: string;
  primary_chunk: EvidenceChunk | null;
  chunks: EvidenceChunk[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  references?: EncapsulationReference[];
}
