import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface HeroProps {
  onNext: () => void;
  active?: boolean;
}

const images = ['/homepicture1.png', '/homepicture2.png', '/homepicture3.png', '/homepicture4.png'];
const slideCount = images.length + 1;

const Hero: React.FC<HeroProps> = ({ onNext, active = true }) => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [pageVisible, setPageVisible] = useState(!document.hidden);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    // Leave attenuation to the user's computer and browser volume controls.
    if (videoRef.current) videoRef.current.volume = 1;
  }, []);

  useEffect(() => {
    const onVisibilityChange = () => setPageVisible(!document.hidden);
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let cancelled = false;
    if (active && pageVisible && currentSlide === 0) {
      void video.play().catch((error: unknown) => {
        // Some browsers require muted playback until the user interacts.
        if (cancelled || !(error instanceof DOMException) || error.name !== 'NotAllowedError') return;
        video.muted = true;
        void video.play().catch(() => {
          // Native controls remain available if autoplay is still blocked.
        });
      });
    } else {
      video.pause();
    }
    return () => { cancelled = true; };
  }, [active, pageVisible, currentSlide]);

  useEffect(() => {
    // Let the entire video play before advancing to the original images.
    if (!active || !pageVisible || currentSlide === 0) return;
    const timer = window.setTimeout(() => {
      setCurrentSlide((previous) => (previous + 1) % slideCount);
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [active, pageVisible, currentSlide]);

  const selectSlide = (index: number) => {
    if (index === 0 && currentSlide !== 0 && videoRef.current) {
      videoRef.current.currentTime = 0;
    }
    setCurrentSlide(index);
  };

  return (
    <div className="relative mx-auto flex h-full w-full max-w-[1400px] flex-col justify-center gap-6 px-6 md:flex-row md:items-center md:justify-between md:gap-8 md:px-16">
      <div className="relative z-10 w-full shrink-0 md:w-[45%]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="space-y-5 md:space-y-8"
        >
          <div className="w-full max-w-[600px]">
            <h1 className="text-4xl font-extrabold leading-tight text-slate-800 md:text-6xl">
              Welcome to <br />
              <span className="bg-gradient-to-r from-blue-600 to-indigo-500 bg-clip-text text-transparent">
                SweetSeek
              </span>
            </h1>
            <p className="mt-4 w-full max-w-[520px] text-justify text-base leading-7 tracking-normal text-slate-600 hyphens-auto md:mt-8 md:text-xl md:leading-8">
              Designed by FCN Lab, SweetSeek is a next-generation research interface for sweet science. Powered by comprehensive databases and intelligent algorithms, it drives breakthroughs in sensory science, aiming to facilitate food engineering.
            </p>
          </div>
          <motion.button
            whileHover={{ scale: 1.05, boxShadow: '0 4px 20px rgba(59,130,246,0.3)' }}
            whileTap={{ scale: 0.98 }}
            onClick={onNext}
            className="group relative overflow-hidden rounded-full bg-blue-600 px-8 py-4 text-lg font-bold tracking-wide text-white shadow-lg transition-all duration-300"
          >
            <span className="relative z-10 flex items-center gap-2">Try now！ →</span>
          </motion.button>
        </motion.div>
      </div>

      <section
        aria-label="SweetSeek introduction video and images"
        aria-roledescription="carousel"
        className="relative w-full min-w-0 md:w-[55%]"
        onKeyDown={(event) => event.stopPropagation()}
        onTouchStart={(event) => event.stopPropagation()}
        onTouchEnd={(event) => event.stopPropagation()}
      >
        <div className="relative flex aspect-video max-h-[48vh] w-full items-center justify-center md:aspect-[4/3] md:max-h-[65vh]">
          <video
            ref={videoRef}
            src="/videos/virtual-lab-introduction.mp4"
            playsInline
            controls
            preload={active ? 'metadata' : 'none'}
            aria-label="SweetSeek Virtual Lab Overview"
            hidden={currentSlide !== 0}
            onEnded={() => {
              if (videoRef.current) videoRef.current.currentTime = 0;
              setCurrentSlide(1);
            }}
            className="aspect-video max-h-full w-full rounded-2xl bg-black object-contain shadow-[0_8px_28px_rgba(15,23,42,0.12)]"
          >
            Your browser does not support embedded video.{' '}
            <a href="/videos/virtual-lab-introduction.mp4">Open the introduction video</a>.
          </video>
          <AnimatePresence mode="wait">
            {currentSlide > 0 && (
              <motion.img
                key={currentSlide}
                src={images[currentSlide - 1]}
                alt={`SweetSeek research illustration ${currentSlide}`}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.6, ease: 'easeInOut' }}
                className="absolute max-h-full max-w-full object-contain drop-shadow-2xl"
              />
            )}
          </AnimatePresence>
        </div>
        <div className="mt-3 flex items-center justify-center gap-1" aria-label="Choose a slide">
          {Array.from({ length: slideCount }, (_, index) => (
            <button
              key={index}
              type="button"
              aria-label={index === 0 ? 'Show introduction video' : `Show image ${index}`}
              aria-current={currentSlide === index ? 'true' : undefined}
              onClick={() => selectSlide(index)}
              className="flex h-8 w-8 items-center justify-center rounded-full focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              <span className={`h-2 rounded-full transition-all ${currentSlide === index ? 'w-6 bg-blue-600' : 'w-2 bg-slate-300 hover:bg-slate-400'}`} />
            </button>
          ))}
        </div>
      </section>
    </div>
  );
};

export default Hero;
