import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BookOpen, ChevronRight, Loader2 } from 'lucide-react';
import * as XLSX from 'xlsx';

interface Reference {
  id: number;
  title: string;
  authors: string;
  journal: string;
  year: number | string;
  volume: string;
  pages: string;
  impactFactor?: number | string;
  esiLabel?: string; // Changed from isESI to esiLabel
  rank?: string;
  webDisplay?: string; // New field for display from 'web' column
  webUrl?: string; // Used for navigation from 'web_hide' column
}

const ReferencesList: React.FC = () => {
  const [references, setReferences] = useState<Reference[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchExcelData = async () => {
      try {
        const response = await fetch('/data/references_template.xlsx');
        if (!response.ok) {
          throw new Error('Failed to fetch Excel file');
        }
        const arrayBuffer = await response.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: 'array' });
        
        // Assuming data is in the first sheet
        const sheetName = workbook.SheetNames[0];
        const sheet = workbook.Sheets[sheetName];
        
        // Convert to JSON
        const jsonData = XLSX.utils.sheet_to_json(sheet);
        
        // Transform data to match Reference interface
        const parsedReferences: Reference[] = jsonData.map((row: any, index: number) => ({
          id: index + 1,
          title: row.Title || '',
          authors: row.Authors || '',
          journal: row.Journal || '',
          year: row.Year || '',
          volume: row.Volume ? String(row.Volume) : '',
          pages: row.Pages ? String(row.Pages) : '',
          impactFactor: row.IF,
          esiLabel: row.IsESI, // Use the string value directly (e.g., "ESI高被引论文")
          rank: row.Rank,
          // 'web' column for display
          webDisplay: row.web || row.Web,
          // 'Web_Hide' column for navigation (adding explicit Web_Hide support)
          webUrl: row.Web_Hide || row.web_hide || row.Web_hide || row.wed_hide || row.Wed_hide, 
        }));

        setReferences(parsedReferences);
      } catch (err) {
        console.error("Error loading references:", err);
        setError('Failed to load references data.');
      } finally {
        setLoading(false);
      }
    };

    fetchExcelData();
  }, []);

  const handleCardClick = (url?: string) => {
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  };

  const highlightAuthor = (authors: string) => {
    // Split by Hujun Xie or Hujun Xie*
    const parts = authors.split(/(Hujun Xie\*?)/g);
    return parts.map((part, i) => 
      part.match(/^Hujun Xie\*?$/) ? <strong key={i} className="font-bold text-slate-900">{part}</strong> : part
    );
  };

  return (
    <div className="w-full h-full flex flex-col bg-slate-50 overflow-hidden">
      {/* Header */}
      <div className="flex-none p-6 md:p-8 border-b border-slate-200 bg-white">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="text-blue-600" />
              References from FCN lab
            </h1>
          </div>
        </div>
      </div>

      {/* List Content */}
      <div className="flex-1 overflow-y-auto p-6 md:p-8">
        <div className="max-w-5xl mx-auto space-y-4">
          {loading ? (
            <div className="flex justify-center items-center py-20">
              <Loader2 className="animate-spin text-blue-600" size={32} />
            </div>
          ) : error ? (
            <div className="text-center py-12 text-red-500 border-2 border-dashed border-red-200 rounded-xl bg-red-50">
              <p>{error}</p>
            </div>
          ) : (
            <>
              {references.map((ref, index) => (
                <motion.div
                  key={ref.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  onClick={() => handleCardClick(ref.webUrl)}
                  className={`group bg-white p-6 rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all relative overflow-hidden ${
                    ref.webUrl ? 'cursor-pointer' : 'cursor-default'
                  }`}
                >
                  {/* Rank Badge */}
                  <div className="absolute top-0 left-0 bg-slate-100 text-slate-500 text-xs font-mono px-3 py-1 rounded-br-lg font-bold">
                    #{index + 1}
                  </div>

                  <div className="ml-4">
                    <h3 className={`text-lg font-bold text-slate-900 mb-2 transition-colors leading-snug ${ref.webUrl ? 'group-hover:text-blue-700' : ''}`}>
                      {ref.title}
                    </h3>
                    
                    <p className="text-sm text-slate-600 mb-3 leading-relaxed">
                      {highlightAuthor(ref.authors)}
                    </p>
                    
                    <div className="flex flex-wrap items-center gap-x-1 gap-y-2 text-sm">
                      <span className="font-serif italic text-slate-800 font-medium">
                        {ref.journal}.
                      </span>
                      <span className="text-slate-600">
                        {/* Display year (bold), web (if present), volume (italic), pages separated by comma */}
                        <span className="font-bold text-slate-900">{ref.year}</span>
                        {ref.webDisplay && <span>, {ref.webDisplay}</span>}
                        {ref.volume && <>, <span className="italic">{ref.volume}</span></>}
                        {ref.pages && <>, {ref.pages}</>}
                        .
                      </span>
                      
                      {/* Tags */}
                      <div className="flex items-center gap-2 ml-auto">
                        {ref.impactFactor && (
                          <span className="px-2 py-0.5 bg-red-50 text-red-600 text-xs font-bold rounded">
                            IF = {ref.impactFactor}
                          </span>
                        )}
                        {ref.esiLabel && (
                          <span className="px-2 py-0.5 bg-red-50 text-red-600 text-xs font-bold rounded">
                            {ref.esiLabel}
                          </span>
                        )}
                        {ref.rank && (
                          <span className="px-2 py-0.5 bg-red-50 text-red-600 text-xs font-bold rounded">
                            {ref.rank}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  {ref.webUrl && (
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity -mr-2 group-hover:mr-0">
                      <ChevronRight className="text-blue-400" />
                    </div>
                  )}
                </motion.div>
              ))}
              
              {/* Placeholder if no data */}
              {references.length === 0 && (
                <div className="text-center py-12 text-slate-400 border-2 border-dashed border-slate-200 rounded-xl">
                  <p>No references found.</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReferencesList;
