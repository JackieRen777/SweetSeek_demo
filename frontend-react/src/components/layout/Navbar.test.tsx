// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Navbar from './Navbar';

afterEach(() => cleanup());

describe('Navbar', () => {
  it('groups both research Q&A pages under the Proteoglycan category', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="encapsulation" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Proteoglycan' }));
    const qaEntry = screen.getByRole('button', { name: 'Encapsulation Q&A' });
    const proteoglycanEntry = screen.getByRole('button', { name: 'Proteoglycan Q&A' });
    fireEvent.click(qaEntry);

    expect(onNavigate).toHaveBeenCalledWith(7);

    fireEvent.click(screen.getByRole('button', { name: 'Proteoglycan' }));
    fireEvent.click(proteoglycanEntry);
    expect(onNavigate).toHaveBeenCalledWith(9);
  });

  it('places AMBER MD Builder under Dual-Protein', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="md-builder" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Dual-Protein' }));
    fireEvent.click(screen.getByRole('button', { name: 'AMBER MD Builder' }));

    expect(onNavigate).toHaveBeenCalledWith(8);
  });

  it('provides both Proteoglycan entries in the mobile navigation', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="proteoglycan" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Open navigation menu' }));
    fireEvent.click(screen.getByRole('button', { name: 'Proteoglycan Q&A' }));
    expect(onNavigate).toHaveBeenCalledWith(9);
    expect(screen.queryByRole('button', { name: 'Close navigation menu' })).toBeNull();
  });
});
