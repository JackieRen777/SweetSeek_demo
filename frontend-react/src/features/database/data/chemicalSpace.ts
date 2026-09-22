import chemicalSpace from './chemicalSpace.json';

export interface ChemicalSpacePoint {
  id: string;
  x: number;
  y: number;
  cluster: string;
}

export const CHEMICAL_SPACE = chemicalSpace as {
  metadata: {
    method: string;
    distance: string;
    fingerprint: string;
    implementation: string;
    sourceRecordCount: number;
    mappedRecordCount: number;
    parameters: {
      nNeighbors: number;
      minDist: number;
      spread: number;
      randomSeed: number;
    };
    clusterMethod: string;
    clusters: Array<{
      id: string;
      label: string;
      size: number;
      medoidId: string;
      medoidName: string | null;
    }>;
    generatedAt: string;
  };
  points: ChemicalSpacePoint[];
  neighbors: Record<string, Array<{ id: string; similarity: number }>>;
  excluded: Array<{ id: string; name: string; reason: string }>;
};

export const CHEMICAL_SPACE_BY_ID = new Map(
  CHEMICAL_SPACE.points.map((point) => [point.id, point]),
);
