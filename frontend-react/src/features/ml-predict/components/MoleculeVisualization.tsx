/**
 * Molecule Visualization (flat layout)
 * Two-column: 2D structure (left) + physicochemical descriptors (right).
 * No card containers — uses spacing, dividers and typography for hierarchy.
 */

import { motion } from 'framer-motion';
import { useState } from 'react';
import { Download } from 'lucide-react';

interface MoleculeProperties {
  mw?: number;
  logp?: number;
  tpsa?: number;
  hba?: number;
  hbd?: number;
  rot_bonds?: number;
  aromatic_rings?: number;
  heavy_atoms?: number;
}

interface Props {
  smilesCanonical: string;
  properties?: MoleculeProperties;
}

const PROPERTY_DEFS: Array<{
  key: keyof MoleculeProperties;
  label: string;
  desc: string;
  unit?: string;
}> = [
  { key: 'mw', label: 'Molecular Weight', desc: 'g/mol', unit: '' },
  { key: 'logp', label: 'LogP', desc: 'Lipophilicity (Crippen)' },
  { key: 'tpsa', label: 'TPSA', desc: 'Topological Polar Surface Area', unit: 'Å²' },
  { key: 'heavy_atoms', label: 'Heavy Atoms', desc: 'Non-hydrogen atom count' },
  { key: 'hba', label: 'HB Acceptors', desc: 'Hydrogen bond acceptors' },
  { key: 'hbd', label: 'HB Donors', desc: 'Hydrogen bond donors' },
  { key: 'rot_bonds', label: 'Rotatable Bonds', desc: 'Conformational flexibility' },
  { key: 'aromatic_rings', label: 'Aromatic Rings', desc: 'Number of aromatic rings' },
];

export default function MoleculeVisualization({ smilesCanonical, properties }: Props) {
  const [imgError, setImgError] = useState(false);
  const imgUrl = `/api/structure/render?smiles=${encodeURIComponent(smilesCanonical)}&width=500&height=500`;

  const handleDownload = async () => {
    try {
      const response = await fetch(imgUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `molecule_structure.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
    }
  };

  const formatValue = (key: keyof MoleculeProperties, value: number | undefined) => {
    if (value === undefined || value === null) return '—';
    if (key === 'mw' || key === 'logp' || key === 'tpsa') {
      return value.toFixed(2);
    }
    return String(value);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-start max-w-5xl mx-auto"
    >
      {/* Left: 2D Structure (1/2) — image on plain white, no surrounding card */}
      <div className="w-full max-w-[336px] mx-auto">
        <div className="relative group aspect-square flex items-center justify-center">
          {!imgError ? (
            <img
              src={imgUrl}
              alt="2D Structure"
              className="w-full h-full object-contain"
              onError={() => setImgError(true)}
            />
          ) : (
            <div className="text-slate-400 text-sm text-center px-4">
              Structure rendering failed
            </div>
          )}

          {!imgError && (
            <button
              onClick={handleDownload}
              className="absolute top-2 right-2 p-1.5 text-slate-400 hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity"
              title="Download Structure"
            >
              <Download size={16} />
            </button>
          )}
        </div>

        <div className="mt-4">
          <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-1">
            Canonical SMILES
          </p>
          <code className="text-xs text-slate-700 break-all leading-relaxed font-mono">
            {smilesCanonical}
          </code>
        </div>
      </div>

      {/* Right: Property grid (1/2) — bare cells separated by dividers, no card per item */}
      <div>
        <div className="grid grid-cols-2 divide-x divide-y divide-slate-200/70 border-y border-slate-200/70">
          {PROPERTY_DEFS.map((def) => {
            const value = properties?.[def.key];
            const display = formatValue(def.key, value as number | undefined);
            const isNumeric = value !== undefined && value !== null;
            return (
              <motion.div
                key={def.key}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="px-3 py-3"
              >
                <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-1 truncate">
                  {def.label}
                </p>
                <p
                  className={`text-lg font-semibold mb-0.5 leading-none ${
                    isNumeric ? 'text-slate-800' : 'text-slate-300'
                  }`}
                >
                  {display}
                  {def.unit && isNumeric && (
                    <span className="text-xs text-slate-400 font-normal ml-1">{def.unit}</span>
                  )}
                </p>
                <p className="text-[10px] text-slate-500 leading-tight line-clamp-2">
                  {def.desc}
                </p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
