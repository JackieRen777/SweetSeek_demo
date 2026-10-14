import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LogOut } from 'lucide-react';
import type { Session } from '@supabase/supabase-js';
import { supabase } from '../../lib/supabase';
import './UserMenu.css';

interface UserMenuProps {
  session: Session;
}

export default function UserMenu({ session }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [daysJoined, setDaysJoined] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);

  const userEmail = session.user.email || '';
  const userInitial = userEmail.charAt(0).toUpperCase();

  // Calculate days since joined
  useEffect(() => {
    if (session.user.created_at) {
      const createdDate = new Date(session.user.created_at);
      const today = new Date();
      const diffTime = Math.abs(today.getTime() - createdDate.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      setDaysJoined(diffDays);
    }
  }, [session.user.created_at]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setIsOpen(false);
  };

  return (
    <div className="user-menu" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="user-menu-trigger"
        aria-label="User menu"
      >
        <div className="user-avatar">
          {userInitial}
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="user-menu-dropdown"
          >
            <div className="user-menu-header">
              <div className="user-menu-avatar-large">
                {userInitial}
              </div>
              <div className="user-menu-info">
                <div className="user-menu-email">{userEmail}</div>
                <div className="user-menu-days">
                  Day {daysJoined} with SweetSeek
                </div>
              </div>
            </div>

            <div className="user-menu-divider"></div>

            <button onClick={handleSignOut} className="user-menu-item sign-out">
              <LogOut size={16} />
              <span>Sign out</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
