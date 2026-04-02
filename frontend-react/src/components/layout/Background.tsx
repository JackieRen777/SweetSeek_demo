import React from 'react';

const Background: React.FC = () => {
  return (
    <div className="fixed inset-0 w-full h-full -z-10 bg-[var(--bg-white)] overflow-hidden">
        {/* Blob 1: Soft Blue - Top Left */}
        <div 
            className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full mix-blend-multiply filter blur-[80px] opacity-60 animate-[blob-float_20s_infinite_ease-in-out]"
            style={{ backgroundColor: '#DBEAFE' }} // Blue 100
        />

        {/* Blob 2: Muted Slate/Indigo - Top Right */}
        <div 
            className="absolute top-[-10%] right-[-10%] w-[45vw] h-[45vw] rounded-full mix-blend-multiply filter blur-[80px] opacity-50 animate-[blob-float_25s_infinite_ease-in-out_reverse]"
            style={{ backgroundColor: '#E0E7FF' }} // Indigo 100
        />

        {/* Blob 3: Very Pale Purple/Pink - Bottom Left (Accent) */}
        <div 
            className="absolute bottom-[-20%] left-[20%] w-[50vw] h-[50vw] rounded-full mix-blend-multiply filter blur-[100px] opacity-40 animate-[blob-float_30s_infinite_ease-in-out]"
            style={{ backgroundColor: '#F3E8FF' }} // Purple 100
        />
        
        {/* Blob 4: Light Cyan - Bottom Right */}
        <div 
            className="absolute bottom-[-10%] right-[-5%] w-[40vw] h-[40vw] rounded-full mix-blend-multiply filter blur-[80px] opacity-50 animate-[blob-float_22s_infinite_ease-in-out_reverse]"
            style={{ backgroundColor: '#CFFAFE' }} // Cyan 100
        />

        {/* Subtle Noise Texture (Optional for that "frosted" look) */}
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none" 
             style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} 
        />
    </div>
  );
};

export default Background;
