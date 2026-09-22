import { Canvas, type ThreeEvent } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { DATABASE_COMPOUNDS, formatNumber } from '../data/portalData';
import { CHEMICAL_SPACE } from '../data/chemicalSpace';
import type { DatabaseCompound } from '../types';

interface Point3D { id: string; x: number; y: number; z: number }
interface Space3D { metadata: { mappedRecordCount: number; dimensions: number }; points: Point3D[] }

const COLORS = ['#4477aa', '#66ccee', '#228833', '#ccbb44', '#ee7733', '#cc6677', '#aa3377', '#999999'];
const SPACE_SCALE = 7;
const positionOf = (point: Point3D): [number, number, number] => [
  (point.x - 0.5) * SPACE_SCALE,
  (point.y - 0.5) * SPACE_SCALE,
  (point.z - 0.5) * SPACE_SCALE,
];

function NeighborLines({ points }: { points: Array<{ point: Point3D }> }) {
  const positions = useMemo(() => {
    const byId = new Map(points.map(({ point }) => [point.id, point]));
    const connected = new Set<string>();
    const values: number[] = [];
    points.forEach(({ point }) => {
      const neighbor = CHEMICAL_SPACE.neighbors[point.id]?.[0];
      const target = neighbor ? byId.get(neighbor.id) : null;
      if (!target) return;
      const key = [point.id, target.id].sort().join('|');
      if (connected.has(key)) return;
      connected.add(key);
      values.push(...positionOf(point), ...positionOf(target));
    });
    return new Float32Array(values);
  }, [points]);
  return <lineSegments renderOrder={-1}>
    <bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry>
    <lineBasicMaterial color="#8caac2" transparent opacity={0.16} depthWrite={false} />
  </lineSegments>;
}

function PointCloud({ points, onHover, onSelect }: {
  points: Array<{ point: Point3D; compound: DatabaseCompound; cluster: string }>;
  onHover: (compound: DatabaseCompound | null, cluster?: string) => void;
  onSelect: (id: string) => void;
}) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const geometry = useMemo(() => new THREE.SphereGeometry(0.095, 10, 8), []);
  const material = useMemo(() => new THREE.MeshBasicMaterial({ color: '#ffffff' }), []);
  useEffect(() => {
    const instanced = mesh.current;
    if (!instanced) return;
    const matrix = new THREE.Matrix4();
    const color = new THREE.Color();
    points.forEach(({ point, cluster }, index) => {
      matrix.makeTranslation(...positionOf(point));
      instanced.setMatrixAt(index, matrix);
      instanced.setColorAt(index, color.set(COLORS[Number(cluster.slice(1)) - 1] ?? COLORS[7]));
    });
    instanced.instanceMatrix.needsUpdate = true;
    if (instanced.instanceColor) instanced.instanceColor.needsUpdate = true;
    instanced.computeBoundingSphere();
  }, [points]);
  const inspect = (event: ThreeEvent<PointerEvent>) => {
    event.stopPropagation();
    const match = points[event.instanceId ?? -1];
    if (match) onHover(match.compound, match.cluster);
  };
  return <instancedMesh ref={mesh} args={[geometry, material, points.length]} onPointerOver={inspect} onPointerMove={inspect} onPointerOut={() => onHover(null)} onClick={(event) => {
    event.stopPropagation();
    const match = points[event.instanceId ?? -1];
    if (match) onSelect(match.compound.id);
  }} />;
}

export default function ChemicalSpace3D({ onSelect }: { onSelect: (id: string) => void }) {
  const [data, setData] = useState<Space3D | null>(null);
  const [error, setError] = useState(false);
  const [hovered, setHovered] = useState<{ compound: DatabaseCompound; cluster: string } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/database-data/chemical-space-3d.json', { signal: controller.signal })
      .then((response) => { if (!response.ok) throw new Error('3D data unavailable'); return response.json() as Promise<Space3D>; })
      .then((payload) => { if (payload.metadata.dimensions !== 3) throw new Error('Invalid 3D data'); setData(payload); })
      .catch(() => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, []);
  const points = useMemo(() => {
    const compounds = new Map(DATABASE_COMPOUNDS.map((compound) => [compound.id, compound]));
    const clusters = new Map(CHEMICAL_SPACE.points.map((point) => [point.id, point.cluster]));
    return (data?.points ?? []).flatMap((point) => {
      const compound = compounds.get(point.id);
      return compound ? [{ point, compound, cluster: clusters.get(point.id) ?? 'C8' }] : [];
    });
  }, [data]);
  if (error) return <div className="sdb-space-3d-state" role="alert">3D map unavailable. The 2D view remains accessible.</div>;
  if (!data) return <div className="sdb-space-3d-state" role="status">Loading 3D molecular space...</div>;
  return <div className="sdb-space-3d" aria-label="Interactive 3D ECFP4 UMAP molecular similarity map">
    <Canvas camera={{ position: [6.2, 4.8, 7.2], fov: 42, near: 0.1, far: 100 }} dpr={[1, 2]} gl={{ antialias: true }} onPointerMissed={() => setHovered(null)}>
      <color attach="background" args={['#fbfdff']} />
      <gridHelper args={[8.5, 10, '#d8e3ec', '#edf2f6']} position={[0, -3.6, 0]} />
      <axesHelper args={[3.9]} position={[-3.5, -3.5, -3.5]} />
      <NeighborLines points={points} />
      <PointCloud points={points} onHover={(compound, cluster) => setHovered(compound ? { compound, cluster: cluster ?? 'C8' } : null)} onSelect={onSelect} />
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} minDistance={5} maxDistance={22} />
    </Canvas>
    <div className="sdb-space-3d-labels" aria-hidden="true"><span>UMAP 1 / 2 / 3</span><span>Drag to rotate · Scroll to zoom</span></div>
    {hovered && <div className="sdb-space-3d-tooltip" role="status"><strong>{hovered.compound.name}</strong><small>{hovered.compound.formula ?? 'Formula unavailable'} · {formatNumber(hovered.compound.molecularWeight)} Da · {hovered.cluster}</small><span>Click point to open record</span></div>}
  </div>;
}
