import React from 'react';
import { motion } from 'framer-motion';

interface SliderProps {
  count: number;
  activeScreen: number;
  onNavigate: (index: number) => void;
}

const Slider: React.FC<SliderProps> = ({ count, activeScreen, onNavigate }) => {
  return (
    <div className="fixed right-8 top-1/2 transform -translate-y-1/2 z-50 flex flex-col items-center gap-4">
      {Array.from({ length: count }).map((_, index) => {
        const isActive = activeScreen === index;
        return (
          <button
            key={index}
            onClick={() => onNavigate(index)}
            className="group relative flex items-center justify-center w-6 h-12 focus:outline-none"
            aria-label={`Scroll to section ${index + 1}`}
          >
            {/* The Line Indicator */}
            <motion.div
              className={`
                w-[2px] rounded-full transition-all duration-300
                ${isActive 
                  ? 'bg-gradient-to-b from-blue-500 to-indigo-500 h-12 shadow-[0_0_10px_rgba(59,130,246,0.5)]' 
                  : 'bg-slate-300/50 h-6 group-hover:bg-slate-400/80 group-hover:h-8'}
              `}
              layoutId="slider-indicator" // Optional: adds layout animation if needed, but simple height change is cleaner here
            />
          </button>
        );
      })}
    </div>
  );
};

export default Slider;
