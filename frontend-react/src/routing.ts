export type FeatureType = 'qa' | 'equation' | 'database' | 'references' | 'dual-protein' | 'encapsulation' | 'proteoglycan' | 'ml-predict' | 'md-builder' | null;

import { MD_BUILDER_ENABLED } from './featureFlags';

const PATH_MAP: Record<string, FeatureType> = {
  '/sweetseek': 'qa',
  '/professionalq&a': 'qa',
  '/equation': 'equation',
  '/database': 'database',
  '/references': 'references',
  '/dual-protein': 'dual-protein',
  '/encapsulation': 'encapsulation',
  '/embedding': 'encapsulation',
  '/proteoglycan': 'proteoglycan',
  '/ml-predict': 'ml-predict',
  '/amber-md-builder': 'md-builder',
  '/docking': 'md-builder',
};

export const REVERSE_PATH_MAP: Record<string, string> = {
  'qa': '/sweetseek',
  'equation': '/equation',
  'database': '/database',
  'references': '/references',
  'dual-protein': '/dual-protein',
  'encapsulation': '/encapsulation',
  'proteoglycan': '/proteoglycan',
  'ml-predict': '/ml-predict',
  'md-builder': '/amber-md-builder',
};

export const featureFromPath = (
  pathname: string,
  mdBuilderEnabled = MD_BUILDER_ENABLED,
): FeatureType => {
  const path = pathname.toLowerCase();
  const cleanPath = path.endsWith('/') && path.length > 1 ? path.slice(0, -1) : path;
  const feature = PATH_MAP[cleanPath] || (cleanPath === '/qa' ? 'qa' : null);
  return feature === 'md-builder' && !mdBuilderEnabled ? null : feature;
};
