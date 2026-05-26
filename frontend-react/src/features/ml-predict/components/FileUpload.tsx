/**
 * File Upload Component
 * Supports CSV files with SMILES column
 */

import { useState } from 'react';

interface Props {
  onPredict: (smiles: string) => void;
  loading: boolean;
}

export default function FileUpload({ onPredict, loading }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [smilesList, setSmilesList] = useState<string[]>([]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      parseFile(selectedFile);
    }
  };

  const parseFile = async (file: File) => {
    const text = await file.text();
    const lines = text.split('\n').filter((line) => line.trim());

    // Simple CSV parsing: assume first column is SMILES or has "smiles" header
    const hasHeader = lines[0].toLowerCase().includes('smiles');
    const dataLines = hasHeader ? lines.slice(1) : lines;

    const smiles = dataLines
      .map((line) => line.split(',')[0].trim())
      .filter((s) => s.length > 0);

    setSmilesList(smiles);
  };

  const handlePredict = () => {
    if (smilesList.length > 0) {
      // For now, predict the first SMILES
      // TODO: Implement batch prediction UI
      onPredict(smilesList[0]);
    }
  };

  return (
    <div>
      <h3 className="text-xl font-semibold mb-4 text-gray-200">上传文件</h3>

      <div className="space-y-4">
        {/* File Input */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            选择 CSV 文件 (第一列为 SMILES)
          </label>
          <input
            type="file"
            accept=".csv,.txt"
            onChange={handleFileChange}
            disabled={loading}
            className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg text-white file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-orange-500 file:text-white hover:file:bg-orange-600 file:cursor-pointer"
          />
        </div>

        {/* File Info */}
        {file && (
          <div className="p-4 bg-gray-700 rounded-lg">
            <p className="text-sm text-gray-300">
              <span className="font-semibold">文件名:</span> {file.name}
            </p>
            <p className="text-sm text-gray-300 mt-1">
              <span className="font-semibold">检测到 SMILES:</span> {smilesList.length} 个
            </p>
          </div>
        )}

        {/* SMILES Preview */}
        {smilesList.length > 0 && (
          <div className="p-4 bg-gray-700 rounded-lg max-h-48 overflow-y-auto">
            <p className="text-sm font-semibold text-gray-300 mb-2">预览 (前 10 个):</p>
            <ul className="space-y-1">
              {smilesList.slice(0, 10).map((smiles, idx) => (
                <li key={idx} className="text-sm text-gray-400">
                  {idx + 1}. <code className="text-orange-400">{smiles}</code>
                </li>
              ))}
            </ul>
            {smilesList.length > 10 && (
              <p className="text-sm text-gray-500 mt-2">...还有 {smilesList.length - 10} 个</p>
            )}
          </div>
        )}

        {/* Predict Button */}
        <button
          onClick={handlePredict}
          disabled={loading || smilesList.length === 0}
          className="w-full py-3 bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 disabled:from-gray-600 disabled:to-gray-600 disabled:cursor-not-allowed rounded-lg font-semibold text-white transition-all shadow-lg"
        >
          {loading ? '预测中...' : `🔮 预测第一个分子 (批量预测开发中)`}
        </button>

        <p className="text-xs text-gray-500 text-center">
          💡 提示: 批量预测功能即将推出,当前仅预测第一个 SMILES
        </p>
      </div>
    </div>
  );
}
