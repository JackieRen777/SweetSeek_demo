/**
 * ML Prediction Section Wrapper
 * Provides consistent layout with other features
 */

import { lazy, Suspense } from 'react';
import { motion } from 'framer-motion';

const MLPredictInterface = lazy(() => import('./components/MLPredictInterface'));

interface Props {
  onClose: () => void;
}

export default function MLPredictSection({ onClose }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 overflow-y-auto"
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="fixed top-4 right-4 z-50 p-3 bg-gray-800/90 hover:bg-gray-700 rounded-full text-white transition-colors shadow-lg"
        aria-label="关闭"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>

      {/* Content */}
      <div className="min-h-screen">
        <Suspense
          fallback={
            <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex items-center justify-center">
              <div className="text-white text-xl">加载中...</div>
            </div>
          }
        >
          <MLPredictInterface />
        </Suspense>
      </div>
    </motion.div>
  );
}
