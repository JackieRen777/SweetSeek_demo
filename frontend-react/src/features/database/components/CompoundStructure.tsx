import React, { useState } from 'react';
import { Download, ZoomIn } from 'lucide-react';

interface CompoundStructureProps {
  name: string;
  cid?: number;
  smiles?: string;
}

const CompoundStructure: React.FC<CompoundStructureProps> = ({ name, cid, smiles }) => {
  const [imgError, setImgError] = useState(false);
  const [fallbackIndex, setFallbackIndex] = useState(0);

  React.useEffect(() => {
    setImgError(false);
    setFallbackIndex(0);
  }, [name, cid, smiles]);

  const imageUrls = React.useMemo(() => {
    const urls: string[] = [];
    if (cid) {
      urls.push(`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/PNG?record_type=2d&image_size=large`);
    }
    if (name) {
      urls.push(`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(name)}/PNG?record_type=2d&image_size=large`);
    }
    if (smiles) {
      urls.push(`/api/structure/render?smiles=${encodeURIComponent(smiles)}&width=400&height=400`);
    }
    return urls;
  }, [name, cid, smiles]);

  const imageUrl = imageUrls[fallbackIndex] || '';

  const handleImageError = () => {
    if (fallbackIndex < imageUrls.length - 1) {
      setFallbackIndex(prev => prev + 1);
    } else {
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
          className="w-full h-full object-contain p-8 bg-white transition-transform duration-500 group-hover:scale-105"
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
