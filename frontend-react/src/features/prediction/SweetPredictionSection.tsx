import React from 'react';
import FeatureSection from '../../components/ui/FeatureSection';

interface Props {
  onTryNow: () => void;
}

const SweetPredictionSection: React.FC<Props> = ({ onTryNow }) => (
  <FeatureSection
    reversed
    title={<span>Sweet <span className="text-blue-600">Prediction</span></span>}
    description="Estimate relative sweetness from molecular structure and sensory descriptors. SweetSeek turns chemical insight into a clear, evidence-backed prediction in seconds."
    onTryNow={onTryNow}
    buttonLabel="Try Now！"
    visualComponent={
      <div className="relative w-80 h-96">
        <div className="absolute -inset-10 rounded-full border border-blue-200/60" />
        <div className="absolute -inset-20 rounded-full border border-blue-100/70 rotate-[-20deg]" />
        <div className="relative w-full h-full p-5 bg-white/95 rounded-2xl shadow-2xl border border-slate-100 transform -rotate-3 hover:rotate-0 transition-transform duration-500">
          <div className="flex items-center gap-2 h-8 border-b border-slate-100 text-xs font-bold text-slate-600">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-blue-100" />
            Sweetness model
            <span className="ml-auto text-[10px] text-green-600">LIVE</span>
          </div>
          <div className="relative h-24 mt-3 rounded-xl bg-slate-50 overflow-hidden">
            <span className="absolute left-[22%] top-[38%] w-6 h-6 rounded-full bg-blue-600 ring-4 ring-white shadow-md" />
            <span className="absolute left-[43%] top-[18%] w-6 h-6 rounded-full bg-indigo-600 ring-4 ring-white shadow-md" />
            <span className="absolute left-[62%] top-[54%] w-6 h-6 rounded-full bg-teal-500 ring-4 ring-white shadow-md" />
            <span className="absolute left-[29%] top-[47%] w-[24%] h-1 bg-blue-300 rotate-[-16deg] origin-left" />
            <span className="absolute left-[49%] top-[34%] w-[23%] h-1 bg-blue-300 rotate-[30deg] origin-left" />
            <span className="absolute left-[29%] top-[55%] w-[38%] h-1 bg-blue-200 rotate-[10deg] origin-left" />
          </div>
          <div className="flex items-center h-12 mt-3 px-3 gap-2 rounded-lg border border-slate-200 text-slate-700">
            <span className="text-[10px] text-slate-400">Molecular input</span>
            <strong className="text-sm">Reb-A</strong>
            <span className="ml-auto px-1.5 py-0.5 rounded bg-blue-50 text-[9px] font-extrabold text-blue-600">SMILES</span>
          </div>
          <div className="relative h-16 mt-3 overflow-hidden bg-[linear-gradient(#fff0_95%,#e2e8f0_95%),linear-gradient(90deg,#fff0_95%,#e2e8f0_95%)] bg-[length:18px_18px]">
            <div className="absolute left-3 top-3 w-[74%] h-12 border-t-4 border-blue-600 rounded-[50%] rotate-[-10deg] skew-x-[-22deg]" />
            {[['left-8', 'top-9'], ['left-[30%]', 'top-7'], ['left-[52%]', 'top-5'], ['left-[73%]', 'top-1']].map(([left, top]) => (
              <span key={`${left}-${top}`} className={`absolute ${left} ${top} w-2.5 h-2.5 rounded-full bg-white border-[3px] border-blue-600`} />
            ))}
          </div>
          <div className="grid grid-cols-[1fr_auto] mt-2 p-3 rounded-xl border border-blue-100 bg-blue-50 text-[10px] text-slate-600">
            <span>Predicted relative sweetness</span>
            <strong className="row-span-2 self-center text-2xl text-blue-600">218×</strong>
            <em className="mt-1 not-italic font-bold text-green-600">confidence 0.94</em>
          </div>
        </div>
      </div>
    }
  />
);

export default SweetPredictionSection;
