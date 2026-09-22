import { useEffect, useMemo, useState } from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import {
  AlertTriangle, BookOpen, Database, FileCheck2, FlaskConical,
  Library, RefreshCw, Scale, Wheat,
} from 'lucide-react';
import { fetchSweetMetaStatistics, type SweetMetaStatistics } from '../sweetmetaApi';

type QueryValue = string | number | null | undefined;
type Navigate = (params: Record<string, QueryValue>) => void;

const COLORS = ['#3d73b2', '#82baab', '#e8825c', '#c2294a', '#d9cf99', '#b3c8e1'];
const READINESS_COLORS: Record<string, string> = { R1: '#3d73b2', R2: '#82baab', R3: '#d9cf99', R4: '#c2294a' };
const CHART_CURSOR = { fill: '#f0ecd7', fillOpacity: 0.48 };

const humanize = (value: string) => value.replaceAll('-', ' ').replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

interface TooltipEntry {
  name?: string;
  value?: number | string;
  color?: string;
  payload?: Record<string, unknown>;
}

const ScientificTooltip = ({ active, payload, label }: { active?: boolean; payload?: TooltipEntry[]; label?: string }) => {
  if (!active || !payload?.length) return null;
  const source = payload[0]?.payload ?? {};
  return <div className="sdb-chart-tooltip">
    <strong>{label || String(source.label ?? source.key ?? '')}</strong>
    {payload.filter((entry) => Number(entry.value) > 0).map((entry) => <span key={entry.name}><i style={{ background: entry.color }} />{humanize(String(entry.name ?? 'Value'))}<b>{Number(entry.value).toLocaleString()}</b></span>)}
    {typeof source.compounds === 'number' && <small>{source.compounds.toLocaleString()} distinct compounds</small>}
    {typeof source.denominator === 'number' && <small>Public release denominator: {source.denominator.toLocaleString()}</small>}
    {typeof source.percent === 'number' && <small>{source.percent}% compound coverage</small>}
  </div>;
};

const ChartPanel = ({ eyebrow, title, note, children, actions }: { eyebrow: string; title: string; note: string; children: React.ReactNode; actions?: React.ReactNode }) => <section className="sdb-stat-panel">
  <header><span>{eyebrow}</span><h2>{title}</h2><p>{note}</p></header>
  <div className="sdb-chart-frame">{children}</div>
  {actions && <div className="sdb-chart-actions">{actions}</div>}
</section>;

const KPI_ICONS = [Database, FileCheck2, FlaskConical, BookOpen, Library, Wheat, Scale, AlertTriangle];

export default function StatisticsDashboard({ onCompounds, onLiterature }: { onCompounds: Navigate; onLiterature: Navigate }) {
  const [data, setData] = useState<SweetMetaStatistics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [hiddenFamilies, setHiddenFamilies] = useState<Set<string>>(new Set());

  useEffect(() => {
    let active = true;
    setError(null);
    fetchSweetMetaStatistics()
      .then((payload) => { if (active) setData(payload); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : 'Statistics could not be loaded'); });
    return () => { active = false; };
  }, [retry]);

  const timeline = useMemo(() => {
    if (!data) return { rows: [] as Array<Record<string, number | string>>, families: [] as string[] };
    const totals = new Map<string, number>();
    data.literatureTimeline.forEach((row) => totals.set(row.family, (totals.get(row.family) ?? 0) + row.records));
    const families = [...totals].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([family]) => family);
    const rows = new Map<string, Record<string, number | string>>();
    data.literatureTimeline.forEach((item) => {
      if (!families.includes(item.family)) return;
      const key = `${item.yearFrom}-${item.yearTo}`;
      const row = rows.get(key) ?? { period: key, yearFrom: item.yearFrom, yearTo: item.yearTo };
      row[item.family] = item.records;
      rows.set(key, row);
    });
    return { rows: [...rows.values()], families };
  }, [data]);

  if (!data && !error) return <div className="sdb-page sdb-statistics-page" aria-busy="true">
    <div className="sdb-stat-skeleton heading" /><div className="sdb-stat-skeleton metrics" /><div className="sdb-stat-skeleton charts" />
  </div>;
  if (error || !data) return <div className="sdb-page sdb-statistics-page"><div className="sdb-stat-error" role="alert"><AlertTriangle /><h1>Statistics are unavailable</h1><p>{error}</p><button onClick={() => setRetry((value) => value + 1)}><RefreshCw /> Retry</button></div></div>;

  const topFoodGroups = data.foodGroups.slice(0, 10);
  const eventPayload = <T extends object>(entry: unknown) => ((entry as { payload?: T }).payload ?? entry as T);
  const openSweetness = (entry: unknown) => {
    const item = eventPayload<SweetMetaStatistics['sweetnessDistribution'][number]>(entry);
    onCompounds({ domain: 'sweetness', sweetnessMinLog10: item.minLog10, sweetnessMaxLog10: item.maxLog10 });
  };

  return <div className="sdb-page sdb-statistics-page">
    <header className="sdb-page-heading compact sdb-stat-heading"><div><h1>SweetMeta Data Statistics</h1><p>An evidence landscape of sweet compounds, tracing molecular collection, curation, validation, and cross-domain data coverage.</p></div></header>

    <div className="sdb-stat-kpis">{data.kpis.map((item, index) => {
      const Icon = KPI_ICONS[index] ?? Database;
      return <article key={item.key}><Icon /><div><strong>{item.value.toLocaleString()}</strong><span>{item.label}</span><small>{item.detail}</small></div></article>;
    })}</div>

    <div className="sdb-stat-section-heading"><h2>Evidence and coverage</h2><p>Click a chart value to inspect the underlying public records.</p></div>
    <div className="sdb-stat-dashboard">
      <ChartPanel eyebrow="Evidence" title="Evidence readiness" note="R1-R4 status across the complete public compound release." actions={data.readiness.map((item) => <button key={item.key} onClick={() => onCompounds({ tier: item.key })}>{item.key} · {item.count}</button>)}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={data.readiness} margin={{ top: 12, right: 18, left: 0, bottom: 4 }}><CartesianGrid vertical={false} stroke="#e8eef2" /><XAxis dataKey="key" tickLine={false} axisLine={false} /><YAxis tickLine={false} axisLine={false} width={42} /><Tooltip content={<ScientificTooltip />} cursor={CHART_CURSOR} /><Bar dataKey="count" name="Compounds" radius={[3, 3, 0, 0]} onClick={(entry) => onCompounds({ tier: eventPayload<{ key: string }>(entry).key })}>{data.readiness.map((item) => <Cell key={item.key} fill={READINESS_COLORS[item.key]} cursor="pointer" />)}</Bar></BarChart></ResponsiveContainer>
      </ChartPanel>

      <ChartPanel eyebrow="Literature" title="Publication timeline" note="Five-year intervals for the six largest literature families." actions={timeline.families.map((family) => <button key={family} className={hiddenFamilies.has(family) ? 'muted' : ''} onClick={() => setHiddenFamilies((current) => { const next = new Set(current); if (next.has(family)) next.delete(family); else next.add(family); return next; })}>{humanize(family)}</button>)}>
        <ResponsiveContainer width="100%" height="100%"><LineChart data={timeline.rows} margin={{ top: 12, right: 16, left: 0, bottom: 4 }}><CartesianGrid vertical={false} stroke="#e8eef2" /><XAxis dataKey="period" tickLine={false} axisLine={false} interval="preserveStartEnd" /><YAxis tickLine={false} axisLine={false} width={42} /><Tooltip content={<ScientificTooltip />} /><Legend content={() => null} />{timeline.families.map((family, index) => hiddenFamilies.has(family) ? null : <Line key={family} dataKey={family} name={humanize(family)} stroke={COLORS[index]} strokeWidth={2} dot={false} activeDot={{ r: 5, cursor: 'pointer', onClick: (_event: unknown, payload: unknown) => { const row = eventPayload<{ yearFrom: number; yearTo: number }>(payload); onLiterature({ yearFrom: row.yearFrom, yearTo: row.yearTo, compoundFamily: family }); } }} />)}</LineChart></ResponsiveContainer>
      </ChartPanel>

      <ChartPanel eyebrow="Quantitative evidence" title="Relative sweetness distribution" note="Reported measurements grouped on a log10 scale relative to the stated reference." actions={data.sweetnessDistribution.map((item) => <button key={item.key} onClick={() => openSweetness(item)}>{item.label} · {item.records}</button>)}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={data.sweetnessDistribution} margin={{ top: 12, right: 18, left: 0, bottom: 4 }}><CartesianGrid vertical={false} stroke="#e8eef2" /><XAxis dataKey="label" tickLine={false} axisLine={false} /><YAxis tickLine={false} axisLine={false} width={42} /><Tooltip content={<ScientificTooltip />} cursor={CHART_CURSOR} /><Bar dataKey="records" name="Measurements" fill="#e8825c" radius={[3, 3, 0, 0]} cursor="pointer" onClick={openSweetness} /></BarChart></ResponsiveContainer>
      </ChartPanel>

      <ChartPanel eyebrow="Cross-domain" title="Compound coverage" note="Distinct public compounds covered by each evidence domain." actions={data.domainCoverage.map((item) => <button key={item.key} onClick={() => onCompounds({ domain: item.key })}>{item.label} · {item.compounds}</button>)}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={data.domainCoverage} layout="vertical" margin={{ top: 6, right: 26, left: 18, bottom: 4 }}><CartesianGrid horizontal={false} stroke="#e8eef2" /><XAxis type="number" domain={[0, data.release.publicCompounds]} tickLine={false} axisLine={false} /><YAxis type="category" dataKey="label" width={126} tickLine={false} axisLine={false} tick={{ fontSize: 10 }} /><Tooltip content={<ScientificTooltip />} cursor={CHART_CURSOR} /><Bar dataKey="compounds" name="Compounds" fill="#3d73b2" radius={[0, 3, 3, 0]} cursor="pointer" onClick={(entry) => onCompounds({ domain: eventPayload<{ key: string }>(entry).key })} /></BarChart></ResponsiveContainer>
      </ChartPanel>

      <ChartPanel eyebrow="Food sources" title="Food category landscape" note="Top FoodDB groups by occurrence count; coverage uses distinct public compounds." actions={topFoodGroups.map((item) => <button key={item.key} onClick={() => onCompounds({ domain: 'food', foodGroup: item.key })}>{item.label} · {item.compounds}</button>)}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={topFoodGroups} layout="vertical" margin={{ top: 6, right: 24, left: 18, bottom: 4 }}><CartesianGrid horizontal={false} stroke="#e8eef2" /><XAxis type="number" tickLine={false} axisLine={false} /><YAxis type="category" dataKey="label" width={126} tickLine={false} axisLine={false} tick={{ fontSize: 10 }} /><Tooltip content={<ScientificTooltip />} cursor={CHART_CURSOR} /><Bar dataKey="records" name="Occurrences" fill="#82baab" radius={[0, 3, 3, 0]} cursor="pointer" onClick={(entry) => onCompounds({ domain: 'food', foodGroup: eventPayload<{ key: string }>(entry).key })} /></BarChart></ResponsiveContainer>
      </ChartPanel>

      <ChartPanel eyebrow="Quality control" title="Data quality profile" note="Verified, attention, and unavailable states across the public release." actions={data.qualityProfile.flatMap((metric) => (['verified', 'attention', 'unknown'] as const).filter((state) => metric[state] > 0).map((state) => <button key={`${metric.key}-${state}`} onClick={() => onCompounds({ qualityMetric: metric.key, qualityState: state })}>{metric.label}: {humanize(state)}</button>))}>
        <ResponsiveContainer width="100%" height="100%"><BarChart data={data.qualityProfile} layout="vertical" stackOffset="expand" margin={{ top: 6, right: 20, left: 24, bottom: 4 }}><CartesianGrid horizontal={false} stroke="#e8eef2" /><XAxis type="number" tickFormatter={(value) => `${Math.round(value * 100)}%`} tickLine={false} axisLine={false} /><YAxis type="category" dataKey="label" width={126} tickLine={false} axisLine={false} tick={{ fontSize: 10 }} /><Tooltip content={<ScientificTooltip />} cursor={CHART_CURSOR} /><Bar dataKey="verified" name="Verified / clear" stackId="quality" fill="#82baab" cursor="pointer" onClick={(entry) => onCompounds({ qualityMetric: eventPayload<{ key: string }>(entry).key, qualityState: 'verified' })} /><Bar dataKey="attention" name="Needs attention" stackId="quality" fill="#c2294a" cursor="pointer" onClick={(entry) => onCompounds({ qualityMetric: eventPayload<{ key: string }>(entry).key, qualityState: 'attention' })} /><Bar dataKey="unknown" name="Not available" stackId="quality" fill="#b3c8e1" cursor="pointer" onClick={(entry) => onCompounds({ qualityMetric: eventPayload<{ key: string }>(entry).key, qualityState: 'unknown' })} /></BarChart></ResponsiveContainer>
      </ChartPanel>
    </div>
    <footer className="sdb-stat-footnote">Coverage percentages use {data.release.publicCompounds.toLocaleString()} formally released compounds as the denominator. Candidate and needs-review literature links are excluded.</footer>
  </div>;
}
