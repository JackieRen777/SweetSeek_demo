import React from 'react';
import { motion } from 'framer-motion';
import { BookOpen, ExternalLink } from 'lucide-react';

interface ReferencesSectionProps {
  onOpenList: () => void;
}

const ReferencesSection: React.FC<ReferencesSectionProps> = ({ onOpenList }) => {
  return (
    <div className="w-full h-full flex flex-col justify-center items-center px-6 md:px-12 lg:px-24 bg-gradient-to-br from-slate-50 to-blue-50/30">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="max-w-4xl text-center"
      >
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-blue-100 rounded-2xl text-blue-600">
            <BookOpen size={48} />
          </div>
        </div>

        <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight">
          Scientific References
        </h2>
        
        <p className="text-lg md:text-xl text-slate-600 mb-8 max-w-2xl mx-auto leading-relaxed">
          Explore the comprehensive collection of research papers and data sources that power SweetSeek's knowledge base.
        </p>

        <motion.button
          onClick={onOpenList}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="group inline-flex items-center gap-2 px-8 py-4 bg-blue-600 text-white rounded-full font-semibold text-lg shadow-lg hover:bg-blue-700 transition-colors"
        >
          <span>View Reference List</span>
          <ExternalLink size={20} className="group-hover:translate-x-1 transition-transform" />
        </motion.button>
      </motion.div>
    </div>
  );
};

export default ReferencesSection;
