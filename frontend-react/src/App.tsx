import { useState, useEffect, lazy, Suspense } from 'react';
import { motion, useAnimation, AnimatePresence } from 'framer-motion';
import { ArrowDown } from 'lucide-react';
import Background from './components/layout/Background';
import Navbar from './components/layout/Navbar';
import Hero from './features/landing/HeroSection';
import QA from './features/qa/QASection';
import SweetTasteEquationSection from './features/equation/SweetTasteEquationSection';
import Database from './features/database/DatabaseSection';
// import ErrorBoundary from './components/ui/ErrorBoundary';
import ErrorBoundary from './components/ui/ErrorBoundary';
import Slider from './components/layout/Slider';
import { useThresholdScroll } from './utils/thresholdScroll';

// Lazy load feature components
const ChatInterface = lazy(() => import('./features/qa/components/ChatInterface'));
const SweetTasteEquation = lazy(() => import('./features/equation/components/SweetTasteEquation'));
const DatabaseInterface = lazy(() => import('./features/database/DatabaseInterface'));
const ReferencesList = lazy(() => import('./features/references/components/ReferencesList'));

const SCREEN_COUNT = 4; // Reduced from 5 to 4

type FeatureType = 'qa' | 'equation' | 'database' | 'references' | null;

// URL Mapping
const PATH_MAP: Record<string, FeatureType> = {
  '/professionalq&a': 'qa', // URL is usually lowercase
  '/equation': 'equation',
  '/database': 'database',
  '/references': 'references'
};

const REVERSE_PATH_MAP: Record<string, string> = {
  'qa': '/professionalQ&A', // Displayed URL
  'equation': '/equation',
  'database': '/database',
  'references': '/references'
};

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

  // --- URL Routing Logic ---

  // 1. Initial Load: Check URL and set activeFeature
  useEffect(() => {
    const path = window.location.pathname.toLowerCase();
    // Handle potential trailing slashes
    const cleanPath = path.endsWith('/') && path.length > 1 ? path.slice(0, -1) : path;
    
    // Support both old and new URL patterns for backward compatibility if needed
    // But mainly map /professionalq&a
    let feature = PATH_MAP[cleanPath];
    if (!feature && cleanPath === '/qa') feature = 'qa'; // Fallback support
    
    if (feature) {
      setActiveFeature(feature);
    } else if (cleanPath === '/') {
        setActiveFeature(null);
    }
  }, []);

  // 2. Sync URL when activeFeature changes
  useEffect(() => {
    if (activeFeature) {
      const path = REVERSE_PATH_MAP[activeFeature];
      if (path && window.location.pathname !== path) {
         window.history.pushState({ feature: activeFeature }, '', path);
      }
    } else {
      // If no active feature (Home), revert to /
      if (window.location.pathname !== '/') {
         window.history.pushState({ feature: null }, '', '/');
      }
    }
  }, [activeFeature]);

  // 3. Handle Browser Back/Forward buttons
  useEffect(() => {
    const handlePopState = () => {
       const path = window.location.pathname.toLowerCase();
       const cleanPath = path.endsWith('/') && path.length > 1 ? path.slice(0, -1) : path;
       const feature = PATH_MAP[cleanPath];
       setActiveFeature(feature || null);
    };
    
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // -------------------------

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
      else if (index === 4) {
        // References is no longer a scroll section, open directly
        setActiveFeature('references');
        return; 
      }
      
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

        {/* Scroll Indicator Arrow (Visible on first 4 screens) */}
        <AnimatePresence>
            {activeScreen < 4 && (
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
          className="flex flex-col w-full h-[500vh]"
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

          {/* Section 3: Sweet Taste Equation */}
          <div className="w-full h-[100vh] pt-[120px] overflow-hidden relative">
            <ErrorBoundary name="SweetTasteEquationSection">
              <SweetTasteEquationSection onTryNow={() => handleOpenFeature('equation')} />
            </ErrorBoundary>
          </div>

          {/* Section 4: Sweet Database */}
          <div className="w-full h-[100vh] pt-[120px] overflow-hidden relative">
            <ErrorBoundary name="DatabaseSection">
              <Database onTryNow={() => handleOpenFeature('database')} />
            </ErrorBoundary>
          </div>

          {/* Section 5: References (REMOVED from slider) */}
          {/* 
          <div className="w-full h-[100vh] pt-[120px] overflow-hidden relative">
            <ErrorBoundary name="ReferencesSection">
              <References onOpenList={() => handleOpenFeature('references')} />
            </ErrorBoundary>
          </div> 
          */}
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
                      {activeFeature === 'equation' && <SweetTasteEquation />}
                      {activeFeature === 'database' && <DatabaseInterface />}
                      {activeFeature === 'references' && <ReferencesList />}
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
