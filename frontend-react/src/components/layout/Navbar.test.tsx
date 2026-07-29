// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Navbar from './Navbar';

describe('Navbar', () => {
  it('groups Encapsulation Q&A under the Encapsulation category', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="encapsulation" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Encapsulation' }));
    const qaEntry = screen.getByRole('button', { name: 'Encapsulation Q&A' });
    fireEvent.click(qaEntry);

    expect(onNavigate).toHaveBeenCalledWith(7);
  });
});
