import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('usage event delivery', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('counts one page load despite repeated initialization', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', fetchMock);
    const { trackPageView } = await import('./usageAnalytics');
    trackPageView();
    trackPageView();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toMatchObject({ event: 'page_view', domain: 'site' });
  });

  it('retries a lost response with the same ID and gives new sends new IDs', async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new Error('response lost'))
      .mockResolvedValue({ ok: true });
    vi.stubGlobal('fetch', fetchMock);
    const { trackQuestionSent } = await import('./usageAnalytics');
    trackQuestionSent('sweetness');
    await vi.advanceTimersByTimeAsync(1000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][1].body).toBe(fetchMock.mock.calls[1][1].body);
    trackQuestionSent('sweetness');
    const first = JSON.parse(fetchMock.mock.calls[0][1].body);
    const second = JSON.parse(fetchMock.mock.calls[2][1].body);
    expect(first.id).not.toBe(second.id);
    expect(Object.keys(first).sort()).toEqual(['domain', 'event', 'id']);
  });

  it('keeps submission nonblocking when statistics cannot be delivered', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('offline'));
    vi.stubGlobal('fetch', fetchMock);
    const { trackQuestionSent } = await import('./usageAnalytics');
    expect(() => trackQuestionSent('proteoglycan')).not.toThrow();
    await vi.advanceTimersByTimeAsync(2000);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
