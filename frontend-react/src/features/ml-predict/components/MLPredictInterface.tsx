/**
 * ML Sweetness Prediction Page
 *
 * Features:
 * - Three input methods: SMILES text, JSME editor, file upload
 * - Real-time prediction with ensemble model
 * - SHAP feature importance visualization
 * - Batch prediction support
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import SmilesInput from './SmilesInput';
import JsmeEditor from './JsmeEditor';
import FileUpload from './FileUpload';
import PredictionResult from './PredictionResult';

type InputMode = 'smiles' | 'draw' | 'file';

interface PredictionData {
  smiles: string;
  smiles_canonical: string;
  is_sweet_pred: number;
  sweet_prob: number;
  shap_top5: Array<{ feature: string; shap: number }>;
  status: string;
}

export default function MLPredictInterface() {
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
        setError(data.error || '预测失败');
        return;
      }

      setPrediction(data.result);
    } catch (err) {
      setError('网络错误，请稍后重试');
      console.error('Prediction error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 text-white">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-orange-400 to-pink-500 bg-clip-text text-transparent">
            🔬 分子甜味预测
          </h1>
          <p className="text-gray-300 text-lg">
            基于 3846 个分子训练的集成模型 (F1=0.82, AUC=0.97)
          </p>
        </motion.div>

        {/* Input Mode Tabs */}
        <div className="flex justify-center mb-8 space-x-4">
          {[
            { id: 'smiles', label: '📝 输入 SMILES', icon: '📝' },
            { id: 'draw', label: '✏️ 画分子结构', icon: '✏️' },
            { id: 'file', label: '📁 上传文件', icon: '📁' },
          ].map((mode) => (
            <button
              key={mode.id}
              onClick={() => setInputMode(mode.id as InputMode)}
              className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                inputMode === mode.id
                  ? 'bg-gradient-to-r from-orange-500 to-pink-500 text-white shadow-lg scale-105'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>

        {/* Input Area */}
        <motion.div
          key={inputMode}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="bg-gray-800 rounded-xl p-8 shadow-2xl mb-8"
        >
          {inputMode === 'smiles' && <SmilesInput onPredict={handlePredict} loading={loading} />}
          {inputMode === 'draw' && <JsmeEditor onPredict={handlePredict} loading={loading} />}
          {inputMode === 'file' && <FileUpload onPredict={handlePredict} loading={loading} />}
        </motion.div>

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="bg-red-900/50 border border-red-500 rounded-lg p-4 mb-8"
          >
            <p className="text-red-200">❌ {error}</p>
          </motion.div>
        )}

        {/* Prediction Result */}
        {prediction && <PredictionResult data={prediction} />}

        {/* Model Info Footer */}
        <div className="mt-12 text-center text-gray-400 text-sm">
          <p>
            模型训练集: 881 Sweet / 2965 NonSweet | 特征维度: 1407 (ECFP4 + MACCS + RDKit2D)
          </p>
          <p className="mt-2">
            验证集性能: Accuracy 90.6% | F1 82.1% | ROC-AUC 96.8%
          </p>
        </div>
      </div>
    </div>
  );
}
