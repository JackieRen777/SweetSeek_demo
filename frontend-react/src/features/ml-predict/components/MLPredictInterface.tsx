/**
 * ML Sweetness Prediction Interface
 *
 * Two-stage flow:
 *   1. Landing — dark intro page with SMILES textarea or "Use Molecule Editor"
 *   2. Detail  — flat layout with steps, visualization and SHAP attribution
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import SmilesInput from './SmilesInput';
import JsmeEditor from './JsmeEditor';
import PredictionResult from './PredictionResult';
import MoleculeVisualization from './MoleculeVisualization';
import RegressionResult from './RegressionResult';
import MLPredictLanding from './MLPredictLanding';

type InputMode = 'smiles' | 'draw';
type View = 'landing' | 'detail';

interface PredictionData {
  smiles: string;
  smiles_canonical: string;
  is_sweet_pred: number;
  sweet_prob: number;
  shap_top5: Array<{ feature: string; shap: number }>;
  properties?: {
    mw?: number;
    logp?: number;
    tpsa?: number;
    hba?: number;
    hbd?: number;
    rot_bonds?: number;
    aromatic_rings?: number;
    heavy_atoms?: number;
  };
  regression?: {
    log_sw: number;
    relative_sweetness: number;
    model_r2: number;
  } | null;
  status: string;
}

export default function MLPredictInterface() {
  const [view, setView] = useState<View>('landing');
  const [inputMode, setInputMode] = useState<InputMode>('smiles');
  const [prediction, setPrediction] = useState<PredictionData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePredict = async (smiles: string) => {
    setLoading(true);
    setError(null);
    setPrediction(null);

    try {
      const response = await fetch('/api/ml/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ smiles }),
      });

      const data = await response.json();

      if (!data.success) {
        setError(data.error || 'Prediction failed');
        return;
      }

      setPrediction(data.result);
    } catch (err) {
      setError('Network error, please try again later');
      console.error('Prediction error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleUseEditor = () => {
    setInputMode('draw');
    setView('detail');
  };

  const handleTryNow = () => {
    setInputMode('smiles');
    setView('detail');
  };

  if (view === 'landing') {
    return (
      <MLPredictLanding
        onUseEditor={handleUseEditor}
        onTryNow={handleTryNow}
      />
    );
  }

  return (
    <div className="w-full h-full flex flex-col overflow-hidden">
      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-6 md:px-10 py-8 space-y-12">

          {/* Back to landing */}
          <button
            onClick={() => setView('landing')}
            className="text-xs text-slate-500 hover:text-slate-700 uppercase tracking-[0.15em] font-semibold"
          >
            ← Back
          </button>

          {/* === Section 1: Input === */}
          <section>
            <div className="flex items-baseline gap-3 mb-4 border-b border-slate-200/70 pb-2">
              <span className="text-[11px] uppercase tracking-[0.15em] text-slate-400 font-semibold">
                Step 01
              </span>
              <h2 className="text-base font-semibold text-slate-800">
                Provide a molecular structure
              </h2>
            </div>

            {/* Tabs */}
            <div className="flex gap-6 mb-5">
              {[
                { id: 'smiles', label: 'SMILES Input' },
                { id: 'draw', label: 'Draw Structure' },
              ].map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => setInputMode(mode.id as InputMode)}
                  className={`pb-2 font-medium text-sm transition-all border-b-2 ${
                    inputMode === mode.id
                      ? 'text-blue-600 border-blue-600'
                      : 'text-slate-500 border-transparent hover:text-slate-700'
                  }`}
                >
                  {mode.label}
                </button>
              ))}
            </div>

            <motion.div
              key={inputMode}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25 }}
            >
              {inputMode === 'smiles' && <SmilesInput onPredict={handlePredict} loading={loading} />}
              {inputMode === 'draw' && <JsmeEditor onPredict={handlePredict} loading={loading} />}
            </motion.div>
          </section>

          {/* Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="border-l-2 border-red-500 pl-4 py-2"
            >
              <p className="text-red-700 text-sm font-medium">Error: {error}</p>
            </motion.div>
          )}

          {/* === Section 2: Visualization === */}
          {prediction && (
            <>
              <section>
                <div className="flex items-baseline gap-3 mb-4 border-b border-slate-200/70 pb-2">
                  <span className="text-[11px] uppercase tracking-[0.15em] text-slate-400 font-semibold">
                    Step 02
                  </span>
                  <h2 className="text-base font-semibold text-slate-800">
                    Structure & physicochemical properties
                  </h2>
                </div>
                <MoleculeVisualization
                  smilesCanonical={prediction.smiles_canonical}
                  properties={prediction.properties}
                />
              </section>

              {/* === Section 3: Result === */}
              <section>
                <div className="flex items-baseline gap-3 mb-4 border-b border-slate-200/70 pb-2">
                  <span className="text-[11px] uppercase tracking-[0.15em] text-slate-400 font-semibold">
                    Step 03
                  </span>
                  <h2 className="text-base font-semibold text-slate-800">
                    Prediction & feature attribution
                  </h2>
                </div>
                <PredictionResult data={prediction} />
              </section>

              {/* === Section 4: Sweetness Intensity Regression === */}
              <section>
                <div className="flex items-baseline gap-3 mb-4 border-b border-slate-200/70 pb-2">
                  <span className="text-[11px] uppercase tracking-[0.15em] text-slate-400 font-semibold">
                    Step 04
                  </span>
                  <h2 className="text-base font-semibold text-slate-800">
                    Sweetness intensity estimation
                  </h2>
                </div>
                <RegressionResult
                  data={prediction.regression || null}
                  isSweet={prediction.is_sweet_pred === 1}
                />
              </section>
            </>
          )}

          {/* === Footer: Model meta — inline, not a card === */}
          <section className="pt-6 border-t border-slate-200/70">
            <div className="flex flex-wrap items-end gap-x-10 gap-y-3 text-sm">
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-0.5">Classification</p>
                <p className="text-slate-800 font-medium">3,846 mols · AUC 0.976</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-0.5">Regression</p>
                <p className="text-slate-800 font-medium">741 mols · R² 0.679</p>
              </div>
              <div>
                <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-0.5">Features</p>
                <p className="text-slate-800 font-medium">1,407 dims</p>
              </div>
              <p className="text-xs text-slate-400 ml-auto">
                ECFP4 + MACCS + RDKit 2D · RF + XGBoost ensemble
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
