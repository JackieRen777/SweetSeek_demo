/**
 * JSME Molecular Editor Component
 *
 * Loads the locally-hosted JSME (JavaScript Molecular Editor) from /public/jsme/
 * and renders an interactive 2D structure drawing canvas.
 */

import { useEffect, useRef, useState } from 'react';

declare global {
  interface Window {
    JSApplet?: {
      JSME: new (
        containerId: string,
        width: string,
        height: string,
        options: { options?: string }
      ) => JsmeApplet;
    };
    jsmeOnLoad?: () => void;
  }
}

interface JsmeApplet {
  smiles: () => string;
  readGenericMolecularInput: (input: string) => void;
  setCallBack: (event: string, fn: () => void) => void;
}

interface Props {
  onPredict: (smiles: string) => void;
  loading: boolean;
}

export default function JsmeEditor({ onPredict, loading }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const appletRef = useRef<JsmeApplet | null>(null);
  const [currentSmiles, setCurrentSmiles] = useState('');
  const [editorReady, setEditorReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const initApplet = () => {
      if (cancelled) return;
      if (!window.JSApplet || !containerRef.current) {
        setLoadError('JSME library failed to load');
        return;
      }
      try {
        const applet = new window.JSApplet.JSME(
          'jsme-container',
          '100%',
          '100%',
          { options: 'query,hydrogens,newLook,star' }
        );
        applet.setCallBack('AfterStructureModified', () => {
          try {
            const smi = applet.smiles();
            setCurrentSmiles(smi);
          } catch {
            /* ignore intermediate-state errors */
          }
        });
        appletRef.current = applet;
        setEditorReady(true);
      } catch (err) {
        console.error('[JSME] init failed', err);
        setLoadError('Failed to initialize JSME editor');
      }
    };

    // JSME exposes a global `jsmeOnLoad` hook fired once GWT bootstrap completes.
    window.jsmeOnLoad = initApplet;

    if (window.JSApplet) {
      // Already loaded earlier in the session
      initApplet();
    } else {
      const existing = document.querySelector<HTMLScriptElement>(
        'script[data-jsme-loader="1"]'
      );
      if (existing) {
        // Another instance is already loading it; jsmeOnLoad will fire
        return;
      }
      const script = document.createElement('script');
      script.src = '/jsme/jsme.nocache.js';
      script.async = true;
      script.dataset.jsmeLoader = '1';
      script.onerror = () => setLoadError('Could not load /jsme/jsme.nocache.js');
      document.head.appendChild(script);
    }

    return () => {
      cancelled = true;
    };
  }, []);

  const handlePredict = () => {
    const smi = currentSmiles.trim();
    if (smi) onPredict(smi);
  };

  const loadExample = (smiles: string) => {
    if (appletRef.current) {
      appletRef.current.readGenericMolecularInput(smiles);
      setCurrentSmiles(smiles);
    } else {
      setCurrentSmiles(smiles);
    }
  };

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4 text-slate-700">Draw Molecular Structure</h3>

      {/* JSME Editor Canvas — 3:2 aspect ratio, capped width, centered */}
      <div className="bg-white rounded-lg mb-4 overflow-hidden border border-slate-300 relative aspect-[3/2] w-full max-w-[600px] mx-auto">
        <div
          id="jsme-container"
          ref={containerRef}
          className="w-full h-full"
        />
        {!editorReady && !loadError && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 text-slate-500 text-sm">
            Loading molecular editor...
          </div>
        )}
        {loadError && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/90 text-red-600 text-sm px-6 text-center">
            {loadError}
          </div>
        )}
      </div>

      {/* Live SMILES preview */}
      <div className="mb-4">
        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">
          Current SMILES
        </p>
        <code className="block w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-md text-sm text-slate-700 font-mono break-all min-h-[2.25rem]">
          {currentSmiles || <span className="text-slate-400">Draw a structure to generate SMILES…</span>}
        </code>
      </div>

      {/* Example Molecules */}
      <div className="mb-4">
        <p className="text-sm text-slate-600 mb-2 font-medium">Load Example:</p>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => loadExample('CCO')}
            className="px-3 py-1.5 bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 rounded-md text-sm text-slate-700"
            disabled={loading}
          >
            Ethanol
          </button>
          <button
            onClick={() => loadExample('C1=CC=C(C=C1)O')}
            className="px-3 py-1.5 bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 rounded-md text-sm text-slate-700"
            disabled={loading}
          >
            Phenol
          </button>
          <button
            onClick={() => loadExample('C1=CC=C2C(=C1)C(=O)NS2(=O)=O')}
            className="px-3 py-1.5 bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 rounded-md text-sm text-slate-700"
            disabled={loading}
          >
            Saccharin
          </button>
          <button
            onClick={() => loadExample('C(C1C(C(C(C(O1)OC2(C(C(C(O2)CO)O)O)CO)O)O)O)O')}
            className="px-3 py-1.5 bg-white border border-slate-300 hover:border-blue-500 hover:bg-blue-50 rounded-md text-sm text-slate-700"
            disabled={loading}
          >
            Sucrose
          </button>
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={handlePredict}
        disabled={loading || !currentSmiles.trim()}
        className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed rounded-lg font-semibold text-white transition-colors"
      >
        {loading ? 'Predicting...' : 'Predict Sweetness'}
      </button>

      <p className="text-xs text-slate-500 mt-3 text-center">
        Powered by JSME — JavaScript Molecular Editor
      </p>
    </div>
  );
}
