import generated from './database.generated.json';
import type { DatabaseCompound, DatabaseMetadata } from '../types';

export const DATABASE_METADATA = generated.metadata as DatabaseMetadata;
export const DATABASE_COMPOUNDS = generated.compounds as DatabaseCompound[];

export const tierCode = (tier: string | null) => tier?.match(/^R[1-4]/)?.[0] ?? 'NA';

export const readable = (value: string | null) => value
  ? value.replace(/^R\d_/, '').replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())
  : 'Not available';

export const formatNumber = (value: number | null, digits = 1) => value === null
  ? 'Not available'
  : value.toLocaleString('en-US', { maximumFractionDigits: digits });
