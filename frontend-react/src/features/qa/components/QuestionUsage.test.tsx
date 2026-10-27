import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ChatInterface from './ChatInterface';
import DualProteinChatInterface from '../../dual-protein/components/DualProteinChatInterface';
import EncapsulationChatInterface from '../../encapsulation/components/EncapsulationChatInterface';
import ProteoglycanChatInterface from '../../proteoglycan/components/ProteoglycanChatInterface';
import { trackQuestionSent } from '../../../lib/usageAnalytics';

vi.mock('../../../lib/usageAnalytics', () => ({ trackQuestionSent: vi.fn() }));

const ready = () => Promise.resolve({
  ok: true,
  json: async () => ({ status: 'ready', ready: true, enabled: true }),
  body: { getReader: () => ({ read: async () => ({ done: true }) }) },
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});

describe('question submission counters', () => {
  it.each([
    ['sweetness', ChatInterface],
    ['dual-protein', DualProteinChatInterface],
    ['encapsulation', EncapsulationChatInterface],
    ['proteoglycan', ProteoglycanChatInterface],
  ] as const)('counts %s Send once, ignoring blanks, presets and Stop', async (domain, Component) => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(ready));
    render(<Component />);
    const input = screen.getByRole('textbox');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(trackQuestionSent).not.toHaveBeenCalled();
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons.find((button) => !button.getAttribute('aria-label'))!);
    expect(trackQuestionSent).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }));
    fireEvent.click(screen.getByRole('button', { name: 'Stop generating' }));
    await act(async () => { await Promise.resolve(); });
    expect(trackQuestionSent).toHaveBeenCalledTimes(1);
    expect(trackQuestionSent).toHaveBeenCalledWith(domain);
  });

  it('counts Enter-to-send once when initialization retries the answer request', async () => {
    let asks = 0;
    vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => {
      if (url === '/api/ask_stream' && ++asks === 1) {
        return Promise.resolve({ ok: false, json: async () => ({ error: 'not initialized' }) });
      }
      return ready();
    }));
    render(<ChatInterface />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Why does sugar taste sweet?' } });
    await act(async () => { fireEvent.keyDown(screen.getByRole('textbox'), { key: 'Enter' }); });
    expect(asks).toBe(2);
    expect(trackQuestionSent).toHaveBeenCalledTimes(1);
  });
});
