/**
 * Landing view for ML Sweetness Prediction.
 * Two entry points:
 *  - SMILES quick input → Try Now!
 *  - Molecule editor (JSME)
 */

interface Props {
  onUseEditor: () => void;
  onTryNow: () => void;
}

export default function MLPredictLanding({ onUseEditor, onTryNow }: Props) {
  return (
    <div className="w-full h-full overflow-y-auto bg-white text-slate-800">
      <div className="max-w-6xl mx-auto px-6 md:px-10 py-12 md:py-16">
        {/* Title */}
        <h1 className="text-center text-3xl md:text-4xl font-bold text-blue-600 tracking-tight mb-12 md:mb-16">
          Sweetness Prediction
        </h1>

        {/* Two-column body */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-16">
          {/* Left: How it works */}
          <div className="flex flex-col">
            <div className="w-10 h-0.5 bg-blue-600 mb-4" />
            <h2 className="text-blue-600 font-bold text-lg mb-4">How it works</h2>
            <p className="text-slate-600 leading-relaxed mb-4">
              Provide the molecular structure as a SMILES string; the machine
              learning model will analyze its structural features and predict
              sweetness intensity.
            </p>
            <div className="mt-auto pt-4">
              <button
                onClick={onTryNow}
                className="px-7 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold tracking-wider uppercase rounded-full transition-colors shadow-sm"
              >
                Try Now!
              </button>
            </div>
          </div>

          {/* Right: Molecule Editor option */}
          <div className="flex flex-col">
            <div className="w-10 h-0.5 bg-blue-600 mb-4" />
            <h2 className="text-blue-600 font-bold text-lg mb-4">Draw a molecule</h2>
            <p className="text-slate-600 leading-relaxed mb-4">
              If you prefer to draw a molecule, use the built-in editor to
              sketch the structure and run the prediction directly.
            </p>
            <div className="mt-auto pt-4">
              <button
                onClick={onUseEditor}
                className="px-7 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold tracking-wider uppercase rounded-full transition-colors shadow-sm"
              >
                Use Molecule Editor
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
