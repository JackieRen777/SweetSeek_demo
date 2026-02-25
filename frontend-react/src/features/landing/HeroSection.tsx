import React from 'react';
import { motion } from 'framer-motion';
import MoleculeViewer from './components/MoleculeViewer';
import { ArrowRight } from 'lucide-react';

interface HeroProps {
  onNext: () => void;
}

const Hero: React.FC<HeroProps> = ({ onNext }) => {
  return (
    <div className="w-full h-full flex flex-col md:flex-row items-center justify-between px-6 md:px-16 max-w-[1400px] mx-auto relative">
      
      {/* Left Column: Text */}
      <div className="w-full md:w-[55%] h-full flex flex-col justify-center relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="space-y-8"
        >
          <div className="w-full max-w-[600px]">
            <h1 className="text-5xl md:text-6xl font-extrabold text-slate-800 leading-tight">
              Welcome to <br />
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-500">
                Sweetseek
              </span>
            </h1>
            <p className="mt-8 text-xl text-slate-600 leading-8 text-justify hyphens-auto w-full max-w-[520px] tracking-normal">
              Explore the molecular science of sweetness through our advanced AI-powered knowledge system.
            </p>
          </div>

          <motion.button
            whileHover={{ scale: 1.05, boxShadow: "0 4px 20px rgba(59,130,246,0.3)" }}
            whileTap={{ scale: 0.98 }}
            onClick={onNext}
            className="
              group relative px-8 py-4 rounded-xl 
              bg-gradient-to-r from-blue-600 to-indigo-500 
              text-white font-bold text-lg tracking-wide
              overflow-hidden shadow-lg transition-all duration-300
            "
          >
            <span className="relative z-10 flex items-center gap-2">
              Try now！ <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
            </span>
          </motion.button>
        </motion.div>
      </div>

      {/* Right Column: 3D Molecule */}
      <div className="w-full md:w-[45%] h-[50vh] md:h-full absolute md:relative top-0 md:top-auto right-0 -z-0 md:z-0 opacity-40 md:opacity-100 pointer-events-none md:pointer-events-auto">
        <MoleculeViewer />
      </div>
    </div>
  );
};

export default Hero;
