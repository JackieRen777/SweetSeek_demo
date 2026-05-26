/**
 * SMILES Text Input Component
 */

import { useState } from 'react';

interface Props {
  onPredict: (smiles: string) => void;
  loading: boolean;
}

const EXAMPLES = [
  { name: '乙醇', smiles: 'CCO' },
  { name: '苯酚', smiles: 'C1=CC=C(C=C1)O' },
  { name: '阿司匹林', smiles: 'CC(=O)Oc1ccccc1C(=O)O' },
  { name: '糖精', smiles: 'C1=CC=C2C(=C1)C(=O)NS2(=O)=O' },
  { name: '蔗糖', smiles: 'C(C1C(C(C(C(O1)OC2(C(C(C(O2)CO)O)O)CO)O)O)O)O' },
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
      <h3 className="text-xl font-semibold mb-4 text-gray-200">输入 SMILES 字符串</h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            SMILES
          </label>
          <input
            type="text"
            value={smiles}
            onChange={(e) => setSmiles(e.target.value)}
            placeholder="例如: CCO (乙醇)"
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-orange-500"
            disabled={loading}
          />
        </div>

        {/* Example Buttons */}
        <div>
          <p className="text-sm text-gray-400 mb-2">快速示例:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex.smiles}
                type="button"
                onClick={() => loadExample(ex.smiles)}
                className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-md text-sm text-gray-300 transition-colors"
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
          className="w-full py-3 bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 disabled:from-gray-600 disabled:to-gray-600 disabled:cursor-not-allowed rounded-lg font-semibold text-white transition-all shadow-lg"
        >
          {loading ? '预测中...' : '🔮 预测甜味'}
        </button>
      </form>
    </div>
  );
}
