/**
 * SMILES Text Input Component
 */

import { useState } from 'react';

interface Props {
  onPredict: (smiles: string) => void;
  loading: boolean;
}

const EXAMPLES = [
  { name: 'Ethanol', smiles: 'CCO' },
  { name: 'Phenol', smiles: 'C1=CC=C(C=C1)O' },
  { name: 'Aspirin', smiles: 'CC(=O)Oc1ccccc1C(=O)O' },
  { name: 'Saccharin', smiles: 'C1=CC=C2C(=C1)C(=O)NS2(=O)=O' },
  { name: 'Sucrose', smiles: 'C(C1C(C(C(C(O1)OC2(C(C(C(O2)CO)O)O)CO)O)O)O)O' },
];

export default function SmilesInput({ onPredict, loading }: Props) {
  const [smiles, setSmiles] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (smiles.trim()) {
      onPredict(smiles.trim());
    }
  };

  const loadExample = (exampleSmiles: string) => {
    setSmiles(exampleSmiles);
  };

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4 text-slate-700">Enter SMILES String</h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-600 mb-2">
            SMILES
          </label>
          <input
            type="text"
            value={smiles}
            onChange={(e) => setSmiles(e.target.value)}
            placeholder="e.g., CCO (ethanol)"
            className="w-full px-4 py-3 bg-white border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={loading}
          />
        </div>

        {/* Example Buttons */}
        <div>
          <p className="text-sm text-slate-600 mb-2 font-medium">Quick Examples:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.smiles}
                type="button"
                onClick={() => loadExample(ex.smiles)}
                className="px-3 py-1.5 bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 rounded-md text-sm text-slate-700 transition-colors"
                disabled={loading}
              >
                {ex.name}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !smiles.trim()}
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed rounded-lg font-semibold text-white transition-colors"
        >
          {loading ? 'Predicting...' : 'Predict Sweetness'}
        </button>
      </form>
    </div>
  );
}
