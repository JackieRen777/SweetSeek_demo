import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

interface StructureViewerProps {
  contents: Array<{ name: string; format: string; text: string }>;
}

interface ProteinAtom {
  chainId: string;
  residueId: string;
  residueName: string;
  atomName: string;
  element: string;
  x: number;
  y: number;
  z: number;
}

interface LigandAtom {
  x: number;
  y: number;
  z: number;
  element: string;
  residueName?: string;
}

type ParsedStructure = {
  proteinAtoms: ProteinAtom[];
  ligandAtoms: LigandAtom[];
};

const colors: Record<string, number> = {
  C: 0x9ca3af,
  N: 0x4f8edb,
  O: 0xe06b6b,
  S: 0xd4a72c,
  P: 0xd47c35,
  H: 0xe5e7eb,
};

const chainColors = [0x3b82f6, 0x10b981, 0xf59e0b, 0xec4899, 0x8b5cf6, 0xef4444];

function safeNumber(value: string): number | null {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function inferElement(atomName: string, explicit?: string) {
  const candidate = (explicit || atomName || 'C').trim();
  const token = candidate.match(/^[A-Za-z]+/)?.[0] || 'C';
  return token.slice(0, 1).toUpperCase();
}

function parsePdb(text: string): ParsedStructure {
  const proteinAtoms: ProteinAtom[] = [];
  const ligandAtoms: LigandAtom[] = [];

  for (const line of text.split(/\r?\n/)) {
    if (!/^(ATOM  |HETATM)/.test(line)) continue;
    const x = safeNumber(line.slice(30, 38).trim());
    const y = safeNumber(line.slice(38, 46).trim());
    const z = safeNumber(line.slice(46, 54).trim());
    if (x === null || y === null || z === null) continue;

    const atomName = line.slice(12, 16).trim();
    const residueName = line.slice(17, 20).trim().toUpperCase() || 'UNK';
    const chainId = line.slice(21, 22).trim() || '_';
    const residueId = line.slice(22, 27).trim() || '0';
    const element = inferElement(atomName, line.slice(76, 78).trim());
    const record = line.slice(0, 6).trim();

    if (record === 'ATOM' && (atomName === 'N' || atomName === 'CA' || atomName === 'C' || atomName === 'O')) {
      proteinAtoms.push({ chainId, residueId, residueName, atomName, element, x, y, z });
      continue;
    }
    if (record === 'ATOM') {
      proteinAtoms.push({ chainId, residueId, residueName, atomName, element, x, y, z });
      continue;
    }
    ligandAtoms.push({ x, y, z, element, residueName });
  }

  return { proteinAtoms, ligandAtoms };
}

function parseMol2(text: string): LigandAtom[] {
  const lines = text.split(/\r?\n/);
  const start = lines.findIndex(line => line.trim() === '@<TRIPOS>ATOM');
  if (start < 0) return [];
  const atoms: LigandAtom[] = [];
  for (const line of lines.slice(start + 1)) {
    if (line.startsWith('@<TRIPOS>')) break;
    if (!line.trim()) continue;
    const fields = line.trim().split(/\s+/);
    if (fields.length < 6) continue;
    const x = safeNumber(fields[2]);
    const y = safeNumber(fields[3]);
    const z = safeNumber(fields[4]);
    if (x === null || y === null || z === null) continue;
    atoms.push({ x, y, z, element: inferElement(fields[1], fields[5]), residueName: fields[7] });
  }
  return atoms;
}

function parseSdf(text: string): LigandAtom[] {
  const lines = text.split(/\r?\n/);
  if (lines.length < 4) return [];
  const counts = lines[3]?.trim().split(/\s+/).map(Number) || [];
  const atomCount = counts[0] || 0;
  if (atomCount <= 0) return [];
  return lines.slice(4, 4 + atomCount).flatMap(line => {
    const fields = line.trim().split(/\s+/);
    if (fields.length < 4) return [];
    const x = safeNumber(fields[0]);
    const y = safeNumber(fields[1]);
    const z = safeNumber(fields[2]);
    if (x === null || y === null || z === null) return [];
    return [{ x, y, z, element: inferElement(fields[3]), residueName: 'LIG' }];
  });
}

function parseStructure(item: { format: string; text: string }) {
  if (item.format === 'pdb') return parsePdb(item.text);
  if (item.format === 'mol2') return { proteinAtoms: [], ligandAtoms: parseMol2(item.text) };
  return { proteinAtoms: [], ligandAtoms: parseSdf(item.text) };
}

function addProteinCartoon(scene: THREE.Scene, proteinAtoms: ProteinAtom[]) {
  const chains = new Map<string, ProteinAtom[]>();
  for (const atom of proteinAtoms) {
    if (atom.atomName !== 'CA') continue;
    const key = atom.chainId || '_';
    if (!chains.has(key)) chains.set(key, []);
    chains.get(key)!.push(atom);
  }

  let index = 0;
  for (const [chainId, atoms] of chains.entries()) {
    if (atoms.length < 2) continue;
    const points = atoms.map(atom => new THREE.Vector3(atom.x, atom.y, atom.z));
    const color = chainColors[index % chainColors.length];
    index += 1;

    const material = new THREE.MeshPhongMaterial({
      color,
      shininess: 40,
      transparent: false,
      flatShading: false,
    });
    const curve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.15);
    const segments = Math.max(64, points.length * 12);
    const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, segments, 0.9, 14, false), material);
    scene.add(tube);

    for (const point of points) {
      const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(0.55, 12, 10),
        new THREE.MeshPhongMaterial({ color, shininess: 50 }),
      );
      sphere.position.copy(point);
      scene.add(sphere);
    }

    const label = new THREE.Object3D();
    label.name = `chain-${chainId}`;
    scene.add(label);
  }
}

function addLigand(scene: THREE.Scene, ligandAtoms: LigandAtom[]) {
  if (!ligandAtoms.length) return;
  const points = ligandAtoms.map(atom => new THREE.Vector3(atom.x, atom.y, atom.z));
  const center = points.reduce((sum, point) => sum.add(point), new THREE.Vector3()).multiplyScalar(1 / points.length);
  const shifted = points.map(point => point.clone().sub(center));

  const group = new THREE.Group();
  const radius = Math.max(0.18, Math.min(0.42, 7 / Math.sqrt(ligandAtoms.length)));
  ligandAtoms.forEach((atom, index) => {
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(radius, 14, 10),
      new THREE.MeshPhongMaterial({ color: colors[atom.element] || 0x7dd3fc, shininess: 60 }),
    );
    mesh.position.copy(shifted[index]);
    group.add(mesh);
  });

  for (let index = 1; index < shifted.length; index += 1) {
    const start = shifted[index - 1];
    const end = shifted[index];
    const direction = new THREE.Vector3().subVectors(end, start);
    const length = direction.length();
    if (length < 0.001) continue;
    const cylinder = new THREE.Mesh(
      new THREE.CylinderGeometry(0.12, 0.12, length, 12),
      new THREE.MeshPhongMaterial({ color: 0xf8fafc, shininess: 20 }),
    );
    const midpoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
    cylinder.position.copy(midpoint);
    cylinder.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.clone().normalize());
    group.add(cylinder);
  }

  group.position.copy(center.clone().multiplyScalar(-1));
  scene.add(group);
}

export default function StructureViewer({ contents }: StructureViewerProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const parsed = useMemo(() => contents.flatMap(item => parseStructure(item)), [contents]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || !contents.length) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1220);

    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 4000);
    camera.position.set(0, 0, 100);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x0b1220, 1);
    host.replaceChildren(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;

    scene.add(new THREE.AmbientLight(0xffffff, 1.8));
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.6);
    keyLight.position.set(40, 60, 80);
    scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0x8ab4ff, 0.8);
    fillLight.position.set(-30, -10, 50);
    scene.add(fillLight);

    const proteinAtoms = parsed.flatMap(item => item.proteinAtoms);
    const ligandAtoms = parsed.flatMap(item => item.ligandAtoms);

    if (proteinAtoms.length) addProteinCartoon(scene, proteinAtoms);
    if (ligandAtoms.length) addLigand(scene, ligandAtoms);

    const bbox = new THREE.Box3();
    scene.traverse(object => {
      if ((object as THREE.Mesh).isMesh) bbox.expandByObject(object);
    });

    if (!bbox.isEmpty()) {
      const size = bbox.getSize(new THREE.Vector3());
      const center = bbox.getCenter(new THREE.Vector3());
      scene.position.sub(center);
      const maxDim = Math.max(size.x, size.y, size.z, 1);
      camera.position.set(0, 0, maxDim * 2.4);
      camera.far = Math.max(2000, maxDim * 12);
      camera.updateProjectionMatrix();
      controls.target.set(0, 0, 0);
    }

    const resize = () => {
      const width = host.clientWidth || 640;
      const height = host.clientHeight || 360;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(host);

    let frame = 0;
    const animate = () => {
      frame = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      renderer.dispose();
      scene.traverse(object => {
        if ((object as THREE.Mesh).isMesh) {
          const mesh = object as THREE.Mesh;
          mesh.geometry.dispose();
          if (Array.isArray(mesh.material)) mesh.material.forEach(material => material.dispose());
          else mesh.material.dispose();
        }
      });
    };
  }, [contents, parsed]);

  return (
    <div className="mdp-structure-viewer" ref={hostRef} aria-label="3D structure viewer">
      <div className="mdp-viewer-caption">
        {contents.length ? `${contents.length} structure${contents.length > 1 ? 's' : ''} loaded` : 'Upload a PDB, MOL2, or SDF to view the structure'}
      </div>
    </div>
  );
}
