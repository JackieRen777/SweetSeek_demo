import React from 'react';
import FeatureSection from '../../components/ui/FeatureSection';
import { Sigma, Activity } from 'lucide-react';

interface SweetTasteEquationSectionProps {
    onTryNow: () => void;
}

const SweetTasteEquationSection: React.FC<SweetTasteEquationSectionProps> = ({ onTryNow }) => {
  return (
    <FeatureSection
      reversed
      title={
        <span>
          Sweet Taste <span className="text-indigo-500">Equation</span>
        </span>
      }
      description="The Sweet Taste Equation transforms computational chemistry into sensory science: by inputting a compound's relative binding free energy (ΔΔG) calculated from molecular simulations, the equation outputs its predicted relative sweetness (Sw) , providing a powerful tool for rational sweetener design."
      onTryNow={onTryNow}
      visualComponent={
        <div className="relative w-96 h-80 bg-slate-900 rounded-2xl shadow-2xl overflow-hidden border border-slate-700 p-6 flex flex-col items-center justify-center group">
            {/* Background Grid */}
            <div className="absolute inset-0 opacity-20">
                 <svg width="100%" height="100%">
                    <pattern id="grid-eq" width="20" height="20" patternUnits="userSpaceOnUse">
                      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="white" strokeWidth="0.5"/>
                    </pattern>
                    <rect width="100%" height="100%" fill="url(#grid-eq)" />
                 </svg>
            </div>

            {/* Glowing Line Chart */}
            <svg viewBox="0 0 200 100" className="w-full h-40 z-10 overflow-visible">
                <path 
                    d="M 0 80 C 40 80, 60 20, 100 50 S 160 80, 200 10" 
                    fill="none" 
                    stroke="url(#gradient-line)" 
                    strokeWidth="4" 
                    strokeLinecap="round"
                    className="drop-shadow-[0_0_10px_rgba(99,102,241,0.5)]"
                />
                <defs>
                    <linearGradient id="gradient-line" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#3B82F6" />
                        <stop offset="100%" stopColor="#6366f1" />
                    </linearGradient>
                </defs>
            </svg>

            {/* Floating Elements */}
            <div className="absolute top-6 left-6 bg-slate-800/80 backdrop-blur-md p-2 rounded-lg border border-slate-600 flex items-center gap-2">
                <Sigma className="text-blue-400" size={16} />
                <span className="text-xs text-slate-300 font-mono">f(x) = sweet</span>
            </div>

            <div className="absolute bottom-6 right-6 bg-slate-800/80 backdrop-blur-md p-2 rounded-lg border border-slate-600 flex items-center gap-2">
                <Activity className="text-indigo-400" size={16} />
                <span className="text-xs text-slate-300 font-mono">R² = 0.98</span>
            </div>
        </div>
      }
    />
  );
};

export default SweetTasteEquationSection;
