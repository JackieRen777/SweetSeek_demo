import bundledCompounds from './compounds.json';
import type { SweetCompound } from '../types';
import { normalizeCompound } from '../utils';

export const BUNDLED_COMPOUNDS: SweetCompound[] = (bundledCompounds as Record<string, unknown>[])
  .map((compound, index) => normalizeCompound(compound, index));

const extractRows = (payload: unknown): Record<string, unknown>[] => {
  if (Array.isArray(payload)) return payload as Record<string, unknown>[];
  if (!payload || typeof payload !== 'object') return [];
  const record = payload as Record<string, unknown>;
  const rows = record.results ?? record.data;
  return Array.isArray(rows) ? rows as Record<string, unknown>[] : [];
};

export const loadCompounds = async (): Promise<{ compounds: SweetCompound[]; source: 'api' | 'bundled' }> => {
  try {
    const response = await fetch('/api/compounds?limit=1000', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    const rows = extractRows(await response.json());
    if (!rows.length) throw new Error('API returned no compounds');
    return { compounds: rows.map(normalizeCompound), source: 'api' };
  } catch {
    return { compounds: BUNDLED_COMPOUNDS, source: 'bundled' };
  }
};
