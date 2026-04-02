import React, { useState, useMemo, useEffect } from 'react';

interface CompoundThumbnailProps {
  name: string;
  cid?: number;
  smiles?: string;
  size?: number; // default 100
  className?: string;
}

const CompoundThumbnail: React.FC<CompoundThumbnailProps> = ({ 
  name, 
  cid, 
  smiles, 
  size = 100,
  className = ""
}) => {
  const [useBackend, setUseBackend] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setUseBackend(true);
    setError(false);
  }, [name, cid, smiles]);

  const imageUrl = useMemo(() => {
    if (useBackend && smiles) {
      return `/api/structure/render?smiles=${encodeURIComponent(smiles)}&width=${size}&height=${size}`;
    }
    
    // Fallback to PubChem
    // Note: PubChem doesn't support arbitrary sizes, only small/medium/large
    // small ~ 100x100, medium ~ 300x300, large ~ 500x500
    const pubchemSize = size <= 100 ? 'small' : (size <= 300 ? 'medium' : 'large');
    
    if (cid) return `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/PNG?record_type=2d&image_size=${pubchemSize}`;
    if (smiles) return `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/${encodeURIComponent(smiles)}/PNG?record_type=2d&image_size=${pubchemSize}`;
    return `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(name)}/PNG?record_type=2d&image_size=${pubchemSize}`;
  }, [name, cid, smiles, size, useBackend]);

  const handleError = () => {
    if (useBackend && smiles) {
      setUseBackend(false);
    } else {
      setError(true);
    }
  };

  if (error) {
     return (
        <div className={`flex items-center justify-center bg-slate-50 text-slate-300 rounded-lg border border-slate-100 ${className}`} style={{ width: size, height: size }}>
            <span className="text-[10px]">No Image</span>
        </div>
     );
  }

  return (
    <img 
      src={imageUrl} 
      alt={name} 
      className={`object-contain bg-white rounded-lg border border-slate-100 p-1 ${className}`}
      width={size}
      height={size}
      onError={handleError}
      loading="lazy"
    />
  );
};

export default CompoundThumbnail;
