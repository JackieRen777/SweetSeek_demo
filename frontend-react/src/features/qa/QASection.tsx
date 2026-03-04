import React from 'react';
import FeatureSection from '../../components/ui/FeatureSection';
import { MessageCircle, Zap, Shield } from 'lucide-react';

interface QAProps {
    onTryNow: () => void;
}

const QA: React.FC<QAProps> = ({ onTryNow }) => {
  return (
    <FeatureSection
      title={
        <span>
          Professional <span className="text-blue-600">Q&A</span>
        </span>
      }
      description="Get instant, scientifically accurate answers on sweetness, molecular interactions, and sensory data. Our agent is trained on thousands of peer-reviewed papers."
      onTryNow={onTryNow}
      visualComponent={
        <div className="relative w-80 h-96 bg-white rounded-2xl shadow-2xl border border-slate-100 p-6 flex flex-col gap-4 transform rotate-3 hover:rotate-0 transition-transform duration-500">
            {/* Mock Chat UI */}
            <div className="flex items-start gap-3">
                <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 shrink-0">
                    <MessageCircle size={20} />
                </div>
                <div className="bg-slate-50 p-3 rounded-2xl rounded-tl-none text-sm text-slate-600 shadow-sm">
                    How does the receptor T1R2 bind to sucrose?
                </div>
            </div>
            <div className="flex items-start gap-3 flex-row-reverse">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-600 to-indigo-500 flex items-center justify-center text-white font-bold text-sm shrink-0">
                    AI
                </div>
                <div className="bg-blue-600 text-white p-3 rounded-2xl rounded-tr-none text-sm shadow-md">
                    The T1R2 subunit binds sucrose via its Venus Flytrap Domain (VFD), utilizing hydrogen bonds...
                </div>
            </div>
            
            {/* Floating Badges */}
            <div className="absolute -right-8 top-12 bg-white p-3 rounded-xl shadow-lg flex items-center gap-2 animate-bounce">
                <Zap className="text-yellow-500" size={20} />
                <span className="font-bold text-slate-700 text-sm">Fast</span>
            </div>
             <div className="absolute -left-6 bottom-20 bg-white p-3 rounded-xl shadow-lg flex items-center gap-2 animate-pulse">
                <Shield className="text-green-500" size={20} />
                <span className="font-bold text-slate-700 text-sm">Verified</span>
            </div>
        </div>
      }
    />
  );
};

export default QA;
