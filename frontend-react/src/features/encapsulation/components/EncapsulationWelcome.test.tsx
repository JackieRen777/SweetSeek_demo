// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import EncapsulationChatInterface from './EncapsulationChatInterface';

describe('Encapsulation welcome experience', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
      if (url.includes('prewarm')) return Promise.resolve({ ok: true });
      return Promise.resolve({
        ok: true,
        body: {
          getReader: () => ({ read: vi.fn().mockResolvedValue({ done: true }) }),
        },
      });
    }));
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('shows the agreed welcome copy without a particle canvas', () => {
    render(<EncapsulationChatInterface />);

    expect(screen.getByRole('heading', { name: /Explore encapsulation science\s*from precise encapsulation to targeted release/ })).toBeTruthy();
    expect(screen.queryByText(/Ask about wall materials/)).toBeNull();
    expect(screen.queryByTestId('encapsulation-particle-scene')).toBeNull();
    expect(screen.getByLabelText('Encapsulation question')).toBeTruthy();
    expect(screen.getByRole('button', { name: '哪些壁材可以提高包埋效率？' })).toBeTruthy();
    expect(screen.getByRole('button', { name: '喷雾干燥如何影响生物活性物质的稳定性？' })).toBeTruthy();
    expect(screen.getByRole('button', { name: '食品递送系统中的释放行为受哪些因素控制？' })).toBeTruthy();

    const suggestions = screen.getByTestId('suggested-questions');
    expect(suggestions.className).toContain('flex-col');
    suggestions.querySelectorAll('button').forEach((button) => {
      expect(button.className.split(/\s+/)).not.toContain('border');
    });
  });

  it('fills the composer without sending when a preset question is selected', () => {
    render(<EncapsulationChatInterface />);
    fireEvent.click(screen.getByRole('button', { name: '喷雾干燥如何影响生物活性物质的稳定性？' }));

    expect((screen.getByLabelText('Encapsulation question') as HTMLTextAreaElement).value)
      .toBe('喷雾干燥如何影响生物活性物质的稳定性？');
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('uses a short fade before revealing the conversation', async () => {
    render(<EncapsulationChatInterface />);
    fireEvent.change(screen.getByLabelText('Encapsulation question'), { target: { value: 'How does spray drying affect stability?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }));

    await act(async () => {
      vi.advanceTimersByTime(400);
      await Promise.resolve();
    });

    expect(screen.getByText('How does spray drying affect stability?')).toBeTruthy();
    expect(screen.queryByTestId('encapsulation-particle-scene')).toBeNull();
  });
});
