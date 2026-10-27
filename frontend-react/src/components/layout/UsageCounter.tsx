import { useEffect, useState } from 'react';
import { USAGE_UPDATED, type UsageSummary } from '../../lib/usageAnalytics';

const UsageCounter = () => {
  const [summary, setSummary] = useState<UsageSummary | null>(null);

  useEffect(() => {
    let active = true;
    let pending = false;
    let refreshRequested = false;
    const controller = new AbortController();
    const refresh = async () => {
      if (!active || document.hidden) return;
      if (pending) {
        refreshRequested = true;
        return;
      }
      pending = true;
      try {
        const response = await fetch('/api/usage/summary', { cache: 'no-store', signal: controller.signal });
        if (!response.ok) return;
        const data: UsageSummary = await response.json();
        if (active) setSummary(data);
      } catch {
        // Leave the footer usable when statistics are temporarily unavailable.
      } finally {
        pending = false;
        if (active && refreshRequested) {
          refreshRequested = false;
          void refresh();
        }
      }
    };
    void refresh();
    const onUpdate = () => { void refresh(); };
    window.addEventListener(USAGE_UPDATED, onUpdate);
    document.addEventListener('visibilitychange', onUpdate);
    const timer = window.setInterval(onUpdate, 60_000);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
      window.removeEventListener(USAGE_UPDATED, onUpdate);
      document.removeEventListener('visibilitychange', onUpdate);
    };
  }, []);

  if (!summary) return null;
  return (
    <span
      aria-label="Website usage statistics"
      title={`Today (China Standard Time): ${summary.today.pageViews} visits · ${summary.today.questionsSent} questions sent`}
    >
      Visits: {summary.total.pageViews.toLocaleString('en-US')}
      {' · '}
      Questions sent: {summary.total.questionsSent.toLocaleString('en-US')}
    </span>
  );
};

export default UsageCounter;
