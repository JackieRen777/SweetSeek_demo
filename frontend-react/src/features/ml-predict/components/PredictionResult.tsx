/**
 * Prediction Result (flat layout)
 * Displays prediction label, probability bar, confidence, and SHAP attributions.
 * No card containers — relies on dividers and typography for hierarchy.
 */

import { motion } from 'framer-motion';

interface PredictionData {
  smiles: string;
  smiles_canonical: string;
  is_sweet_pred: number;
  sweet_prob: number;
  shap_top5: Array<{ feature: string; shap: number }>;
  status: string;
}

interface Props {
  data: PredictionData;
}

export default function PredictionResult({ data }: Props) {
  if (data.status !== 'ok') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="border-l-2 border-red-500 pl-4 py-2"
      >
        <h3 className="text-base font-semibold text-red-700 mb-1">Prediction Failed</h3>
        <p className="text-red-600 text-sm">Status: {data.status}</p>
      </motion.div>
    );
  }

  const isSweet = data.is_sweet_pred === 1;
  const prob = data.sweet_prob;
  const confidence =
    Math.abs(prob - 0.5) > 0.3 ? 'High' : Math.abs(prob - 0.5) > 0.15 ? 'Medium' : 'Low';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
      {/* Verdict line — large probability + label, no badge box */}
      <div className="flex items-end justify-between gap-6 flex-wrap">
        <div>
          <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-1">
            Verdict
          </p>
          <div className="flex items-baseline gap-3">
            <span
              className={`text-3xl font-bold tracking-tight ${
                isSweet ? 'text-emerald-600' : 'text-slate-700'
              }`}
            >
              {isSweet ? 'Sweet' : 'Non-Sweet'}
            </span>
            <span className="text-sm text-slate-500">
              confidence {confidence.toLowerCase()}
            </span>
          </div>
        </div>
        <div className="text-right">
          <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-1">
            Sweetness Probability
          </p>
          <p className="text-3xl font-bold text-slate-800 tracking-tight">
            {(prob * 100).toFixed(1)}
            <span className="text-base text-slate-400 font-normal ml-0.5">%</span>
          </p>
        </div>
      </div>

      {/* Probability bar — thin, full-width, with threshold marker */}
      <div>
        <div className="relative w-full h-1.5 bg-slate-200 rounded-full overflow-visible">
          <div
            className="absolute top-0 bottom-0 w-px bg-amber-500 z-10"
            style={{ left: '36%' }}
          >
            <div className="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] text-amber-600 whitespace-nowrap font-medium">
              Threshold
            </div>
          </div>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${prob * 100}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className={`h-full rounded-full ${
              isSweet ? 'bg-emerald-500' : 'bg-slate-400'
            }`}
          />
        </div>
        <div className="flex justify-between text-[10px] text-slate-400 mt-1.5">
          <span>0%</span>
          <span>36%</span>
          <span>100%</span>
        </div>
      </div>

      {/* SMILES — divided list, no card */}
      <div className="border-t border-slate-200/70 pt-5 space-y-3">
        <div>
          <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-1">
            Input SMILES
          </p>
          <code className="text-sm text-slate-700 break-all font-mono">{data.smiles}</code>
        </div>
        {data.smiles !== data.smiles_canonical && (
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-1">
              Canonical SMILES
            </p>
            <code className="text-sm text-slate-700 break-all font-mono">
              {data.smiles_canonical}
            </code>
          </div>
        )}
      </div>

      {/* SHAP — table-like rows, separated by hairlines only */}
      <div className="border-t border-slate-200/70 pt-5">
        <div className="flex items-baseline justify-between mb-3">
          <h4 className="text-sm font-semibold text-slate-800">
            Top feature contributions
          </h4>
          <p className="text-xs text-slate-400">SHAP attribution</p>
        </div>
        <div className="divide-y divide-slate-200/70">
          {data.shap_top5.map((item, idx) => {
            const isPositive = item.shap > 0;
            const absShap = Math.abs(item.shap);
            const maxShap = Math.max(...data.shap_top5.map((f) => Math.abs(f.shap)));
            const barWidth = (absShap / maxShap) * 100;

            return (
              <div key={idx} className="py-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm text-slate-700 font-mono truncate flex-1">
                    <span className="text-slate-400 mr-2">{idx + 1}.</span>
                    {item.feature}
                  </span>
                  <span
                    className={`text-sm font-semibold ml-3 tabular-nums ${
                      isPositive ? 'text-emerald-600' : 'text-rose-600'
                    }`}
                  >
                    {isPositive ? '+' : ''}
                    {item.shap.toFixed(4)}
                  </span>
                </div>
                <div className="relative w-full h-0.5 bg-slate-100 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${barWidth}%` }}
                    transition={{ duration: 0.5, delay: idx * 0.08 }}
                    className={`h-full ${
                      isPositive ? 'bg-emerald-500' : 'bg-rose-500'
                    }`}
                  />
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  {isPositive ? 'Promotes sweetness' : 'Inhibits sweetness'}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
