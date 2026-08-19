import { useState, useEffect, lazy, Suspense } from 'react';
import { motion, useAnimation, AnimatePresence } from 'framer-motion';
import { ArrowDown } from 'lucide-react';
import Background from './components/layout/Background';
import Navbar from './components/layout/Navbar';
import Hero from './features/landing/HeroSection';
import QA from './features/qa/QASection';
import SweetTasteEquationSection from './features/equation/SweetTasteEquationSection';
import Database from './features/database/DatabaseSection';
import SweetPredictionSection from './features/prediction/SweetPredictionSection';
// import ErrorBoundary from './components/ui/ErrorBoundary';
import ErrorBoundary from './components/ui/ErrorBoundary';
import Slider from './components/layout/Slider';
import { useThresholdScroll } from './utils/thresholdScroll';
import { featureFromPath, REVERSE_PATH_MAP, type FeatureType } from './routing';
import { MD_BUILDER_ENABLED } from './featureFlags';

// Lazy load feature components
const ChatInterface = lazy(() => import('./features/qa/components/ChatInterface'));
const SweetTasteEquation = lazy(() => import('./features/equation/components/SweetTasteEquation'));
const DatabaseInterface = lazy(() => import('./features/database/DatabaseInterface'));
const ReferencesList = lazy(() => import('./features/references/components/ReferencesList'));
const DualProteinChatInterface = lazy(() => import('./features/dual-protein/components/DualProteinChatInterface'));
const EncapsulationChatInterface = lazy(() => import('./features/encapsulation/components/EncapsulationChatInterface'));
const ProteoglycanChatInterface = lazy(() => import('./features/proteoglycan/components/ProteoglycanChatInterface'));
const MLPredictSection = lazy(() => import('./features/ml-predict/MLPredictSection'));
const AmberMDBuilder = MD_BUILDER_ENABLED
  ? lazy(() => import('./features/md-builder/AmberMDBuilder'))
  : null;

const SCREEN_COUNT = 5;

function App() {
  const [activeFeature, setActiveFeature] = useState<FeatureType>(() => {
    const feature = featureFromPath(window.location.pathname);
    if (feature === 'md-builder' && window.location.pathname.toLowerCase().replace(/\/$/, '') === '/docking') {
      window.history.replaceState({ feature }, '', REVERSE_PATH_MAP['md-builder']);
    }
    return feature;
  });
  const controls = useAnimation();
  
  // Use custom threshold scroll hook
  const { activeScreen, navigateTo } = useThresholdScroll({
    sectionCount: SCREEN_COUNT,
    thresholdDistance: 60,
    thresholdVelocity: 1.2,
    animationDuration: 600
  });

  // --- URL Routing Logic ---

  // Sync URL when activeFeature changes
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

  // Handle Browser Back/Forward buttons
  useEffect(() => {
    const handlePopState = () => {
       setActiveFeature(featureFromPath(window.location.pathname));
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
      else if (index === 4) { setActiveFeature('references'); return; }
      else if (index === 5) { setActiveFeature('dual-protein'); return; }
      else if (index === 6) { setActiveFeature('ml-predict'); return; }
      else if (index === 7) { setActiveFeature('encapsulation'); return; }
      else if (index === 8 && MD_BUILDER_ENABLED) { setActiveFeature('md-builder'); return; }
      else if (index === 9) { setActiveFeature('proteoglycan'); return; }
      else if (index === 10 && MD_BUILDER_ENABLED) { setActiveFeature('md-builder'); return; }

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
            mdBuilderEnabled={MD_BUILDER_ENABLED}
        />

        {/* Vertical Slider Indicator */}
        <Slider 
            count={SCREEN_COUNT} 
            activeScreen={activeScreen} 
            onNavigate={navigateTo} 
        />

        {/* Scroll Indicator Arrow (Visible on first 3 screens, hidden on last) */}
        <AnimatePresence>
            {activeScreen < SCREEN_COUNT - 1 && (
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

          {/* Section 2: SweetSeek */}
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

          {/* Section 5: Sweetness Prediction */}
          <div className="w-full h-[100vh] pt-[120px] overflow-hidden relative">
            <ErrorBoundary name="SweetPredictionSection">
              <SweetPredictionSection onTryNow={() => handleOpenFeature('ml-predict')} />
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
              className={`fixed inset-0 z-[100] ${
                activeFeature === 'ml-predict'
                  ? 'bg-white'
                  : 'bg-white/95 backdrop-blur-xl'
              }`}
            >
              <div className="w-full h-full overflow-hidden relative flex flex-col pt-[120px]">
                {activeFeature === 'ml-predict' ? (
                  <div className="flex-1 w-full overflow-hidden">
                    <Suspense fallback={<div className="w-full h-full flex items-center justify-center text-slate-400">Loading...</div>}>
                      <MLPredictSection onClose={() => setActiveFeature(null)} />
                    </Suspense>
                  </div>
                ) : (
                  <div className={`flex-1 w-full mx-auto overflow-hidden ${activeFeature === 'qa' || activeFeature === 'dual-protein' || activeFeature === 'encapsulation' || activeFeature === 'proteoglycan' || activeFeature === 'md-builder' ? 'max-w-none px-0 pb-0' : 'max-w-[1600px] px-4 md:px-8 pb-4 md:pb-8'}`}>
                    <div className={`w-full h-full bg-white overflow-hidden relative ${activeFeature === 'qa' || activeFeature === 'dual-protein' || activeFeature === 'encapsulation' || activeFeature === 'proteoglycan' || activeFeature === 'md-builder' ? '' : 'rounded-2xl shadow-lg border border-slate-200'}`}>
                      <Suspense fallback={<div className="w-full h-full flex items-center justify-center text-slate-400">Loading...</div>}>
                        {activeFeature === 'qa' && <ChatInterface />}
                        {activeFeature === 'equation' && <SweetTasteEquation />}
                        {activeFeature === 'database' && <DatabaseInterface />}
                        {activeFeature === 'references' && <ReferencesList />}
                        {activeFeature === 'dual-protein' && <DualProteinChatInterface />}
                        {activeFeature === 'encapsulation' && <EncapsulationChatInterface />}
                        {activeFeature === 'proteoglycan' && <ProteoglycanChatInterface />}
                        {activeFeature === 'md-builder' && AmberMDBuilder && <AmberMDBuilder />}
                      </Suspense>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </ErrorBoundary>
  );
}

export default App;
