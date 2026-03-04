import React, { useState } from 'react';
import { Search, Beaker, Filter } from 'lucide-react';
import { motion } from 'framer-motion';
import CompoundThumbnail from './CompoundThumbnail';

interface Compound {
  id: number;
  name: string;
  sweetness?: number | string;
  cid?: number;
  smiles?: string;
}

interface CompoundListProps {
  compounds: Compound[];
  onSelect: (compound: Compound) => void;
  selectedId?: number;
  onSearch: (query: string) => void;
  isLoading: boolean;
}

const CompoundList: React.FC<CompoundListProps> = ({ 
  compounds, 
  onSelect, 
  selectedId, 
  onSearch, 
  isLoading 
}) => {
  const [searchValue, setSearchValue] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchValue);
  };

  return (
    <div className="flex flex-col h-full bg-white border-r border-slate-200 w-full md:w-[400px]">
      <div className="p-4 border-b border-slate-100 space-y-4">
        <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
          <Beaker className="text-blue-600" size={24} />
          Sweet Database
        </h2>
        <form onSubmit={handleSubmit} className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input
            type="text"
            placeholder="Search compounds..."
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-sm"
          />
          {isLoading && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="animate-spin h-4 w-4 border-2 border-blue-500 rounded-full border-t-transparent"></div>
            </div>
          )}
        </form>
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>{compounds.length} results found</span>
          <button className="flex items-center gap-1 hover:text-blue-600 transition-colors">
            <Filter size={14} /> Filter
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {compounds.length > 0 ? (
          <div className="divide-y divide-slate-50">
            {compounds.map((item) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                onClick={() => onSelect(item)}
                className={`p-4 cursor-pointer hover:bg-slate-50 transition-colors flex gap-4 ${
                  selectedId === item.id ? 'bg-blue-50/50 border-l-4 border-blue-500' : 'border-l-4 border-transparent'
                }`}
              >
                <div className="w-12 h-12 flex-shrink-0 flex items-center justify-center">
                   <CompoundThumbnail 
                      name={item.name}
                      cid={item.cid}
                      smiles={item.smiles}
                      size={48}
                      className="w-full h-full object-contain opacity-80"
                   />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-slate-800 truncate">{item.name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
                      {item.sweetness ? `${item.sweetness}x` : 'N/A'}
                    </span>
                    {item.cid && <span className="text-xs text-slate-400">CID: {item.cid}</span>}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8 text-center">
            <Beaker size={48} className="mb-4 opacity-20" />
            <p>No compounds found</p>
            <p className="text-sm mt-2">Try adjusting your search terms</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CompoundList;
