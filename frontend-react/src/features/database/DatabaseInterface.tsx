import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Beaker, FileText, Activity } from 'lucide-react';

import CompoundList from './components/CompoundList';
import CompoundStructure from './components/CompoundStructure';
import SweetnessChart from './components/SweetnessChart';
import PropertyRadar from './components/PropertyRadar';
import LipinskiBadge from './components/LipinskiBadge';

// Mock data for initial development, will be replaced by API
// import { MOCK_DATA } from './DatabaseInterface'; // Keep existing mock or fetch from API

interface Compound {
  id: number;
  name: string;
  cid?: number;
  formula?: string;
  mw?: number;
  sweetness?: number | string;
  smiles?: string;
  isomeric_smiles?: string;
  inchi?: string;
  inchikey?: string;
  iupac_name?: string;
  logp?: number;
  tpsa?: number;
  hbond_donor?: number;
  hbond_acceptor?: number;
  rotatable_bond?: number;
  heavy_atom?: number;
  qed?: number;
  sa_score?: number;
  lipinski?: number;
  match_score?: number;
  match_source?: string;
  common_name?: string;
  sweetness_potency?: number | string;
  molecular_formula?: string;
  cas_number?: string;
  description?: string;
}

const DatabaseInterface: React.FC = () => {
  const [compounds, setCompounds] = useState<Compound[]>([]);
  const [selectedCompound, setSelectedCompound] = useState<Compound | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showTechnical, setShowTechnical] = useState(false);

  // Load initial data
  useEffect(() => {
    fetchData('');
  }, []);

  const fetchData = async (query: string = '') => {
    setIsLoading(true);
    try {
      // In a real app, replace with actual API call
      // const res = await fetch(`/api/compounds/search?query=${query}`);
      // const data = await res.json();
      
      // Simulating API delay and fuzzy search with mock data for now
      // Or if API is ready, use it:
      const endpoint = query 
        ? `/api/compounds/search` 
        : `/api/compounds?limit=1000`; // Increase limit to fetch all compounds initially
        
      const method = query ? 'POST' : 'GET';
      const body = query ? JSON.stringify({ query, limit: 100 }) : undefined;
      
      const res = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body
      });
      
      const data = await res.json();
      
      if (data.success || Array.isArray(data)) {
        const results = data.results || data.data || []; // Handle both search wrapper and direct array
        setCompounds(results);
        // Only set selected compound if none is currently selected OR if we just performed a search
        if ((!selectedCompound && results.length > 0) || (query && results.length > 0)) {
          setSelectedCompound(results[0]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch compounds:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (query: string) => {
    fetchData(query);
  };

  if (!selectedCompound && compounds.length === 0 && isLoading) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-slate-50">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 rounded-full border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex bg-slate-50 overflow-hidden">
      {/* Left Sidebar - List View */}
      <CompoundList 
        compounds={compounds} 
        onSelect={setSelectedCompound} 
        selectedId={selectedCompound?.id}
        onSearch={handleSearch}
        isLoading={isLoading}
      />

      {/* Right Main View - Detail View */}
      <div className="flex-1 flex flex-col h-full overflow-y-auto bg-white">
        {selectedCompound ? (
          <motion.div 
            key={selectedCompound.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-8 max-w-6xl mx-auto w-full space-y-8"
          >
            {/* Header Section */}
            <div className="flex justify-between items-start border-b border-slate-100 pb-6">
              <div>
                <h1 className="text-3xl font-bold text-slate-900 mb-2">{selectedCompound.name}</h1>
                <div className="flex items-center gap-3 text-sm text-slate-500">
                  <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-mono">
                    {selectedCompound.formula || selectedCompound.molecular_formula || 'Formula N/A'}
                  </span>
                  <span>MW: {selectedCompound.mw || 'N/A'} g/mol</span>
                  {selectedCompound.cas_number && (
                    <span className="text-slate-400">CAS: {selectedCompound.cas_number}</span>
                  )}
                </div>
              </div>
              {/* Export/Share buttons removed */}
            </div>

            {/* Core Visuals Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Structure Viewer (Left Large) */}
              <div className="lg:col-span-5">
                <CompoundStructure 
                  name={selectedCompound.name} 
                  cid={selectedCompound.cid} 
                  smiles={selectedCompound.smiles} 
                />
              </div>

              {/* Key Metrics Cards (Right) */}
              <div className="lg:col-span-7 grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Sweetness Chart */}
                <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm min-h-[280px] h-auto">
                  <SweetnessChart 
                    value={Number(selectedCompound.sweetness || selectedCompound.sweetness_potency || 0)} 
                    name={selectedCompound.name} 
                  />
                </div>

                {/* Lipinski & Basic Props */}
                <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm min-h-[280px] h-auto flex flex-col justify-between">
                  <LipinskiBadge 
                    mw={selectedCompound.mw || 0}
                    logp={selectedCompound.logp || 0}
                    hbondDonor={selectedCompound.hbond_donor || 0}
                    hbondAcceptor={selectedCompound.hbond_acceptor || 0}
                  />
                  
                  <div className="mt-4 pt-4 border-t border-slate-50 grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-xs text-slate-400 uppercase block mb-1">Rotatable Bonds</span>
                      <span className="text-lg font-semibold text-slate-700">{selectedCompound.rotatable_bond || '-'}</span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400 uppercase block mb-1">Heavy Atoms</span>
                      <span className="text-lg font-semibold text-slate-700">{selectedCompound.heavy_atom || '-'}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Properties Dashboard */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Radar Chart */}
              <div className="md:col-span-1 bg-white p-5 rounded-2xl border border-slate-100 shadow-sm min-h-[300px]">
                <PropertyRadar data={{
                  logp: selectedCompound.logp || 0,
                  tpsa: selectedCompound.tpsa || 0,
                  mw: selectedCompound.mw || 0,
                  qed: selectedCompound.qed || 0,
                  sa_score: selectedCompound.sa_score || 0
                }} />
              </div>

              {/* Detailed Metrics Grid */}
              <div className="md:col-span-2 bg-slate-50 p-6 rounded-2xl border border-slate-100">
                <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center gap-2">
                  <Activity size={16} className="text-blue-500" />
                  Physicochemical Properties
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
                  {[
                    { label: 'XLogP3', value: selectedCompound.logp },
                    { label: 'TPSA', value: `${selectedCompound.tpsa} Å²` },
                    { label: 'H-Bond Donors', value: selectedCompound.hbond_donor },
                    { label: 'H-Bond Acceptors', value: selectedCompound.hbond_acceptor },
                    { label: 'QED Score', value: selectedCompound.qed },
                    { label: 'SA Score', value: selectedCompound.sa_score },
                    { label: 'Complexity', value: 'N/A' }, // Placeholder if needed
                    { label: 'Charge', value: '0' }, // Placeholder
                  ].map((prop) => (
                    <div key={prop.label}>
                      <span className="text-xs text-slate-400 block mb-1">{prop.label}</span>
                      <span className="font-medium text-slate-800">{prop.value || '-'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Technical Details (Collapsible) */}
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <button 
                onClick={() => setShowTechnical(!showTechnical)}
                className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
              >
                <span className="font-semibold text-slate-700 flex items-center gap-2">
                  <FileText size={18} className="text-slate-400" />
                  Technical Specifications
                </span>
                {showTechnical ? <ChevronUp size={18} className="text-slate-400" /> : <ChevronDown size={18} className="text-slate-400" />}
              </button>
              
              <AnimatePresence>
                {showTechnical && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="p-6 grid gap-4 bg-white text-sm font-mono text-slate-600 break-all">
                      <div>
                        <span className="text-xs text-slate-400 uppercase block mb-1 font-sans">Canonical SMILES</span>
                        <div className="p-3 bg-slate-50 rounded border border-slate-100 select-all">
                          {selectedCompound.smiles || 'N/A'}
                        </div>
                      </div>
                      {selectedCompound.isomeric_smiles && (
                        <div>
                          <span className="text-xs text-slate-400 uppercase block mb-1 font-sans">Isomeric SMILES</span>
                          <div className="p-3 bg-slate-50 rounded border border-slate-100 select-all">
                            {selectedCompound.isomeric_smiles}
                          </div>
                        </div>
                      )}
                      {selectedCompound.inchi && (
                        <div>
                          <span className="text-xs text-slate-400 uppercase block mb-1 font-sans">InChI</span>
                          <div className="p-3 bg-slate-50 rounded border border-slate-100 select-all">
                            {selectedCompound.inchi}
                          </div>
                        </div>
                      )}
                      {selectedCompound.inchikey && (
                        <div>
                          <span className="text-xs text-slate-400 uppercase block mb-1 font-sans">InChI Key</span>
                          <div className="p-3 bg-slate-50 rounded border border-slate-100 select-all">
                            {selectedCompound.inchikey}
                          </div>
                        </div>
                      )}
                      <div className="flex gap-4 pt-2">
                        {/* PubChem Link Removed */}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="h-12" /> {/* Bottom spacer */}
          </motion.div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
            <Beaker size={64} className="mb-4 opacity-10" />
            <p className="text-lg font-medium text-slate-500">Select a compound to view details</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DatabaseInterface;
