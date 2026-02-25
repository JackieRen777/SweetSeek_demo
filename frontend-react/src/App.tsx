import { useState, useEffect, lazy, Suspense } from 'react';
import { motion, useAnimation, AnimatePresence } from 'framer-motion';
import { ArrowDown } from 'lucide-react';
import Background from './components/layout/Background';
import Navbar from './components/layout/Navbar';
import Hero from './features/landing/HeroSection';
import QA from './features/qa/QASection';
import Equation from './features/equation/EquationSection';
import Database from './features/database/DatabaseSection';
import ErrorBoundary from './components/ui/ErrorBoundary';
import Slider from './components/layout/Slider';
import { useThresholdScroll } from './utils/thresholdScroll';

// Lazy load feature components
const ChatInterface = lazy(() => import('./features/qa/components/ChatInterface'));
const EquationModeler = lazy(() => import('./features/equation/components/EquationModeler'));
const DatabaseInterface = lazy(() => import('./features/database/DatabaseInterface'));

const SCREEN_COUNT = 4;

type FeatureType = 'qa' | 'equation' | 'database' | null;

function App() {
  const [activeFeature, setActiveFeature] = useState<FeatureType>(null);
  const controls = useAnimation();
  
  // Use custom threshold scroll hook
  const { activeScreen, navigateTo } = useThresholdScroll({
    sectionCount: SCREEN_COUNT,
    thresholdDistance: 60,
    thresholdVelocity: 1.2,
    animationDuration: 600
  });

  // Sync animation with active screen
  useEffect(() => {
    controls.start({
      y: `-${activeScreen * 100}vh`,
      transition: { duration: 0.6, ease: "easeInOut" }
    });
  }, [activeScreen, controls]);

  const handleOpenFeature = (feature: FeatureType) => {
    setActiveFeature(feature);
  };

  // Handle navigation from Navbar
  const handleNavigate = (index: number) => {
      // If clicking Home (0), always close modal and go to top
      if (index === 0) {
          setActiveFeature(null);
          navigateTo(0);
          return;
      }
      
      // If clicking other links, check if they map to features
      if (index === 1) setActiveFeature('qa');
      else if (index === 2) setActiveFeature('equation');
      else if (index === 3) setActiveFeature('database');
      
      // Also scroll to that section in the background
      navigateTo(index);
  };

  return (
    <ErrorBoundary name="AppRoot">
      <div className="relative w-screen h-screen overflow-hidden text-slate-800">
        
        <Background />
        
        <Navbar 
            activeScreen={activeScreen} 
            onNavigate={handleNavigate} 
            activeFeature={activeFeature}
        />

        {/* Vertical Slider Indicator */}
        <Slider 
            count={SCREEN_COUNT} 
            activeScreen={activeScreen} 
            onNavigate={navigateTo} 
        />

        {/* Scroll Indicator Arrow (Visible only on first screen) */}
        <AnimatePresence>
            {activeScreen === 0 && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.5 }}
                    className="fixed bottom-8 left-1/2 -translate-x-1/2 z-40 text-slate-400"
                >
                    <motion.div
                        animate={{ y: [0, 10, 0] }}
                        transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                    >
                        <ArrowDown size={32} />
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>

        {/* Main Vertical Scroll Container */}
        <motion.div
          className="flex flex-col w-full h-[400vh]"
          initial={{ y: 0 }}
          animate={controls}
          style={{ touchAction: "none" }} // Disable default browser scrolling
        >
          {/* Section 1: Hero */}
          <div className="w-full h-[100vh] pt-[120px] overflow-hidden relative">
            <ErrorBoundary name="HeroSection">
              <Hero onNext={() => navigateTo(1)} />
            </ErrorBoundary>
          </div>

          {/* Section 2: Professional Q&A */}
          <div className="w-full h-[100vh] pt-[120px] overflow-hidden relative">
            <ErrorBoundary name="QASection">
              <QA onTryNow={() => handleOpenFeature('qa')} />
            </ErrorBoundary>
          </div>

          {/* Section 3: Perception Equation */}
          <div className="w-full h-[100vh] pt-[120px] overflow-hidden relative">
            <ErrorBoundary name="EquationSection">
              <Equation onTryNow={() => handleOpenFeature('equation')} />
            </ErrorBoundary>
          </div>

          {/* Section 4: Database */}
          <div className="w-full h-[100vh] pt-[120px] overflow-hidden relative">
            <ErrorBoundary name="DatabaseSection">
              <Database onTryNow={() => handleOpenFeature('database')} />
            </ErrorBoundary>
          </div>
        </motion.div>

        {/* Feature Modal Overlay */}
        <AnimatePresence>
          {activeFeature && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="fixed inset-0 z-[100] bg-white/95 backdrop-blur-xl"
            >
              <div className="w-full h-full overflow-hidden relative flex flex-col pt-[120px]">
                <div className="flex-1 w-full max-w-[1600px] mx-auto px-4 md:px-8 pb-4 md:pb-8 overflow-hidden">
                  <div className="w-full h-full bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden relative">
                    <Suspense fallback={<div className="w-full h-full flex items-center justify-center text-slate-400">Loading...</div>}>
                      {activeFeature === 'qa' && <ChatInterface />}
                      {activeFeature === 'equation' && <EquationModeler />}
                      {activeFeature === 'database' && <DatabaseInterface />}
                    </Suspense>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </ErrorBoundary>
  );
}

export default App;
