// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Navbar from './Navbar';

afterEach(() => cleanup());

describe('Navbar', () => {
  it('keeps Encapsulation and Proteoglycan as separate research domains', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="encapsulation" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Encapsulation' }));
    fireEvent.click(screen.getByRole('button', { name: 'Encapsulation Q&A' }));
    expect(onNavigate).toHaveBeenCalledWith(7);

    fireEvent.click(screen.getByRole('button', { name: 'Proteoglycan' }));
    fireEvent.click(screen.getByRole('button', { name: 'Proteoglycan Q&A' }));
    expect(onNavigate).toHaveBeenCalledWith(9);
  });

  it('places AMBER MD Builder and Docking under Dual-Protein', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="md-builder" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Dual-Protein' }));
    fireEvent.click(screen.getByRole('button', { name: 'AMBER MD Builder' }));
    expect(onNavigate).toHaveBeenCalledWith(8);

    fireEvent.click(screen.getByRole('button', { name: 'Dual-Protein' }));
    fireEvent.click(screen.getByRole('button', { name: 'Docking' }));
    expect(onNavigate).toHaveBeenCalledWith(10);
  });

  it('provides Proteoglycan in the mobile navigation', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="proteoglycan" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Open navigation menu' }));
    fireEvent.click(screen.getByRole('button', { name: 'Proteoglycan Q&A' }));
    expect(onNavigate).toHaveBeenCalledWith(9);
    expect(screen.queryByRole('button', { name: 'Close navigation menu' })).toBeNull();
  });
});
