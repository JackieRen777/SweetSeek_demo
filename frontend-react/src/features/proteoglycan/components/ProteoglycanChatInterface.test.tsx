// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ProteoglycanChatInterface from './ProteoglycanChatInterface';

describe('Pro-glycan Q&A', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('uses the Pro-glycan copy and fills a suggestion without sending', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'unavailable', enabled: true }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'warming' }) });
    vi.stubGlobal('fetch', fetchMock);
    render(<ProteoglycanChatInterface />);

    expect(screen.getByRole('heading', { name: /Pro-glycan Q&A\s*Protein-polysaccharide interactions and functional systems/ })).toBeTruthy();
    expect(screen.getByPlaceholderText('Ask anything about protein-polysaccharide systems')).toBeTruthy();
    const suggestion = screen.getByRole('button', { name: '蛋白质与多糖通过哪些相互作用形成复合物？' });
    fireEvent.click(suggestion);
    expect((screen.getByLabelText('Pro-glycan question') as HTMLTextAreaElement).value)
      .toBe('蛋白质与多糖通过哪些相互作用形成复合物？');
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    expect(fetchMock).toHaveBeenCalledWith('/api/proteoglycan/health');
    expect(fetchMock).toHaveBeenCalledWith('/api/proteoglycan/prewarm', { method: 'POST' });
  });

  it('renders the empty knowledge-base error returned by the API', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ready', enabled: true }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ready' }) })
      .mockResolvedValueOnce({
        ok: false,
        statusText: 'Service Unavailable',
        json: async () => ({ error: 'Pro-glycan 知识库尚未建立，请先导入 PDF 并构建索引' }),
      });
    vi.stubGlobal('fetch', fetchMock);
    render(<ProteoglycanChatInterface />);
    fireEvent.change(screen.getByLabelText('Pro-glycan question'), { target: { value: '测试问题' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send question' }));

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText('Pro-glycan 知识库尚未建立，请先导入 PDF 并构建索引')).toBeTruthy();
  });
});
