/**
 * Sweetness Intensity Regression Result (Step 04)
 * Displays predicted logSw, relative sweetness, and a reference scale.
 */

import { motion } from 'framer-motion';

interface RegressionData {
  log_sw: number;
  relative_sweetness: number;
  model_r2: number;
}

interface Props {
  data: RegressionData | null;
  isSweet: boolean;
}

const REFERENCE_SWEETENERS = [
  { name: 'Lactose', logSw: -0.4, pos: 0 },
  { name: 'Sucrose', logSw: 0, pos: 0 },
  { name: 'Cyclamate', logSw: 1.48, pos: 0 },
  { name: 'Aspartame', logSw: 2.3, pos: 0 },
  { name: 'Sucralose', logSw: 2.78, pos: 0 },
  { name: 'Saccharin', logSw: 2.7, pos: 0 },
  { name: 'Neotame', logSw: 3.9, pos: 0 },
];

export default function RegressionResult({ data, isSweet }: Props) {
  if (!data) {
    return (
      <div className="text-sm text-slate-400 italic">
        Regression model not available
      </div>
    );
  }

  const { log_sw, relative_sweetness, model_r2 } = data;

  const scaleMin = -1;
  const scaleMax = 5;
  const clampedLogSw = Math.max(scaleMin, Math.min(scaleMax, log_sw));
  const predPercent = ((clampedLogSw - scaleMin) / (scaleMax - scaleMin)) * 100;

  const formatSweetness = (rs: number): string => {
    if (rs >= 1000) return `${(rs / 1000).toFixed(1)}k`;
    if (rs >= 100) return rs.toFixed(0);
    if (rs >= 1) return rs.toFixed(1);
    return rs.toFixed(2);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={`space-y-6 ${!isSweet ? 'opacity-60' : ''}`}
    >
      {!isSweet && (
        <div className="border-l-2 border-amber-400 pl-3 py-1">
          <p className="text-xs text-amber-700">
            This molecule is predicted as non-sweet. Intensity estimate is for reference only.
          </p>
        </div>
      )}

      <div className="flex items-end justify-between gap-6 flex-wrap">
        <div>
          <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-1">
            Predicted Sweetness Intensity
          </p>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-800 tracking-tight">
              {formatSweetness(relative_sweetness)}
            </span>
            <span className="text-sm text-slate-500">
              × sucrose
            </span>
          </div>
        </div>
        <div className="text-right">
          <p className="text-[10px] text-slate-400 uppercase tracking-[0.15em] font-semibold mb-1">
            log(Relative Sweetness)
          </p>
          <p className="text-2xl font-bold text-slate-700 tracking-tight">
            {log_sw.toFixed(2)}
          </p>
        </div>
      </div>

      {/* Scale bar with reference sweeteners */}
      <div className="pt-2">
        <div className="relative w-full h-2 bg-gradient-to-r from-slate-200 via-emerald-200 to-emerald-500 rounded-full">
          {/* Prediction marker */}
          <motion.div
            initial={{ left: '0%' }}
            animate={{ left: `${predPercent}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2"
          >
            <div className="w-4 h-4 rounded-full bg-blue-600 border-2 border-white shadow-md" />
            <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] font-semibold text-blue-700 whitespace-nowrap">
              Prediction
            </div>
          </motion.div>

          {/* Reference markers */}
          {REFERENCE_SWEETENERS.map((ref) => {
            const refPercent = ((ref.logSw - scaleMin) / (scaleMax - scaleMin)) * 100;
            if (refPercent < 0 || refPercent > 100) return null;
            return (
              <div
                key={ref.name}
                className="absolute top-full mt-1 -translate-x-1/2"
                style={{ left: `${refPercent}%` }}
              >
                <div className="w-px h-2 bg-slate-400 mx-auto" />
                <p className="text-[9px] text-slate-500 whitespace-nowrap mt-0.5 text-center">
                  {ref.name}
                </p>
              </div>
            );
          })}
        </div>

        {/* Scale labels */}
        <div className="flex justify-between text-[9px] text-slate-400 mt-8">
          <span>0.1×</span>
          <span>1× (sucrose)</span>
          <span>100×</span>
          <span>10,000×</span>
          <span>100,000×</span>
        </div>
      </div>

      {/* Model confidence note */}
      <div className="pt-2 border-t border-slate-200/70">
        <p className="text-xs text-slate-400">
          Pilot model · R² = {model_r2.toFixed(3)} · BrixDB (741 molecules) · Preliminary estimate
        </p>
      </div>
    </motion.div>
  );
}
