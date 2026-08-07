import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';

interface NavbarProps {
  activeScreen: number;
  onNavigate: (index: number) => void;
  activeFeature: 'qa' | 'equation' | 'database' | 'references' | 'dual-protein' | 'encapsulation' | 'ml-predict' | 'md-builder' | 'docking' | null;
}

interface NavCategory {
  label: string;
  items: Array<{ label: string; index: number; feature: string | null }>;
}

const Navbar: React.FC<NavbarProps> = ({ activeScreen, onNavigate, activeFeature }) => {
  const [openCategory, setOpenCategory] = useState<string | null>(null);

  const categories: NavCategory[] = [
    {
      label: 'Sweetness',
      items: [
        { label: 'Sweet Q&A', index: 1, feature: 'qa' },
        { label: 'Sweet Taste Equation', index: 2, feature: 'equation' },
        { label: 'Sweet Database', index: 3, feature: 'database' },
        { label: 'Sweetness Prediction', index: 6, feature: 'ml-predict' },
      ],
    },
    {
      label: 'Dual-Protein',
      items: [
        { label: 'Dual-Protein Q&A', index: 5, feature: 'dual-protein' },
        { label: 'AMBER MD Builder', index: 8, feature: 'md-builder' },
        { label: 'Docking workspace', index: 9, feature: 'docking' },
      ],
    },
    {
      label: 'Encapsulation',
      items: [
        { label: 'Encapsulation Q&A', index: 7, feature: 'encapsulation' },
      ],
    },
  ];

  // References remains a standalone destination.
  const referencesItem = { label: 'References', index: 4, feature: 'references' };

  const isActive = (item: { feature: string | null }) => {
    if (activeFeature) {
      return activeFeature === item.feature;
    }
    return false;
  };

  const isCategoryActive = (category: NavCategory) => {
    return category.items.some((item) => isActive(item));
  };

  const handleCategoryClick = (categoryLabel: string) => {
    setOpenCategory(openCategory === categoryLabel ? null : categoryLabel);
  };

  const handleItemClick = (item: { index: number; feature: string | null }) => {
    onNavigate(item.index);
    setOpenCategory(null); // Close drawer after selection
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
            <span className="text-[26px] md:text-[30px] lg:text-[36px] font-bold tracking-tight text-slate-800 leading-none">
              SweetSeek
            </span>
          </div>

          {/* Separator */}
          <div className="hidden md:block h-6 w-px bg-slate-200"></div>

          {/* FCN Logo */}
          <div className="hidden md:flex items-center gap-3">
            <a
              href="https://www.x-mol.com/groups/hujun_xie"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:opacity-80 transition-opacity"
            >
              <img
                src="/FCN_logo.png"
                alt="FCN Logo"
                className="h-10 w-auto md:h-12 lg:h-14 object-contain"
              />
            </a>
            <img
              src="/FFHI_logo.jpg"
              alt="食品风味与健康创新团队"
              className="h-[47px] w-auto md:h-[56px] lg:h-[66px] object-contain"
            />
          </div>
        </div>

        {/* Right Section: Category Navigation */}
        <div className="hidden md:flex items-center gap-2 relative">
          {/* Home Button */}
          <button
            onClick={() => onNavigate(0)}
            className={`
              px-5 py-2.5 rounded-full text-base font-medium transition-all duration-300
              ${activeScreen === 0 && !activeFeature
                ? 'text-[var(--color-primary)] bg-blue-50/50'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-slate-50/50'
              }
            `}
          >
            Home
          </button>

          {/* Category Dropdowns */}
          {categories.map((category) => {
            const isOpen = openCategory === category.label;
            const active = isCategoryActive(category);

            return (
              <div key={category.label} className="relative">
                <button
                  onClick={() => handleCategoryClick(category.label)}
                  className={`
                    flex items-center gap-1 px-5 py-2.5 rounded-full text-base font-medium transition-all duration-300
                    ${active
                      ? 'text-[var(--color-primary)] bg-blue-50/50'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-slate-50/50'
                    }
                  `}
                >
                  {category.label}
                  <ChevronDown
                    className={`w-4 h-4 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                  />
                </button>

                {/* Dropdown Drawer */}
                <AnimatePresence>
                  {isOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.2 }}
                      className="absolute top-full mt-2 right-0 bg-white rounded-xl shadow-lg border border-slate-200 overflow-hidden min-w-[200px] z-[120]"
                    >
                      {category.items.map((item) => (
                        <button
                          key={item.label}
                          onClick={() => handleItemClick(item)}
                          className={`
                            w-full text-left px-4 py-3 text-sm font-medium transition-colors
                            ${isActive(item)
                              ? 'bg-blue-50 text-[var(--color-primary)]'
                              : 'text-slate-700 hover:bg-slate-50'
                            }
                          `}
                        >
                          {item.label}
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}

          {/* References - Standalone Button */}
          <button
            onClick={() => handleItemClick(referencesItem)}
            className={`
              px-5 py-2.5 rounded-full text-base font-medium transition-all duration-300
              ${isActive(referencesItem)
                ? 'text-[var(--color-primary)] bg-blue-50/50'
                : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-slate-50/50'
              }
            `}
          >
            References
          </button>
        </div>

        {/* Mobile Menu Button (placeholder for future mobile support) */}
        <div className="md:hidden">
          <button className="p-2 text-slate-600 hover:text-slate-800">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
