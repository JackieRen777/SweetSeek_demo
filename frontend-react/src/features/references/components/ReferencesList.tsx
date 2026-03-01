import React from 'react';
import { motion } from 'framer-motion';
import { BookOpen, ChevronRight } from 'lucide-react';

// Mock data structure based on the user's image
const MOCK_REFERENCES = [
  {
    id: 1,
    title: "Interaction mechanism between zein and β-lactoglobulin: Insights from multi-spectroscopy and molecular dynamics simulation methods.",
    authors: "Chengzhi Liu†, Nan Lv†, Lijuan Dong, Min Huang (黄敏)*, Qing Shen, Gerui Ren, Ruibo Wu, Binju Wang, Zexing Cao, Hujun Xie (谢湖均)*.",
    journal: "Food Hydrocolloids",
    year: 2023,
    volume: "135",
    pages: "108226",
    impactFactor: 11,
    isESI: true,
    rank: "前1%"
  },
  {
    id: 2,
    title: "Highly biologically active and pH-sensitive collagen hydrolysate-chitosan film loaded with red cabbage extracts realizing dynamic visualization and preservation of shrimp freshness.",
    authors: "Gerui Ren, Ying He, Junfei Lv, Ying Zhu, Zhengfang Xue, Yujing Zhan, Yufan Sun, Xin Luo, Ting Li, Yuling Song, Fuge Niu, Min Huang, Sheng Fang, Linglin Fu, Hujun Xie (谢湖均)*.",
    journal: "International Journal of Biological Macromolecules",
    year: 2023,
    volume: "233",
    pages: "123414",
    impactFactor: 9,
    isESI: true,
    rank: "前1%"
  },
  // Add more placeholders as needed
];

const ReferencesList: React.FC = () => {

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
          {MOCK_REFERENCES.map((ref, index) => (
            <motion.div
              key={ref.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="group bg-white p-6 rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all cursor-pointer relative overflow-hidden"
            >
              {/* Rank Badge */}
              <div className="absolute top-0 left-0 bg-slate-100 text-slate-500 text-xs font-mono px-3 py-1 rounded-br-lg font-bold">
                #{index + 1}
              </div>

              <div className="ml-4">
                <h3 className="text-lg font-bold text-slate-900 mb-2 group-hover:text-blue-700 transition-colors leading-snug">
                  {ref.title}
                </h3>
                
                <p className="text-sm text-slate-600 mb-3 leading-relaxed">
                  {ref.authors}
                </p>
                
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
                  <span className="font-serif italic text-slate-800 font-medium">
                    {ref.journal}.
                  </span>
                  <span className="font-bold text-slate-900">
                    {ref.year}
                  </span>
                  <span className="text-slate-600">
                    {ref.volume}, {ref.pages}.
                  </span>
                  
                  {/* Tags */}
                  <div className="flex items-center gap-2 ml-auto">
                    {ref.impactFactor && (
                      <span className="px-2 py-0.5 bg-red-50 text-red-600 text-xs font-bold rounded">
                        IF = {ref.impactFactor}
                      </span>
                    )}
                    {ref.isESI && (
                      <span className="px-2 py-0.5 bg-red-50 text-red-600 text-xs font-bold rounded">
                        ESI高被引论文
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
              
              <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity -mr-2 group-hover:mr-0">
                <ChevronRight className="text-blue-400" />
              </div>
            </motion.div>
          ))}
          
          {/* Placeholder for more content */}
          <div className="text-center py-12 text-slate-400 border-2 border-dashed border-slate-200 rounded-xl">
            <p>More references will be added here...</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReferencesList;
