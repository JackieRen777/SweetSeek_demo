import React, { useState } from 'react';
import { Sliders, Download, BookOpen, Share2, Info } from 'lucide-react';
import OralCavity3D from './OralCavity3D';
import ScientificChart from './ScientificChart';

const EquationModeler: React.FC = () => {
  // State for parameters
  const [deltaG, setDeltaG] = useState<number>(-8.0); // Default value within experimental range
  const [concentration, setConcentration] = useState<number>(5); // mM
  const [receptorDensity, setReceptorDensity] = useState<number>(1.0); // 1.0x baseline
  const [salivaFlow, setSalivaFlow] = useState<number>(1.0); // 1.0x baseline

  // Calculations based on Paper Equation (1): ΔΔG = 10.13 * log10(Sw) - 20.72
  // Inverse for prediction: log10(Sw) = (ΔΔG + 20.72) / 10.13
  const logSw = (deltaG + 20.72) / 10.13;
  const rawSw = Math.pow(10, logSw);
  
  // Adjust perceived sweetness based on physiological factors (heuristic)
  // Higher receptor density -> higher sensitivity (linear?)
  // Higher saliva flow -> wash away -> lower sensitivity (inverse?)
  const perceivedSw = rawSw * receptorDensity * (1 / salivaFlow);

  // Handlers
  const handleExport = () => {
    const csvContent = `data:text/csv;charset=utf-8,DeltaG,Concentration,ReceptorDensity,SalivaFlow,LogSw,RawSw,PerceivedSw\n${deltaG},${concentration},${receptorDensity},${salivaFlow},${logSw.toFixed(4)},${rawSw.toFixed(2)},${perceivedSw.toFixed(2)}`;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "sweetness_prediction.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleCitation = () => {
    const bibtex = `@article{SweetnessEquation2026,
  title={The Sweetness Taste Equation: Transforming Computational Chemistry into Sensory Science},
  author={SweetSeek Research Team},
  journal={Journal of Computational Sensory Science},
  year={2026},
  note={Interactive Model v1.0}
}`;
    navigator.clipboard.writeText(bibtex);
    alert("BibTeX citation copied to clipboard!");
  };

  return (
    <div className="w-full h-full flex flex-col bg-slate-50 overflow-hidden relative">
      
      {/* Main Content Grid */}
      <div className="flex-1 w-full grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        
        {/* Left Panel: Controls (3 Cols) */}
        <div className="lg:col-span-3 h-full bg-white border-r border-slate-200 p-6 overflow-y-auto flex flex-col gap-8 z-10 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
            
            {/* Header Info */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-slate-800">Equation Modeler</h2>
                <div className="flex items-center gap-2">
                     <button 
                        onClick={handleCitation}
                        className="p-2 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Copy Citation"
                    >
                        <BookOpen size={18} />
                    </button>
                    <button 
                        onClick={handleExport}
                        className="p-2 text-slate-500 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                        title="Export Data"
                    >
                        <Download size={18} />
                    </button>
                </div>
            </div>
            
            {/* Equation Display */}
            <div className="bg-slate-900 rounded-xl p-4 text-center shadow-lg relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/20 to-indigo-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                <h3 className="text-xs font-mono text-slate-400 mb-2 uppercase tracking-widest">Governing Equation (Eq 1)</h3>
                <div className="font-serif text-white text-lg md:text-xl italic">
                    <span className="text-indigo-400 font-bold">ΔΔG</span> = 10.13 × log₁₀(Sw) - 20.72
                </div>
            </div>

            {/* Parameters */}
            <div className="space-y-6">
                <div className="flex items-center gap-2 text-slate-800 font-bold border-b border-slate-100 pb-2">
                    <Sliders size={18} className="text-blue-500" />
                    <span>Parameters</span>
                </div>

                {/* Delta G Slider */}
                <div className="space-y-3">
                    <div className="flex justify-between items-center">
                        <label className="text-sm font-medium text-slate-600">Binding Free Energy (ΔΔG)</label>
                        <div className="flex items-center gap-2">
                             <input 
                                type="number"
                                value={deltaG}
                                onChange={(e) => setDeltaG(Math.max(-25, Math.min(15, parseFloat(e.target.value))))}
                                className="w-20 text-right text-xs font-mono bg-slate-100 px-2 py-1 rounded text-slate-700 border border-slate-200 focus:outline-none focus:border-blue-500"
                                step="0.1"
                            />
                            <span className="text-xs font-mono text-slate-500">kcal/mol</span>
                        </div>
                    </div>
                    <input 
                        type="range" 
                        min="-25" 
                        max="15" 
                        step="0.1" 
                        value={deltaG}
                        onChange={(e) => setDeltaG(parseFloat(e.target.value))}
                        className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                    />
                    <p className="text-xs text-slate-400 leading-relaxed">
                        Range based on experimental data: -17.47 (4-Cl) to +8.68 (4-1p-6p-4Cl). Higher ΔΔG correlates with higher sweetness in this model.
                    </p>
                </div>

                {/* Concentration Slider */}
                <div className="space-y-3">
                    <div className="flex justify-between items-center">
                        <label className="text-sm font-medium text-slate-600">Concentration</label>
                        <span className="text-xs font-mono bg-slate-100 px-2 py-1 rounded text-slate-500">{concentration} mM</span>
                    </div>
                    <input 
                        type="range" 
                        min="1" 
                        max="20" 
                        step="1" 
                        value={concentration}
                        onChange={(e) => setConcentration(parseFloat(e.target.value))}
                        className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-500"
                    />
                </div>

                <div className="w-full h-px bg-slate-100 my-2"></div>

                {/* Physiological Factors */}
                <div className="space-y-4">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wide">Physiological Factors</h4>
                    
                    {/* Receptor Density */}
                    <div className="space-y-2">
                        <div className="flex justify-between text-xs text-slate-600">
                            <span>Receptor Density</span>
                            <span>{receptorDensity.toFixed(1)}x</span>
                        </div>
                        <input 
                            type="range" 
                            min="0.5" 
                            max="2.0" 
                            step="0.1" 
                            value={receptorDensity}
                            onChange={(e) => setReceptorDensity(parseFloat(e.target.value))}
                            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-purple-500"
                        />
                    </div>

                    {/* Saliva Flow */}
                    <div className="space-y-2">
                        <div className="flex justify-between text-xs text-slate-600">
                            <span>Saliva Flow Rate</span>
                            <span>{salivaFlow.toFixed(1)}x</span>
                        </div>
                        <input 
                            type="range" 
                            min="0.5" 
                            max="2.0" 
                            step="0.1" 
                            value={salivaFlow}
                            onChange={(e) => setSalivaFlow(parseFloat(e.target.value))}
                            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                        />
                    </div>
                </div>
            </div>

            {/* Result Box */}
            <div className="mt-auto bg-blue-50 rounded-xl p-4 border border-blue-100">
                <div className="text-xs text-blue-600 font-medium mb-1">Predicted Relative Sweetness</div>
                <div className="text-3xl font-bold text-blue-800 tabular-nums">
                    {perceivedSw > 1000000 
                        ? (perceivedSw / 1000000).toFixed(2) + 'M' 
                        : perceivedSw > 1000 
                            ? (perceivedSw / 1000).toFixed(1) + 'k' 
                            : perceivedSw.toFixed(0)}
                    <span className="text-sm font-normal text-blue-400 ml-1">x Sucrose</span>
                </div>
            </div>
        </div>

        {/* Center Panel: 3D Visualization (6 Cols) */}
        <div className="lg:col-span-6 h-[50vh] lg:h-full bg-slate-100 relative p-4 lg:p-6">
            <OralCavity3D 
                receptorDensity={receptorDensity} 
                deltaG={deltaG} 
                concentration={concentration} 
            />
            
            {/* Legend Overlay */}
            <div className="absolute bottom-8 left-8 bg-white/90 backdrop-blur px-4 py-3 rounded-xl border border-white/50 shadow-sm text-xs space-y-2 pointer-events-none">
                <div className="font-bold text-slate-700 mb-1">Visualization Legend</div>
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-pink-500"></span>
                    <span className="text-slate-600">Active T1R2/T1R3 Receptor</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-white border border-slate-300"></span>
                    <span className="text-slate-600">Sweet Molecule</span>
                </div>
            </div>
        </div>

        {/* Right Panel: Charts (3 Cols) */}
        <div className="lg:col-span-3 h-full bg-white border-l border-slate-200 p-6 overflow-y-auto">
            <div className="flex flex-col gap-6">
                <div className="flex items-center gap-2 text-slate-800 font-bold">
                    <div className="p-1 bg-purple-100 rounded text-purple-600">
                        <Share2 size={16} />
                    </div>
                    <span>Data Analysis</span>
                </div>
                
                <ScientificChart 
                    currentDeltaG={deltaG} 
                    currentSw={rawSw} 
                    currentLogSw={logSw}
                />

                <div className="bg-amber-50 rounded-xl p-4 border border-amber-100 flex gap-3 items-start">
                    <Info className="text-amber-500 shrink-0 mt-0.5" size={16} />
                    <p className="text-xs text-amber-700 leading-relaxed">
                        <strong>Insight:</strong> The logarithmic relationship implies that small changes in binding energy (ΔΔG) result in exponential changes in perceived sweetness. A decrease of 1 kcal/mol increases sweetness by ~32,000x.
                    </p>
                </div>
            </div>
        </div>

      </div>
    </div>
  );
};

export default EquationModeler;
