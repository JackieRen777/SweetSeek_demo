import { useState } from 'react';
import type { FormEvent } from 'react';
import { supabase } from '../../lib/supabase';
import './Auth.css';

interface AuthProps {
  onClose: () => void;
}

export function Auth({ onClose }: AuthProps) {
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  const handleSignIn = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) throw error;
      onClose();
    } catch (error: any) {
      setMessage(error.message || 'Sign in failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async () => {
    if (!email || !password) {
      setMessage('Please enter email and password');
      return;
    }

    setLoading(true);
    setMessage('');

    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
      });
      if (error) throw error;
      setMessage('Check your email for the confirmation link!');
    } catch (error: any) {
      setMessage(error.message || 'Sign up failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <div className="auth-modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Welcome to SweetSeek</h2>
        <p className="auth-modal-subtitle">Sign in to continue</p>

        <form onSubmit={handleSignIn} className="auth-modal-form">
          <div className="auth-modal-field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              disabled={loading}
            />
          </div>

          <div className="auth-modal-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              disabled={loading}
              minLength={6}
            />
          </div>

          {message && (
            <div className={`auth-modal-message ${message.includes('error') || message.includes('failed') ? 'error' : 'success'}`}>
              {message}
            </div>
          )}

          <div className="auth-modal-buttons">
            <button type="submit" className="auth-modal-button primary" disabled={loading}>
              {loading ? 'Loading...' : 'Sign in'}
            </button>
            <button type="button" onClick={handleSignUp} className="auth-modal-button secondary" disabled={loading}>
              Sign up
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
