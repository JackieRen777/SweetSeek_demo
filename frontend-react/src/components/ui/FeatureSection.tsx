import React from 'react';
import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

interface FeatureSectionProps {
  title: ReactNode;
  description: string;
  onTryNow: () => void;
  visualComponent: ReactNode;
  reversed?: boolean; // If true, visual on left, text on right
}

const FeatureSection: React.FC<FeatureSectionProps> = ({ 
  title, 
  description, 
  onTryNow, 
  visualComponent,
  reversed = false 
}) => {
  return (
    <div className={`w-full h-full flex flex-col ${reversed ? 'md:flex-row-reverse' : 'md:flex-row'} items-center justify-between px-6 md:px-16 max-w-[1400px] mx-auto relative`}>
      
      {/* Text Column */}
      <div className="w-full md:w-[55%] h-full flex flex-col justify-center relative z-10">
        <motion.div
          initial={{ opacity: 0, x: reversed ? 50 : -50 }}
          whileInView={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          className="space-y-8"
        >
          <div className="w-full max-w-[600px]">
            <h2 className="text-4xl md:text-5xl font-bold text-slate-800 leading-tight">
              {title}
            </h2>
            <p className="mt-8 text-lg md:text-xl text-slate-600 leading-8 text-justify hyphens-auto w-full max-w-[520px] tracking-normal">
              {description}
            </p>
          </div>

          <motion.button
            whileHover={{ scale: 1.05, boxShadow: "0 4px 20px rgba(59,130,246,0.3)" }}
            whileTap={{ scale: 0.98 }}
            onClick={onTryNow}
            className="
              group relative px-8 py-3 rounded-xl 
              bg-white border border-slate-200
              text-slate-800 font-bold text-lg tracking-wide
              hover:border-blue-500 hover:text-blue-600
              overflow-hidden shadow-sm transition-all duration-300
            "
          >
            <span className="relative z-10 flex items-center gap-2">
              Try now <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
            </span>
          </motion.button>
        </motion.div>
      </div>

      {/* Visual Column */}
      <div className="w-full md:w-[45%] h-[40vh] md:h-full flex items-center justify-center relative z-0">
        <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="w-full h-full flex items-center justify-center"
        >
            {visualComponent}
        </motion.div>
      </div>
    </div>
  );
};

export default FeatureSection;
