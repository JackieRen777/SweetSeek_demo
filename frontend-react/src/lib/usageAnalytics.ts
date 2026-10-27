export type QADomain = 'sweetness' | 'dual-protein' | 'encapsulation' | 'proteoglycan';

export interface UsageSummary {
  timezone: string;
  date: string;
  total: { pageViews: number; questionsSent: number };
  today: { pageViews: number; questionsSent: number };
  questionsByDomain: Record<QADomain, { total: number; today: number }>;
}

export const USAGE_UPDATED = 'sweetseek:usage-updated';
let pageViewTracked = false;

const track = (event: 'page_view' | 'question_sent', domain: QADomain | 'site') => {
  // A retry keeps the same ID, so a lost response cannot double the counter.
  const id = globalThis.crypto?.randomUUID?.() ?? 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(
    /[xy]/g,
    (character) => {
      const random = Math.floor(Math.random() * 16);
      return (character === 'x' ? random : (random & 3) | 8).toString(16);
    },
  );
  const body = JSON.stringify({ id, event, domain });
  const deliver = async () => {
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        const response = await fetch('/api/usage/events', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body,
          keepalive: true,
          signal: AbortSignal.timeout(4000),
        });
        if (response.ok) {
          window.dispatchEvent(new Event(USAGE_UPDATED));
          return;
        }
        if (response.status < 500) return;
      } catch {
        // Analytics must never block or interrupt the question request.
      }
      if (attempt === 0) await new Promise((resolve) => window.setTimeout(resolve, 1000));
    }
  };
  void deliver();
};

export const trackPageView = () => {
  if (pageViewTracked) return;
  pageViewTracked = true;
  track('page_view', 'site');
};

// Called once at user submission, outside all knowledge-base retry loops.
export const trackQuestionSent = (domain: QADomain) => track('question_sent', domain);
