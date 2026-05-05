import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
// import MoleculeViewer from './components/MoleculeViewer';
import { ArrowRight } from 'lucide-react';

interface HeroProps {
  onNext: () => void;
}

const Hero: React.FC<HeroProps> = ({ onNext }) => {
  // Hero section with image carousel
  const images = ['/homepicture1.png', '/homepicture2.png', '/homepicture3.png', '/homepicture4.png'];
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % images.length);
    }, 3000); // Change image every 3 seconds

    return () => clearInterval(timer);
  }, []);

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
                SweetSeek
              </span>
            </h1>
            <p className="mt-8 text-xl text-slate-600 leading-8 text-justify hyphens-auto w-full max-w-[520px] tracking-normal">
            Designed by FCN Lab, SweetSeek is a next-generation research interface for sweet science. Powered by comprehensive databases and intelligent algorithms, it drives breakthroughs in sensory science, aiming to facilitate food engineering.
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

      {/* Right Column: 3D Molecule / Image Carousel - Absolute Positioning to Break Constraints */}
      <div className="absolute top-0 right-0 w-full md:w-[60%] h-full z-0 flex items-center justify-center overflow-visible pointer-events-none md:pointer-events-auto">
        <div className="w-full h-full relative translate-x-[10%] flex items-center justify-center">
          {/* <MoleculeViewer /> */}
          <AnimatePresence mode="wait">
            <motion.img
              key={currentImageIndex}
              src={images[currentImageIndex]}
              alt="SweetSeek Hero"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.8, ease: "easeInOut" }}
              className="max-w-[80%] max-h-[64%] object-contain drop-shadow-2xl absolute"
            />
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default Hero;
