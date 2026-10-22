import { useState, useEffect } from 'react';
import type { Session } from '@supabase/supabase-js';
import { motion, useAnimation, AnimatePresence } from 'framer-motion';
import { ArrowDown } from 'lucide-react';
import { supabase } from './lib/supabase';
import { Auth } from './features/auth/Auth';
import Background from './components/layout/Background';
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';
import Hero from './features/landing/HeroSection';
import QA from './features/qa/QASection';
import SweetTasteEquationSection from './features/equation/SweetTasteEquationSection';
import Database from './features/database/DatabaseSection';
import SweetPredictionSection from './features/prediction/SweetPredictionSection';
import ErrorBoundary from './components/ui/ErrorBoundary';
import Slider from './components/layout/Slider';
import { useThresholdScroll } from './utils/thresholdScroll';
import { featureFromPath, REVERSE_PATH_MAP, type FeatureType } from './routing';
import { MD_BUILDER_ENABLED } from './featureFlags';
import { lazy, Suspense } from 'react';

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
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [activeFeature, setActiveFeature] = useState<FeatureType>(() => {
    const feature = featureFromPath(window.location.pathname);
    if (feature === 'md-builder' && window.location.pathname.toLowerCase().replace(/\/$/, '') === '/docking') {
      window.history.replaceState({ feature }, '', REVERSE_PATH_MAP['md-builder']);
    }
    return feature;
  });
  const controls = useAnimation();

  const { activeScreen, navigateTo } = useThresholdScroll({
    enabled: !activeFeature,
    sectionCount: SCREEN_COUNT,
    thresholdDistance: 60,
    thresholdVelocity: 1.2,
    animationDuration: 600
  });

  // Check authentication status
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

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

  useEffect(() => {
    controls.start({
      y: `-${activeScreen * 100}vh`,
      transition: { duration: 0.6, ease: "easeInOut" }
    });
  }, [activeScreen, controls]);

  // Features that require authentication
  const authRequiredFeatures: FeatureType[] = ['qa', 'dual-protein', 'encapsulation', 'proteoglycan', 'ml-predict'];

  const handleOpenFeature = (feature: FeatureType) => {
    // Check if feature requires authentication
    if (authRequiredFeatures.includes(feature) && !session) {
      setShowAuthModal(true);
      return;
    }
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

      // Map index to feature and check authentication
      let targetFeature: FeatureType = null;
      if (index === 1) targetFeature = 'qa';
      else if (index === 2) targetFeature = 'equation';
      else if (index === 3) targetFeature = 'database';
      else if (index === 4) targetFeature = 'references';
      else if (index === 5) targetFeature = 'dual-protein';
      else if (index === 6) targetFeature = 'ml-predict';
      else if (index === 7) targetFeature = 'encapsulation';
      else if (index === 8 && MD_BUILDER_ENABLED) targetFeature = 'md-builder';
      else if (index === 9) targetFeature = 'proteoglycan';
      else if (index === 10 && MD_BUILDER_ENABLED) targetFeature = 'md-builder';

      // Check if feature requires authentication
      if (targetFeature && authRequiredFeatures.includes(targetFeature) && !session) {
        setShowAuthModal(true);
        return;
      }

      setActiveFeature(targetFeature);

      // Also scroll to that section in the background
      navigateTo(index);
  };

  // Show loading state
  if (loading) {
    return (
      <div className="w-screen h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="text-slate-400">Loading...</div>
      </div>
    );
  }

  return (
    <ErrorBoundary name="AppRoot">
      <div className="relative w-screen h-screen overflow-hidden text-slate-800">

        <Background />

        {activeFeature !== 'database' && (
          <Navbar
              activeScreen={activeScreen}
              onNavigate={handleNavigate}
              activeFeature={activeFeature}
              mdBuilderEnabled={MD_BUILDER_ENABLED}
              onSignInClick={!session ? () => setShowAuthModal(true) : undefined}
              session={session}
          />
        )}

        {/* Auth Modal */}
        {showAuthModal && !session && (
          <Auth onClose={() => setShowAuthModal(false)} />
        )}

        {/* Vertical Slider Indicator */}
        {!activeFeature && (
          <Slider
              count={SCREEN_COUNT}
              activeScreen={activeScreen}
              onNavigate={navigateTo}
          />
        )}

        {/* Scroll Indicator Arrow (Visible on first 3 screens, hidden on last) */}
        <AnimatePresence>
          {activeScreen < SCREEN_COUNT - 1 && !activeFeature && (
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
          aria-hidden={Boolean(activeFeature)}
          initial={{ y: 0 }}
          animate={controls}
          style={{ touchAction: "none" }}
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

          {/* Section 4: SweetMeta */}
          <div className="w-full h-[100vh] pt-[120px] overflow-hidden relative">
            <ErrorBoundary name="DatabaseSection">
              <Database onTryNow={() => handleOpenFeature('database')} />
            </ErrorBoundary>
          </div>

          {/* Section 5: Sweetness Prediction */}
          <div className="w-full h-[100vh] pt-[120px] pb-[var(--footer-height)] overflow-hidden relative">
            <ErrorBoundary name="SweetPredictionSection">
              <SweetPredictionSection onTryNow={() => handleOpenFeature('ml-predict')} />
            </ErrorBoundary>
            <Footer />
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
              className={`fixed inset-0 z-[100] ${
                activeFeature === 'ml-predict'
                  ? 'bg-white'
                  : 'bg-white/95 backdrop-blur-xl'
              }`}
            >
              <div className={`w-full h-full overflow-hidden relative flex flex-col ${activeFeature === 'database' ? 'pt-0' : 'pt-[120px]'}`}>
                {activeFeature === 'ml-predict' || activeFeature === 'database' ? (
                  <div className="flex-1 w-full overflow-hidden">
                    <Suspense fallback={<div className="w-full h-full flex items-center justify-center text-slate-400">Loading...</div>}>
                      {activeFeature === 'ml-predict' ? <MLPredictSection onClose={() => setActiveFeature(null)} /> : <DatabaseInterface onClose={() => setActiveFeature(null)} />}
                    </Suspense>
                  </div>
                ) : (
                  <div className={`flex-1 w-full mx-auto overflow-hidden ${activeFeature === 'qa' || activeFeature === 'dual-protein' || activeFeature === 'encapsulation' || activeFeature === 'proteoglycan' || activeFeature === 'md-builder' ? 'max-w-none px-0 pb-0' : 'max-w-[1600px] px-4 md:px-8 pb-4 md:pb-8'}`}>
                    <div className={`w-full h-full bg-white overflow-hidden relative ${activeFeature === 'qa' || activeFeature === 'dual-protein' || activeFeature === 'encapsulation' || activeFeature === 'proteoglycan' || activeFeature === 'md-builder' ? '' : 'rounded-2xl shadow-lg border border-slate-200'}`}>
                      <Suspense fallback={<div className="w-full h-full flex items-center justify-center text-slate-400">Loading...</div>}>
                        {activeFeature === 'qa' && <ChatInterface />}
                        {activeFeature === 'equation' && <SweetTasteEquation />}
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
