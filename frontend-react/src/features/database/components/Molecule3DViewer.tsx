import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useEffect, useMemo, useState } from 'react';
import * as THREE from 'three';

interface Atom3D {
  id: number;
  element: number;
  position: [number, number, number];
}

interface Bond3D {
  id: string;
  order: number;
  position: [number, number, number];
  length: number;
  quaternion: [number, number, number, number];
}

interface MoleculeModel {
  atoms: Atom3D[];
  bonds: Bond3D[];
}

const ELEMENTS: Record<number, { color: string; radius: number }> = {
  1: { color: '#f1f5f9', radius: 0.23 },
  6: { color: '#3f4b52', radius: 0.38 },
  7: { color: '#315fbd', radius: 0.39 },
  8: { color: '#d84a42', radius: 0.4 },
  9: { color: '#4caf72', radius: 0.4 },
  11: { color: '#7656b5', radius: 0.48 },
  15: { color: '#dd8a31', radius: 0.46 },
  16: { color: '#d5b52d', radius: 0.46 },
  17: { color: '#4c9c63', radius: 0.44 },
};

const normalizeRecord = (payload: unknown): MoleculeModel => {
  const record = (payload as { PC_Compounds?: Array<Record<string, unknown>> })?.PC_Compounds?.[0];
  if (!record) throw new Error('No 3D conformer returned');
  const atomsData = record.atoms as { aid?: number[]; element?: number[] };
  const bondsData = record.bonds as { aid1?: number[]; aid2?: number[]; order?: number[] };
  const coords = (record.coords as Array<{ aid?: number[]; conformers?: Array<{ x?: number[]; y?: number[]; z?: number[] }> }>)?.[0];
  const conformer = coords?.conformers?.[0];
  if (!atomsData?.aid || !atomsData.element || !coords?.aid || !conformer?.x || !conformer.y || !conformer.z) {
    throw new Error('Incomplete 3D coordinates');
  }
  const raw = coords.aid.map((id, index) => ({
    id,
    element: atomsData.element?.[atomsData.aid?.indexOf(id) ?? -1] ?? 6,
    position: [conformer.x?.[index] ?? 0, conformer.y?.[index] ?? 0, conformer.z?.[index] ?? 0] as [number, number, number],
  }));
  const center = raw.reduce((sum, atom) => [sum[0] + atom.position[0], sum[1] + atom.position[1], sum[2] + atom.position[2]], [0, 0, 0]).map((value) => value / raw.length);
  const atoms = raw.map((atom) => ({ ...atom, position: atom.position.map((value, index) => value - center[index]) as [number, number, number] }));
  const byId = new Map(atoms.map((atom) => [atom.id, atom]));
  const bonds = (bondsData?.aid1 ?? []).map((leftId, index) => {
    const left = byId.get(leftId);
    const right = byId.get(bondsData.aid2?.[index] ?? -1);
    if (!left || !right) return null;
    const start = new THREE.Vector3(...left.position);
    const end = new THREE.Vector3(...right.position);
    const direction = end.clone().sub(start);
    const quaternion = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.clone().normalize());
    const midpoint = start.clone().add(end).multiplyScalar(0.5);
    return {
      id: `${leftId}-${right.id}`,
      order: bondsData.order?.[index] ?? 1,
      position: midpoint.toArray() as [number, number, number],
      length: direction.length(),
      quaternion: quaternion.toArray() as [number, number, number, number],
    };
  }).filter((bond): bond is Bond3D => bond !== null);
  return { atoms, bonds };
};

const MolecularScene = ({ model }: { model: MoleculeModel }) => {
  const extent = useMemo(() => Math.max(3, ...model.atoms.map((atom) => Math.hypot(...atom.position))), [model]);
  const sceneScale = Math.min(1, 3.2 / extent);
  return (
    <>
      <ambientLight intensity={1.7} />
      <directionalLight position={[7, 9, 8]} intensity={2.2} />
      <directionalLight position={[-7, -4, -6]} intensity={0.8} />
      <group scale={sceneScale}>
        {model.bonds.map((bond) => <mesh key={bond.id} position={bond.position} quaternion={bond.quaternion}>
          <cylinderGeometry args={[bond.order > 1 ? 0.105 : 0.08, bond.order > 1 ? 0.105 : 0.08, bond.length, 18]} />
          <meshStandardMaterial color="#9ca9ae" roughness={0.4} metalness={0.05} />
        </mesh>)}
        {model.atoms.map((atom) => { const style = ELEMENTS[atom.element] ?? { color: '#b28bc7', radius: 0.42 }; return <mesh key={atom.id} position={atom.position}>
          <sphereGeometry args={[style.radius, 32, 24]} />
          <meshStandardMaterial color={style.color} roughness={0.28} metalness={0.03} />
        </mesh>; })}
      </group>
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} enablePan={false} minDistance={4} maxDistance={14} />
    </>
  );
};

export default function Molecule3DViewer({ cid, name, smiles }: { cid: number; name: string; smiles: string }) {
  const [state, setState] = useState<{ status: 'loading' | 'ready' | 'error'; model: MoleculeModel | null }>({ status: 'loading', model: null });
  useEffect(() => {
    const controller = new AbortController();
    const endpoints = [
      `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/${encodeURIComponent(smiles)}/record/JSON?record_type=3d`,
      `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/record/JSON?record_type=3d`,
    ];
    const load = async () => {
      for (const endpoint of endpoints) {
        try {
          const response = await fetch(endpoint, { signal: controller.signal });
          if (!response.ok) continue;
          setState({ status: 'ready', model: normalizeRecord(await response.json()) });
          return;
        } catch (error: unknown) {
          if ((error as Error).name === 'AbortError') return;
        }
      }
      setState({ status: 'error', model: null });
    };
    void load();
    return () => controller.abort();
  }, [cid, smiles]);
  if (state.status === 'loading') return <div className="db-structure-message"><strong>Loading 3D conformer</strong><span>PubChem CID {cid}</span></div>;
  if (state.status === 'error' || !state.model) return <div className="db-structure-message"><strong>3D conformer unavailable</strong><span>No usable PubChem 3D record was returned for {name}.</span></div>;
  return <Canvas className="db-3d-canvas" dpr={[1, 2]} camera={{ position: [0, 0, 11], fov: 42 }} gl={{ antialias: true, alpha: false }}><color attach="background" args={['#f8fafb']} /><MolecularScene model={state.model} /></Canvas>;
}
