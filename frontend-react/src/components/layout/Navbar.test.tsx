// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Navbar from './Navbar';

afterEach(() => cleanup());

describe('Navbar', () => {
  it('groups Proteoglycan and Encapsulation Q&A under Proteoglycan', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="encapsulation" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Proteoglycan' }));
    fireEvent.click(screen.getByRole('button', { name: 'Proteoglycan Q&A' }));
    expect(onNavigate).toHaveBeenCalledWith(9);

    fireEvent.click(screen.getByRole('button', { name: 'Proteoglycan' }));
    fireEvent.click(screen.getByRole('button', { name: 'Encapsulation Q&A' }));
    expect(onNavigate).toHaveBeenCalledWith(7);
    expect(screen.queryByRole('button', { name: 'Encapsulation' })).toBeNull();
  });

  it('uses AMBER MD Builder as the single structural workflow entry', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="md-builder" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Dual-Protein' }));
    fireEvent.click(screen.getByRole('button', { name: 'AMBER MD Builder' }));
    expect(onNavigate).toHaveBeenCalledWith(8);

    expect(screen.queryByRole('button', { name: 'Docking' })).toBeNull();
  });

  it('provides both Q&A entries under Proteoglycan in the mobile navigation', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="proteoglycan" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Open navigation menu' }));
    expect(screen.getByRole('button', { name: 'Encapsulation Q&A' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Proteoglycan Q&A' }));
    expect(onNavigate).toHaveBeenCalledWith(9);
    expect(screen.queryByRole('button', { name: 'Close navigation menu' })).toBeNull();
  });
});
