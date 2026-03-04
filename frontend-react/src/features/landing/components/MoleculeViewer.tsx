import React, { useMemo, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Center, Sparkles } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import * as THREE from 'three';
import { AlertTriangle, Loader2 } from 'lucide-react';
import ErrorBoundary from '../../../components/ui/ErrorBoundary';

// Loading Spinner inside Canvas
const CanvasLoader = () => {
  return (
    <group>
      <Html center>
        <div className="flex flex-col items-center gap-2 bg-white/80 p-4 rounded-xl backdrop-blur-sm shadow-lg">
          <Loader2 className="animate-spin text-blue-500" size={32} />
          <span className="text-xs font-medium text-slate-600">Loading Model...</span>
        </div>
      </Html>
    </group>
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

const HeroModel = () => {
  const { scene } = useGLTF('/Sucralose _model.glb');

  // Process the model to apply the requested visual style
  const modelScene = useMemo(() => {
    const cloned = scene.clone();

    cloned.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const mesh = child as THREE.Mesh;
        
        // Apply a gradient effect based on vertex position
        // We calculate bounding box to normalize Y coordinate for gradient
        mesh.geometry.computeBoundingBox();
        const bbox = mesh.geometry.boundingBox!;
        const height = bbox.max.y - bbox.min.y;
        
        // Use MeshPhysicalMaterial with custom onBeforeCompile to inject gradient shader
        mesh.material = new THREE.MeshPhysicalMaterial({
          color: '#ffffff', 
          roughness: 0.2,
          metalness: 0.1,
          emissive: '#ffffff',
          emissiveIntensity: 0.2, // Reduced slightly as we increased lighting
          side: THREE.DoubleSide
        });

          // Inject shader to mix colors based on world position Y
        // @ts-ignore
        mesh.material.onBeforeCompile = (shader) => {
          // Use more vivid/saturated colors
          shader.uniforms.uColor1 = { value: new THREE.Color("#60A5FA") }; // Vivid Blue (Top)
          shader.uniforms.uColor2 = { value: new THREE.Color("#C084FC") }; // Vivid Purple (Middle)
          shader.uniforms.uColor3 = { value: new THREE.Color("#F472B6") }; // Vivid Pink (Bottom)
          shader.uniforms.uMinY = { value: bbox.min.y };
          shader.uniforms.uMaxY = { value: bbox.max.y };

          shader.vertexShader = `
            varying float vY;
            ${shader.vertexShader}
          `.replace(
            '#include <begin_vertex>',
            `
            #include <begin_vertex>
            vY = position.y; 
            `
          );

          shader.fragmentShader = `
            uniform vec3 uColor1;
            uniform vec3 uColor2;
            uniform vec3 uColor3;
            uniform float uMinY;
            uniform float uMaxY;
            varying float vY;
            ${shader.fragmentShader}
          `.replace(
            '#include <color_fragment>',
            `
            #include <color_fragment>
            float t = (vY - uMinY) / (uMaxY - uMinY);
            t = smoothstep(0.0, 1.0, t);
            
            vec3 gradientColor;
            if (t < 0.5) {
                gradientColor = mix(uColor3, uColor2, t * 2.0);
            } else {
                gradientColor = mix(uColor2, uColor1, (t - 0.5) * 2.0);
            }
            
            // Force pure color
            diffuseColor.rgb = gradientColor;
            
            // Apply slight emissive effect for self-illumination
             // This ensures it glows even in shadows
             diffuseColor.rgb += gradientColor * 0.2;
             `
           );
        };
        
        mesh.castShadow = true;
        mesh.receiveShadow = true;
      }
    });

    return cloned;
  }, [scene]);

  return <primitive object={modelScene} scale={0.08} />;
};

// Needed for Html component import
import { Html } from '@react-three/drei';

const MoleculeViewer: React.FC = () => {
  return (
    <div className="w-full h-full relative" style={{ overflow: 'visible' }}>
      <ErrorBoundary fallback={<CanvasErrorFallback />}>
        <Canvas 
           camera={{ position: [0, 0, 15], fov: 35 }} 
           dpr={[1.5, 2]} 
           gl={{ antialias: true, preserveDrawingBuffer: true, alpha: true }}
           style={{ width: '100%', height: '100%' }}
         >
          {/* 
              Lighting Setup for Gradient Effect:
              - Top-Left: Pink/Purple (#f9cdfd)
              - Bottom-Right: Light Blue (#d4e8fe)
          */}
          <ambientLight intensity={1.0} color="#ffffff" />
          
          {/* Main Key Light (Pink/Purple) */}
          <spotLight 
            position={[-5, 8, 5]} 
            angle={0.5} 
            penumbra={1} 
            intensity={1.0} 
            color="#f9cdfd" 
          />
          
          {/* Fill Light (Light Blue) */}
          <pointLight position={[5, -5, 5]} intensity={1.0} color="#d4e8fe" />
          
          {/* Front Light for brightness */}
          <directionalLight position={[0, 0, 5]} intensity={0.8} color="#ffffff" />

          {/* Back Light to illuminate the rear side */}
          <directionalLight position={[0, 0, -5]} intensity={1.0} color="#ffffff" />
          
          <Suspense fallback={<CanvasLoader />}>
             <Center>
                <group rotation={[Math.PI, 0, 0]}>
                  <HeroModel />
                </group>
             </Center>
             
             {/* Floating Particles (Sparkles) */}
            {/* Pink particles */}
            <Sparkles 
                count={30} 
                scale={12} 
                size={4} 
                speed={0.4} 
                opacity={0.6} 
                color="#f9cdfd" 
            />
            {/* Blue particles */}
            <Sparkles 
                count={20} 
                scale={14} 
                size={6} 
                speed={0.3} 
                opacity={0.5} 
                color="#d4e8fe" 
            />
          </Suspense>
          
          <OrbitControls 
            enableZoom={false} 
            enablePan={false} 
            enableRotate={false}
            autoRotate
            autoRotateSpeed={2.0}
            minPolarAngle={0}
            maxPolarAngle={Math.PI}
          />
          
           {/* Post Processing for Glow/Bloom effect */}
          <EffectComposer enableNormalPass={false}>
            <Bloom 
                luminanceThreshold={0.85} // Only very bright things glow
                mipmapBlur // Soft blur
                intensity={0.4} // Glow intensity
                radius={0.4} // Glow radius
            />
          </EffectComposer>
        </Canvas>
      </ErrorBoundary>
    </div>
  );
};

// Preload the model
useGLTF.preload('/Sucralose _model.glb');

export default MoleculeViewer;
