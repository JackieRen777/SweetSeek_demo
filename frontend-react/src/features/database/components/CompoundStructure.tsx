import React, { useState } from 'react';
import { Download, ZoomIn } from 'lucide-react';

interface CompoundStructureProps {
  name: string;
  cid?: number;
  smiles?: string;
}

const CompoundStructure: React.FC<CompoundStructureProps> = ({ name, cid, smiles }) => {
  const [imgError, setImgError] = useState(false);
  const [useBackend, setUseBackend] = useState(true); // Prioritize local backend

  // Reset error state when molecule changes
  React.useEffect(() => {
    setImgError(false);
    setUseBackend(true); // Reset to try backend first for new molecule
  }, [name, cid, smiles]);

  const imageUrl = React.useMemo(() => {
    if (useBackend && smiles) {
      return `/api/structure/render?smiles=${encodeURIComponent(smiles)}&width=400&height=400`;
    }
    
    // Fallback to PubChem - Try different formats
    // Priority: CID -> Name -> SMILES (SMILES often has encoding issues in URLs)
    if (cid) {
        return `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/PNG?record_type=2d&image_size=large`;
    }
    
    // Clean up name for URL (remove special chars if needed, though encodeURIComponent usually handles it)
    if (name) {
        return `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(name)}/PNG?record_type=2d&image_size=large`;
    }

    if (smiles) {
        return `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/${encodeURIComponent(smiles)}/PNG?record_type=2d&image_size=large`;
    }

    return '';
  }, [name, cid, smiles, useBackend]);

  const handleImageError = () => {
    if (useBackend && smiles) {
      // If backend fails, try PubChem
      setUseBackend(false);
    } else {
      // If PubChem also fails (or was already trying PubChem), show placeholder
      setImgError(true);
    }
  };
  const handleDownload = async () => {
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name}_structure.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  return (
    <div className="relative bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden group aspect-square flex items-center justify-center">
      <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
        <button 
          onClick={handleDownload}
          className="p-2 bg-white/90 backdrop-blur text-slate-600 hover:text-blue-600 rounded-lg shadow-sm border border-slate-200 transition-colors"
          title="Download Structure"
        >
          <Download size={18} />
        </button>
        <button 
          className="p-2 bg-white/90 backdrop-blur text-slate-600 hover:text-blue-600 rounded-lg shadow-sm border border-slate-200 transition-colors"
          title="Zoom View"
        >
          <ZoomIn size={18} />
        </button>
      </div>
      
      {!imgError ? (
        <img 
          src={imageUrl} 
          alt={`${name} Structure`}
          className="w-full h-full object-contain p-8 transition-transform duration-500 group-hover:scale-105"
          onError={handleImageError}
        />
      ) : (
        <div className="flex flex-col items-center justify-center text-slate-400 p-8 text-center">
          <div className="text-4xl mb-2">⚛️</div>
          <p className="text-sm">Structure not available</p>
        </div>
      )}
      
      <div className="absolute bottom-4 left-4 bg-white/80 backdrop-blur px-3 py-1 rounded-full border border-slate-100 text-xs font-mono text-slate-500">
        2D Structure
      </div>
    </div>
  );
};

export default CompoundStructure;
