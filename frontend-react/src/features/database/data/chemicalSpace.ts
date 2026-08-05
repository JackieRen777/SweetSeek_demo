import chemicalSpace from './chemicalSpace.json';

export interface ChemicalSpacePoint {
  cid: number;
  x: number;
  y: number;
}

export const CHEMICAL_SPACE = chemicalSpace as {
  metadata: {
    method: string;
    distance: string;
    fingerprint: string;
    source: string;
    sourceRecordCount: number;
    generatedAt: string;
  };
  points: ChemicalSpacePoint[];
  excluded: Array<{ cid: number; name: string; reason: string }>;
};

export const CHEMICAL_SPACE_BY_CID = new Map(
  CHEMICAL_SPACE.points.map((point) => [point.cid, point]),
);
