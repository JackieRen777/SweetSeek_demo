import React from 'react';
import FeatureSection from '../../components/ui/FeatureSection';
import { Database as DbIcon, Search, FileText } from 'lucide-react';

interface DatabaseProps {
    onTryNow: () => void;
}

const Database: React.FC<DatabaseProps> = ({ onTryNow }) => {
  return (
    <FeatureSection
      title={
        <span>
          Sweet <span className="text-blue-600">Database</span>
        </span>
      }
      description="Access a comprehensive library of 500+ sweet compounds. Search by chemical structure, sensory profile, or biological activity with advanced filtering capabilities."
      onTryNow={onTryNow}
      visualComponent={
        <div className="relative w-80 h-96">
            {/* Stacked Cards Effect */}
            <div className="absolute top-0 left-0 w-full h-full bg-white rounded-2xl shadow-xl border border-slate-200 transform -rotate-6 scale-95 opacity-60 z-0"></div>
            <div className="absolute top-0 left-0 w-full h-full bg-white rounded-2xl shadow-xl border border-slate-200 transform -rotate-3 scale-98 opacity-80 z-10"></div>
            
            {/* Main Card */}
            <div className="absolute top-0 left-0 w-full h-full bg-white rounded-2xl shadow-2xl border border-slate-100 p-6 z-20 flex flex-col gap-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                            <DbIcon size={20} />
                        </div>
                        <span className="font-bold text-slate-700">SweetDB</span>
                    </div>
                    <Search size={18} className="text-slate-400" />
                </div>

                {/* List Items */}
                {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-center gap-3 p-3 hover:bg-slate-50 rounded-xl transition-colors cursor-pointer group">
                        <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-400 group-hover:bg-blue-100 group-hover:text-blue-500 transition-colors">
                            <FileText size={18} />
                        </div>
                        <div className="flex-1">
                            <div className="h-3 w-24 bg-slate-200 rounded mb-1.5 group-hover:bg-blue-200 transition-colors"></div>
                            <div className="h-2 w-16 bg-slate-100 rounded"></div>
                        </div>
                    </div>
                ))}
                
                <div className="mt-auto pt-4 border-t border-slate-50 flex justify-center">
                    <span className="text-xs font-medium text-slate-400">500+ Records Found</span>
                </div>
            </div>
        </div>
      }
    />
  );
};

export default Database;
