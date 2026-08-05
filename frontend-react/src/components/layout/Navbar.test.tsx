// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Navbar from './Navbar';

afterEach(() => cleanup());

describe('Navbar', () => {
  it('groups Encapsulation Q&A under the Encapsulation category', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="encapsulation" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Encapsulation' }));
    const qaEntry = screen.getByRole('button', { name: 'Encapsulation Q&A' });
    fireEvent.click(qaEntry);

    expect(onNavigate).toHaveBeenCalledWith(7);
  });

  it('places AMBER MD Builder under Dual-Protein', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="md-builder" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Dual-Protein' }));
    fireEvent.click(screen.getByRole('button', { name: 'AMBER MD Builder' }));

    expect(onNavigate).toHaveBeenCalledWith(8);
  });
});
