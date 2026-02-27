import React, { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera, Float } from '@react-three/drei';
import * as THREE from 'three';

interface OralCavity3DProps {
  receptorDensity: number; // 0.5 to 2.0
  deltaG: number; // Binding affinity, affects interaction visual
  concentration: number; // Affects particle count
}

const TongueSurface = () => (
  <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, 0]} receiveShadow>
    <planeGeometry args={[20, 20]} />
    <meshStandardMaterial 
      color="#ff9999" 
      roughness={0.8} 
      metalness={0.1}
      bumpScale={0.1}
    />
  </mesh>
);

const Receptors = ({ count, deltaG }: { count: number; deltaG: number }) => {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = new THREE.Object3D();
  
  // Calculate color based on deltaG (lower deltaG = stronger binding = more active/bright)
  // deltaG range ~1.5 to 2.5. 
  // 1.5 -> Hot Pink (High Activity), 2.5 -> Blue (Low Activity)
  const color = useMemo(() => {
    const t = (deltaG - 1.5) / (2.5 - 1.5); // 0 to 1
    const c1 = new THREE.Color("#ec4899"); // Pink
    const c2 = new THREE.Color("#3b82f6"); // Blue
    return c1.lerp(c2, Math.max(0, Math.min(1, t)));
  }, [deltaG]);

  useEffect(() => {
    if (!meshRef.current) return;
    
    // Reset matrix
    for (let i = 0; i < 100; i++) {
        // Hide unused instances
        if (i >= count) {
            dummy.scale.set(0, 0, 0);
        } else {
            const x = (Math.random() - 0.5) * 12;
            const z = (Math.random() - 0.5) * 12;
            dummy.position.set(x, 0, z);
            dummy.rotation.x = (Math.random() - 0.5) * 0.2;
            dummy.rotation.z = (Math.random() - 0.5) * 0.2;
            dummy.scale.setScalar(0.5 + Math.random() * 0.3);
        }
        dummy.updateMatrix();
        meshRef.current.setMatrixAt(i, dummy.matrix);
    }
    meshRef.current.instanceMatrix.needsUpdate = true;
  }, [count]);

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, 100]} castShadow receiveShadow>
      {/* Receptor Shape: A simplified protein structure (Capsule-like) */}
      <capsuleGeometry args={[0.3, 0.8, 4, 8]} />
      <meshStandardMaterial color={color} roughness={0.3} metalness={0.4} />
    </instancedMesh>
  );
};

const Molecules = ({ count }: { count: number }) => {
  // Create a cloud of sweet molecules
  const groupRef = useRef<THREE.Group>(null);
  
  useFrame((state) => {
    if (!groupRef.current) return;
    groupRef.current.children.forEach((child, i) => {
      // Brownian-like motion
      child.position.y += Math.sin(state.clock.elapsedTime * 2 + i) * 0.002;
      child.rotation.x += 0.01;
      child.rotation.y += 0.01;
    });
    groupRef.current.rotation.y += 0.002;
  });

  const molecules = useMemo(() => {
    return Array.from({ length: Math.min(50, Math.max(5, count)) }).map((_, i) => {
      const x = (Math.random() - 0.5) * 10;
      const y = 1 + Math.random() * 3;
      const z = (Math.random() - 0.5) * 10;
      return (
        <Float key={i} speed={2} rotationIntensity={1} floatIntensity={1}>
            <mesh position={[x, y, z]}>
            <dodecahedronGeometry args={[0.15, 0]} />
            <meshStandardMaterial color="white" emissive="white" emissiveIntensity={0.5} />
            </mesh>
        </Float>
      );
    });
  }, [count]);

  return <group ref={groupRef}>{molecules}</group>;
};

const OralCavity3D: React.FC<OralCavity3DProps> = ({ receptorDensity, deltaG, concentration }) => {
  // Normalize inputs for visual logic
  const receptorCount = Math.floor(receptorDensity * 30); // 15 to 60
  const moleculeCount = Math.floor(concentration * 5); // 

  return (
    <div className="w-full h-full rounded-xl overflow-hidden bg-slate-900 border border-slate-700 shadow-inner relative">
      <div className="absolute top-4 left-4 z-10 bg-black/50 backdrop-blur-md px-3 py-1 rounded-lg border border-white/10">
        <span className="text-xs text-white/80 font-mono">Simulated Oral Environment</span>
      </div>
      
      <Canvas shadows dpr={[1, 2]} camera={{ position: [0, 5, 8], fov: 45 }}>
        <PerspectiveCamera makeDefault position={[0, 6, 8]} fov={50} />
        <OrbitControls 
            enablePan={false} 
            minPolarAngle={0} 
            maxPolarAngle={Math.PI / 2.5}
            minDistance={5}
            maxDistance={15}
        />
        
        {/* Lighting */}
        <ambientLight intensity={0.8} />
        <spotLight position={[10, 10, 5]} angle={0.3} penumbra={1} intensity={2} castShadow />
        <pointLight position={[-10, 5, -5]} intensity={1} color="#ec4899" />
        <pointLight position={[0, -5, 0]} intensity={0.5} color="#3b82f6" />

        {/* Environment */}
        <TongueSurface />
        <Receptors count={receptorCount} deltaG={deltaG} />
        <Molecules count={moleculeCount} />
        
        <fog attach="fog" args={['#0f172a', 5, 20]} />
      </Canvas>
    </div>
  );
};

export default OralCavity3D;
