/**
 * Prediction Result Display Component
 * Shows prediction label, probability, confidence, and SHAP feature importance
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
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-red-900/50 border border-red-500 rounded-xl p-6"
      >
        <h3 className="text-xl font-semibold text-red-200 mb-2">预测失败</h3>
        <p className="text-red-300">状态: {data.status}</p>
      </motion.div>
    );
  }

  const isSweet = data.is_sweet_pred === 1;
  const prob = data.sweet_prob;
  const confidence =
    Math.abs(prob - 0.5) > 0.3 ? '高' : Math.abs(prob - 0.5) > 0.15 ? '中' : '低';

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-xl p-8 shadow-2xl border border-gray-700"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl font-bold text-white">预测结果</h3>
        <div
          className={`px-4 py-2 rounded-full font-semibold ${
            isSweet
              ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white'
              : 'bg-gradient-to-r from-gray-600 to-gray-700 text-gray-200'
          }`}
        >
          {isSweet ? '🍬 甜味' : '🚫 非甜味'}
        </div>
      </div>

      {/* SMILES */}
      <div className="mb-6 p-4 bg-gray-700/50 rounded-lg">
        <p className="text-sm text-gray-400 mb-1">输入 SMILES</p>
        <code className="text-orange-400 text-sm">{data.smiles}</code>
        {data.smiles !== data.smiles_canonical && (
          <>
            <p className="text-sm text-gray-400 mt-2 mb-1">标准化 SMILES</p>
            <code className="text-orange-400 text-sm">{data.smiles_canonical}</code>
          </>
        )}
      </div>

      {/* Probability Bar */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-300">甜味概率</span>
          <span className="text-lg font-bold text-white">{(prob * 100).toFixed(2)}%</span>
        </div>
        <div className="relative w-full h-8 bg-gray-700 rounded-full overflow-hidden">
          {/* Threshold line at 36% */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-yellow-400 z-10"
            style={{ left: '36%' }}
          >
            <div className="absolute -top-6 left-1/2 transform -translate-x-1/2 text-xs text-yellow-400 whitespace-nowrap">
              阈值 36%
            </div>
          </div>
          {/* Probability fill */}
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${prob * 100}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className={`h-full ${
              isSweet
                ? 'bg-gradient-to-r from-green-500 to-emerald-500'
                : 'bg-gradient-to-r from-gray-500 to-gray-600'
            }`}
          />
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Confidence */}
      <div className="mb-6 p-4 bg-gray-700/30 rounded-lg">
        <p className="text-sm text-gray-400">
          置信度: <span className="font-semibold text-white">{confidence}</span>
        </p>
      </div>

      {/* SHAP Feature Importance */}
      <div>
        <h4 className="text-lg font-semibold text-white mb-4">
          🔍 关键特征 (SHAP 可解释性)
        </h4>
        <div className="space-y-3">
          {data.shap_top5.map((item, idx) => {
            const isPositive = item.shap > 0;
            const absShap = Math.abs(item.shap);
            const maxShap = Math.max(...data.shap_top5.map((f) => Math.abs(f.shap)));
            const barWidth = (absShap / maxShap) * 100;

            return (
              <div key={idx} className="p-3 bg-gray-700/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-300 flex-1 truncate">
                    {idx + 1}. {item.feature}
                  </span>
                  <span
                    className={`text-sm font-semibold ml-2 ${
                      isPositive ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {isPositive ? '↑' : '↓'} {item.shap.toFixed(4)}
                  </span>
                </div>
                <div className="relative w-full h-2 bg-gray-600 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${barWidth}%` }}
                    transition={{ duration: 0.5, delay: idx * 0.1 }}
                    className={`h-full ${
                      isPositive
                        ? 'bg-gradient-to-r from-green-500 to-emerald-500'
                        : 'bg-gradient-to-r from-red-500 to-pink-500'
                    }`}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {isPositive ? '促进甜味' : '抑制甜味'}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Model Info */}
      <div className="mt-6 pt-6 border-t border-gray-700">
        <p className="text-xs text-gray-500 text-center">
          ℹ️ 此预测基于 3846 个分子的训练集 (F1=0.82, AUC=0.97),仅供参考
        </p>
      </div>
    </motion.div>
  );
}
