/**
 * JSME Molecular Editor Component
 *
 * Integrates JSME (JavaScript Molecular Editor) for drawing molecules.
 * JSME converts drawn structures to SMILES automatically.
 */

import { useEffect, useRef, useState } from 'react';

interface Props {
  onPredict: (smiles: string) => void;
  loading: boolean;
}

// Declare JSME global type
declare global {
  interface Window {
    JSApplet: any;
  }
}

export default function JsmeEditor({ onPredict, loading }: Props) {
  const editorRef = useRef<HTMLDivElement>(null);
  const jsmeAppletRef = useRef<any>(null);
  const [isJsmeLoaded, setIsJsmeLoaded] = useState(false);
  const [currentSmiles, setCurrentSmiles] = useState('');

  useEffect(() => {
    // Load JSME script
    const script = document.createElement('script');
    script.src = '/jsme/jsme.nocache.js';
    script.async = true;
    script.onload = () => {
      setIsJsmeLoaded(true);
      initializeJsme();
    };
    script.onerror = () => {
      console.error('Failed to load JSME editor');
    };
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  const initializeJsme = () => {
    if (!editorRef.current || !window.JSApplet) return;

    try {
      // Initialize JSME applet
      // Parameters: container_id, width, height
      jsmeAppletRef.current = new window.JSApplet.JSME(
        'jsme-container',
        '100%',
        '500px',
        {
          options: 'query,hydrogens',
        }
      );

      // Set up callback for structure changes
      jsmeAppletRef.current.setCallBack('AfterStructureModified', (jsmeEvent: any) => {
        const smiles = jsmeAppletRef.current.smiles();
        setCurrentSmiles(smiles);
      });
    } catch (error) {
      console.error('Error initializing JSME:', error);
    }
  };

  const handlePredict = () => {
    if (jsmeAppletRef.current) {
      const smiles = jsmeAppletRef.current.smiles();
      if (smiles && smiles.trim()) {
        onPredict(smiles.trim());
      }
    }
  };

  const handleClear = () => {
    if (jsmeAppletRef.current) {
      jsmeAppletRef.current.clear();
      setCurrentSmiles('');
    }
  };

  const loadExample = (smiles: string) => {
    if (jsmeAppletRef.current) {
      jsmeAppletRef.current.readGenericMolecularInput(smiles);
      setCurrentSmiles(smiles);
    }
  };

  return (
    <div>
      <h3 className="text-xl font-semibold mb-4 text-gray-200">画分子结构</h3>

      {/* JSME Editor Container */}
      <div
        id="jsme-container"
        ref={editorRef}
        className="bg-white rounded-lg mb-4 overflow-hidden"
        style={{ minHeight: '500px' }}
      >
        {!isJsmeLoaded && (
          <div className="flex items-center justify-center h-full text-gray-500">
            <p>加载分子编辑器中...</p>
          </div>
        )}
      </div>

      {/* Current SMILES Display */}
      {currentSmiles && (
        <div className="mb-4 p-3 bg-gray-700 rounded-lg">
          <p className="text-sm text-gray-300">
            <span className="font-semibold">当前 SMILES:</span>{' '}
            <code className="text-orange-400">{currentSmiles}</code>
          </p>
        </div>
      )}

      {/* Example Molecules */}
      <div className="mb-4">
        <p className="text-sm text-gray-400 mb-2">快速加载示例:</p>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => loadExample('CCO')}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-md text-sm text-gray-300"
            disabled={loading}
          >
            乙醇
          </button>
          <button
            onClick={() => loadExample('C1=CC=C(C=C1)O')}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-md text-sm text-gray-300"
            disabled={loading}
          >
            苯酚
          </button>
          <button
            onClick={() => loadExample('C1=CC=C2C(=C1)C(=O)NS2(=O)=O')}
            className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded-md text-sm text-gray-300"
            disabled={loading}
          >
            糖精
          </button>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <button
          onClick={handlePredict}
          disabled={loading || !currentSmiles}
          className="flex-1 py-3 bg-gradient-to-r from-orange-500 to-pink-500 hover:from-orange-600 hover:to-pink-600 disabled:from-gray-600 disabled:to-gray-600 disabled:cursor-not-allowed rounded-lg font-semibold text-white transition-all shadow-lg"
        >
          {loading ? '预测中...' : '🔮 预测甜味'}
        </button>
        <button
          onClick={handleClear}
          disabled={loading}
          className="px-6 py-3 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 disabled:cursor-not-allowed rounded-lg font-semibold text-gray-300 transition-colors"
        >
          清空
        </button>
      </div>
    </div>
  );
}
