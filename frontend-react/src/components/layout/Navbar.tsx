import React from 'react';
import { motion } from 'framer-motion';

interface NavbarProps {
  activeScreen: number;
  onNavigate: (index: number) => void;
  activeFeature: 'qa' | 'equation' | 'database' | 'references' | null;
}

const Navbar: React.FC<NavbarProps> = ({ activeScreen, onNavigate, activeFeature }) => {
  const navItems = [
    { label: 'Home', index: 0, feature: null },
    { label: 'Professional Q&A', index: 1, feature: 'qa' },
    { label: 'Sweet Taste Equation', index: 2, feature: 'equation' },
    { label: 'Sweet Database', index: 3, feature: 'database' },
    { label: 'References', index: 4, feature: 'references' },
  ];

  const isActive = (item: typeof navItems[0]) => {
      if (activeFeature) {
          return activeFeature === item.feature;
      }
      return activeScreen === item.index;
  };

  const handleNavigation = (item: typeof navItems[0]) => {
      onNavigate(item.index);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-[110] flex justify-center pointer-events-none px-4 pt-4 md:px-8 md:pt-6">
      <div className="pointer-events-auto flex items-center justify-between px-6 py-3 bg-white/80 backdrop-blur-md border border-white/60 rounded-full shadow-sm hover:shadow-md transition-shadow duration-300 w-full max-w-7xl">
        
        {/* Left Section: Brand + Logo */}
        <div className="flex items-center gap-4">
            {/* SweetSeek Brand */}
            <div 
                className="flex flex-col cursor-pointer group"
                onClick={() => onNavigate(0)}
            >
                <span className="text-[26px] md:text-[30px] lg:text-[36px] font-bold tracking-tight text-slate-800 leading-none">SweetSeek</span>
            </div>

            {/* Separator */}
            <div className="hidden md:block h-6 w-px bg-slate-200"></div>

            {/* FCN Logo Placeholder */}
            <div className="hidden md:flex items-center gap-2">
                 {/* Replace src with actual logo path */}
                 <a 
                    href="https://www.x-mol.com/groups/hujun_xie" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="hover:opacity-80 transition-opacity"
                 >
                     <img 
                        src="/logo_fcn.png" 
                        alt="FCN Logo" 
                        className="h-10 w-auto md:h-12 lg:h-14 object-contain"
                     />
                 </a>
            </div>
        </div>

        {/* Right Section: Navigation Links */}
        <div className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
                const active = isActive(item);
                return (
                    <button
                        key={item.label}
                        onClick={() => handleNavigation(item)}
                        className={`
                            relative px-5 py-2.5 rounded-full text-base font-medium transition-all duration-300 whitespace-nowrap
                            ${active 
                                ? 'text-[var(--color-primary)] bg-blue-50/50' 
                                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-slate-50/50'
                            }
                        `}
                    >
                        {item.label}
                        {active && (
                            <motion.div
                                layoutId="navbar-indicator"
                                className="absolute inset-0 rounded-full border border-blue-100 bg-blue-50/30 -z-10"
                                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                            />
                        )}
                    </button>
                );
            })}
        </div>
        
        {/* Mobile Menu Icon (Placeholder) */}
        <div className="md:hidden text-[var(--text-secondary)]">
             {/* Menu icon */}
             <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 6H20M4 12H20M4 18H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
             </svg>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
