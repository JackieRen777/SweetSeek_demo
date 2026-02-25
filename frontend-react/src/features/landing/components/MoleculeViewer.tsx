import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, ContactShadows, Html } from '@react-three/drei';
import * as THREE from 'three';
import { AlertTriangle, Loader2 } from 'lucide-react';
import ErrorBoundary from '../../../components/ui/ErrorBoundary';

// Loading Spinner inside Canvas
const CanvasLoader = () => {
  return (
    <Html center>
      <div className="flex flex-col items-center gap-2 bg-white/80 p-4 rounded-xl backdrop-blur-sm shadow-lg">
        <Loader2 className="animate-spin text-blue-500" size={32} />
        <span className="text-xs font-medium text-slate-600">Loading Model...</span>
      </div>
    </Html>
  );
};

// Error State inside Canvas
const CanvasErrorFallback = () => {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-slate-50/50 backdrop-blur-sm rounded-xl border border-red-100 p-6 text-center">
      <AlertTriangle className="text-red-400 mb-2" size={32} />
      <p className="text-sm text-slate-600 font-medium">3D Model Failed to Load</p>
      <p className="text-xs text-slate-400 mt-1">Please check your connection or browser support.</p>
    </div>
  );
};

// Fallback molecule (DNA helix style) if PDB fails or loading
const FallbackMolecule = () => {
  const groupRef = useRef<THREE.Group>(null);
  
  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += 0.005;
      groupRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.2) * 0.2;
    }
  });

  const spheres = Array.from({ length: 20 }).map((_, i) => {
    const t = i / 10 * Math.PI * 2;
    const x = Math.cos(t) * 3;
    const y = (i - 10) * 0.5;
    const z = Math.sin(t) * 3;
    return (
      <mesh key={i} position={[x, y, z]}>
        <sphereGeometry args={[0.4, 32, 32]} />
        <meshStandardMaterial color={i % 2 === 0 ? "#3B82F6" : "#EC4899"} metalness={0.3} roughness={0.2} />
      </mesh>
    );
  });

  return <group ref={groupRef}>{spheres}</group>;
};

const MoleculeViewer: React.FC = () => {
  return (
    <div className="w-full h-full relative">
      <ErrorBoundary fallback={<CanvasErrorFallback />}>
        <Canvas camera={{ position: [0, 0, 15], fov: 45 }} dpr={[1, 2]}>
          <ambientLight intensity={0.5} />
          <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={1} />
          <pointLight position={[-10, -10, -10]} intensity={0.5} />
          
          <React.Suspense fallback={<CanvasLoader />}>
             <FallbackMolecule /> 
          </React.Suspense>
          
          <ContactShadows resolution={1024} scale={50} blur={2} opacity={0.25} far={10} color="#3B82F6" />
          <OrbitControls enableZoom={false} enablePan={false} />
        </Canvas>
      </ErrorBoundary>
    </div>
  );
};

export default MoleculeViewer;
