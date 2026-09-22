// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Navbar from './Navbar';

afterEach(() => cleanup());

describe('Navbar', () => {
  it('groups Pro-glycan and Encapsulation Q&A under Pro-glycan', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="encapsulation" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Pro-glycan' }));
    fireEvent.click(screen.getByRole('button', { name: 'Pro-glycan Q&A' }));
    expect(onNavigate).toHaveBeenCalledWith(9);

    fireEvent.click(screen.getByRole('button', { name: 'Pro-glycan' }));
    fireEvent.click(screen.getByRole('button', { name: 'Encapsulation Q&A' }));
    expect(onNavigate).toHaveBeenCalledWith(7);
    expect(screen.queryByRole('button', { name: 'Encapsulation' })).toBeNull();
  });

  it('uses AMBER MD Builder as the single structural workflow entry', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="md-builder" onNavigate={onNavigate} mdBuilderEnabled />);

    fireEvent.click(screen.getByRole('button', { name: 'Dual-Protein' }));
    fireEvent.click(screen.getByRole('button', { name: 'AMBER MD Builder' }));
    expect(onNavigate).toHaveBeenCalledWith(8);

    expect(screen.queryByRole('button', { name: 'Docking' })).toBeNull();
  });

  it('hides MD Builder when its feature flag is disabled', () => {
    render(
      <Navbar
        activeScreen={0}
        activeFeature={null}
        onNavigate={vi.fn()}
        mdBuilderEnabled={false}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Dual-Protein' }));
    expect(screen.queryByRole('button', { name: 'AMBER MD Builder' })).toBeNull();
  });

  it('provides both Q&A entries under Pro-glycan in the mobile navigation', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature="proteoglycan" onNavigate={onNavigate} />);

    fireEvent.click(screen.getByRole('button', { name: 'Open navigation menu' }));
    expect(screen.getByRole('button', { name: 'Encapsulation Q&A' })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Pro-glycan Q&A' }));
    expect(onNavigate).toHaveBeenCalledWith(9);
    expect(screen.queryByRole('button', { name: 'Close navigation menu' })).toBeNull();
  });

  it('hides the FCN References entry by default while allowing it to be restored', () => {
    const { rerender } = render(
      <Navbar activeScreen={0} activeFeature={null} onNavigate={vi.fn()} />,
    );

    expect(screen.queryByRole('button', { name: 'References' })).toBeNull();

    rerender(
      <Navbar
        activeScreen={0}
        activeFeature={null}
        onNavigate={vi.fn()}
        referencesNavEnabled
      />,
    );
    expect(screen.getByRole('button', { name: 'References' })).toBeTruthy();
  });

  it('exposes Sweetness before SweetMeta as a top-level navigation destination', () => {
    const onNavigate = vi.fn();
    render(<Navbar activeScreen={0} activeFeature={null} onNavigate={onNavigate} />);

    const sweetMetaButton = screen.getByRole('button', { name: 'SweetMeta' });
    const sweetnessButton = screen.getByRole('button', { name: 'Sweetness' });

    expect(sweetnessButton.compareDocumentPosition(sweetMetaButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    fireEvent.click(sweetMetaButton);
    expect(onNavigate).toHaveBeenCalledWith(3);

    fireEvent.click(sweetnessButton);
    expect(screen.queryByRole('button', { name: 'Sweet Database' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Database' })).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'Open navigation menu' }));
    const mobileSweetMetaButton = screen.getAllByRole('button', { name: 'SweetMeta' })[1];
    const mobileSweetnessLabel = screen.getAllByText('Sweetness')[1];
    expect(mobileSweetnessLabel.compareDocumentPosition(mobileSweetMetaButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    fireEvent.click(mobileSweetMetaButton);
    expect(onNavigate).toHaveBeenLastCalledWith(3);
  });
});
