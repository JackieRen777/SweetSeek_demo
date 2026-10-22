import { useEffect, useMemo, useRef, useState } from 'react';
import * as echarts from 'echarts/core';
import type { EChartsCoreOption as EChartsOption, EChartsType } from 'echarts/core';
import { BarChart, LineChart, SankeyChart, ScatterChart } from 'echarts/charts';
import { AriaComponent, GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { fetchSweetMetaStatistics, type SweetMetaStatistics } from '../sweetmetaApi';

echarts.use([AriaComponent, BarChart, CanvasRenderer, GridComponent, LegendComponent, LineChart, SankeyChart, ScatterChart, TooltipComponent]);

type QueryValue = string | number | null | undefined;
type Navigate = (params: Record<string, QueryValue>) => void;
type ChartClick = { data?: unknown; dataIndex?: number; dataType?: string; name?: string; seriesName?: string; value?: unknown };

const INK = '#202124';
const AXIS = '#3C4043';
const GRID = '#D9DEDF';
const BLUES = ['#08306B', '#1D4E89', '#2171B5', '#6BAED6', '#C6DBEF'];
const FAMILY_COLORS = ['#0D0887', '#501F80', '#92377A', '#D25172', '#DD8B57', '#E7C33C', '#F3F440'];
const GRADE_COLORS: Record<string, string> = { E1: '#0C8F86', E2: '#3679B8', E3: '#D8922E' };
const FONT = 'Arial, "Helvetica Neue", sans-serif';
const COVERAGE_FEATURE_ORDER = ['Structure', 'Taste / sweetness data', 'Quantitative sweetness', 'Reference identifier', 'Full-text corpus', 'Evidence tiering', 'Receptor activity', 'Food occurrence', 'Regulatory mapping', 'Experimental structures', 'Protein records'];
const SOURCE_ORDER = ['Existing multi-source release', 'ChemTastesDB curated entries', 'ChemTastesDB + PubChem registry', 'Direct evidence / other curated'];

const escapeHtml = (value: unknown) => String(value ?? '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
const number = (value: number | null | undefined, digits = 0) => Number.isFinite(Number(value)) ? Number(value).toLocaleString(undefined, { maximumFractionDigits: digits }) : '—';
const familyShort = (value: string) => value
  .replace(' sweeteners', '').replace('Carbohydrates, rare sugars and polyols', 'Carbohydrates / polyols')
  .replace('Non-glycosidic terpenoid, steroid and lipid-like', 'Terpenoid / steroid / lipid')
  .replace('Sulfur- and nitrogen-containing synthetic', 'S/N synthetic')
  .replace('Aromatic, phenolic and flavonoid', 'Aromatic / phenolic')
  .replace('Heterocyclic and other specialised', 'Heterocyclic / specialised')
  .replace('Peptide and amino-acid', 'Peptide / amino-acid')
  .replace('Glycosidic natural', 'Glycosidic natural');
const sourceShort = (value: string) => value
  .replace('Existing multi-source release', 'Existing multi-source')
  .replace('ChemTastesDB curated entries', 'ChemTastesDB curated')
  .replace('ChemTastesDB + PubChem registry', 'ChemTastesDB + PubChem')
  .replace('Direct evidence / other curated', 'Direct / other curated');

const baseText = { fontFamily: FONT, color: AXIS, fontSize: 11 };
const baseGrid = { left: 70, right: 30, top: 28, bottom: 48, containLabel: true };
const baseTooltip = { confine: true, backgroundColor: '#FFFFFF', borderColor: '#C9D2D8', borderWidth: 1, textStyle: { ...baseText, color: INK }, extraCssText: 'box-shadow:0 8px 24px rgba(20,45,65,.12);border-radius:4px;' };

function EChart({ option, label, className = '', onClick }: { option: EChartsOption; label: string; className?: string; onClick?: (params: ChartClick) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useRef<EChartsType | null>(null);
  useEffect(() => {
    if (!ref.current || navigator.userAgent.toLowerCase().includes('jsdom')) return;
    const chart = echarts.init(ref.current, undefined, { renderer: 'canvas' });
    instance.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => { observer.disconnect(); chart.dispose(); instance.current = null; };
  }, []);
  useEffect(() => { instance.current?.setOption(option, { notMerge: true }); }, [option]);
  useEffect(() => {
    const chart = instance.current;
    if (!chart) return;
    chart.off('click');
    if (onClick) chart.on('click', (params) => onClick(params as ChartClick));
  }, [onClick]);
  return <div ref={ref} className={`sdb-echart ${className}`} role="img" aria-label={label} tabIndex={0}><span className="sdb-chart-fallback">{label}</span></div>;
}

function Figure({ eyebrow, title, note, className = '', children }: { eyebrow: string; title: string; note: string; className?: string; children: React.ReactNode }) {
  return <article className={`sdb-stat-figure ${className}`}><header><span>{eyebrow}</span><h3>{title}</h3><p>{note}</p></header>{children}</article>;
}

function Section({ id, title, note, children }: { id: string; title: string; note: string; children: React.ReactNode }) {
  return <section className="sdb-stat-topic" id={`statistics-${id}`} aria-labelledby={`statistics-${id}-title`}><header className="sdb-stat-topic-heading"><div><h2 id={`statistics-${id}-title`}>{title}</h2><p>{note}</p></div></header>{children}</section>;
}

function ProjectionFigure({ method, data, colors, hidden, onToggle, onCompound }: { method: 'umap' | 'pca'; data: SweetMetaStatistics; colors: Map<string, string>; hidden: Set<string>; onToggle: (family: string) => void; onCompound: (id: string) => void }) {
  const rows = data.chemicalSpace.filter((row) => row.method === method && !hidden.has(row.sweetClassLevel1));
  const option = useMemo<EChartsOption>(() => ({
    animationDuration: 240,
    aria: { enabled: true, description: `${method.toUpperCase()} projection of ${rows.length} reviewed compounds by SweetClass family.` },
    grid: { ...baseGrid, left: 58, right: 22, top: 18, bottom: 54 },
    tooltip: { ...baseTooltip, trigger: 'item', formatter: (raw: unknown) => {
      const params = raw as { data?: { row?: SweetMetaStatistics['chemicalSpace'][number] } };
      const row = params.data?.row;
      if (!row) return '';
      return `<strong>${escapeHtml(row.name)}</strong><br/><span>${escapeHtml(row.id)}</span><br/><br/>SweetClass L1: ${escapeHtml(row.sweetClassLevel1)}<br/>SweetClass L2: ${escapeHtml(row.sweetClassLevel2)}<br/>Formula: ${escapeHtml(row.formula ?? 'Not available')}<br/>MW: ${number(row.molecularWeight, 2)} Da<br/>Evidence: ${escapeHtml(row.evidenceGrade)}<br/>Source: ${escapeHtml(row.sourceCollection)}<br/>Raw coordinates: ${number(row.x, 3)}, ${number(row.y, 3)}`;
    } },
    xAxis: { type: 'value', name: method === 'umap' ? 'UMAP 1' : 'PC 1', nameLocation: 'middle', nameGap: 31, nameTextStyle: baseText, axisLabel: baseText, axisLine: { lineStyle: { color: AXIS } }, splitLine: { lineStyle: { color: GRID, width: .6 } } },
    yAxis: { type: 'value', name: method === 'umap' ? 'UMAP 2' : 'PC 2', nameLocation: 'middle', nameGap: 40, nameTextStyle: baseText, axisLabel: baseText, axisLine: { lineStyle: { color: AXIS } }, splitLine: { lineStyle: { color: GRID, width: .6 } } },
    series: data.composition.level1.filter((family) => !hidden.has(family.key)).map((family) => ({
      name: family.label, type: 'scatter', symbolSize: 5.5, large: true, largeThreshold: 800,
      emphasis: { focus: 'series', itemStyle: { borderColor: INK, borderWidth: 1 }, scale: 1.7 },
      itemStyle: { color: colors.get(family.key), opacity: .76 },
      data: rows.filter((row) => row.sweetClassLevel1 === family.key).map((row) => ({ value: [row.x, row.y], row })),
    })),
  }), [colors, data.composition.level1, hidden, method, rows]);
  return <Figure eyebrow="Reviewed ECFP4 coordinates" title={`${method.toUpperCase()} molecular space`} note={`${rows.length.toLocaleString()} compounds shown. Select a point to open its reviewed record.`}>
    <EChart option={option} label={`${method.toUpperCase()} molecular space by SweetClass family`} className="sdb-echart-space" onClick={(params) => { const datum = params.data as { row?: { id: string } } | undefined; if (datum?.row?.id) onCompound(datum.row.id); }} />
    <div className="sdb-inline-legend" aria-label={`${method.toUpperCase()} family visibility`}>{data.composition.level1.map((family) => <button type="button" aria-pressed={!hidden.has(family.key)} key={family.key} className={hidden.has(family.key) ? 'muted' : ''} onClick={() => onToggle(family.key)}><i style={{ background: colors.get(family.key) }} />{familyShort(family.label)}</button>)}</div>
  </Figure>;
}

function ViolinFigure({ distributions, colors, onCompounds }: { distributions: SweetMetaStatistics['properties']; colors: Map<string, string>; onCompounds: Navigate }) {
  const familyOrder = [...colors.keys()];
  return <Figure eyebrow="Reviewed RDKit descriptors" title="Property distributions by SweetClass family" note="Six coordinated views use a shared family order. Hover for n, median, IQR, and range; select a violin to open Browse." className="sdb-stat-figure-full">
    <div className="sdb-violin-composite">{distributions.slice(0, 6).map((distribution) => {
      const groups = [...distribution.groups].sort((a, b) => familyOrder.indexOf(a.family) - familyOrder.indexOf(b.family));
      const low = Math.min(...groups.map((group) => group.min));
      const high = Math.max(...groups.map((group) => group.max));
      const span = high - low || 1;
      return <div className="sdb-violin-facet" key={distribution.key}><h4>{distribution.label}{distribution.unit ? ` (${distribution.unit})` : ''}</h4><div className="sdb-violin-axis"><span>{number(high, distribution.axisPrecision)}</span><span>{number(low, distribution.axisPrecision)}</span></div><div className="sdb-violin-groups">{groups.map((group) => {
        const maxDensity = Math.max(...group.density.map((point) => point.density), .001);
        const points = group.density.map((point) => ({ y: 96 - ((point.value - low) / span) * 92, width: (point.density / maxDensity) * 42 }));
        const polygon = [...points.map((point) => `${50 - point.width},${point.y}`), ...[...points].reverse().map((point) => `${50 + point.width},${point.y}`)].join(' ');
        const medianY = 96 - ((group.median - low) / span) * 92;
        const q1Y = 96 - ((group.q1 - low) / span) * 92;
        const q3Y = 96 - ((group.q3 - low) / span) * 92;
        const queryKey = distribution.key === 'molecularWeight' ? 'mw' : distribution.key === 'clogp' ? 'clogp' : distribution.key === 'tpsa' ? 'tpsa' : '';
        return <button type="button" className="sdb-violin" key={group.family} aria-label={`${distribution.label}, ${group.family}, median ${number(group.median, distribution.axisPrecision)}`} onClick={() => onCompounds({ sweetClassL1: group.family, ...(queryKey ? { [`${queryKey}Min`]: group.q1, [`${queryKey}Max`]: group.q3 } : {}) })}><svg viewBox="0 0 100 100" preserveAspectRatio="none"><polygon points={polygon} fill={colors.get(group.family)} opacity=".78" /><line className="iqr" x1="50" x2="50" y1={q3Y} y2={q1Y} /><line className="median" x1="31" x2="69" y1={medianY} y2={medianY} /></svg><div className="sdb-violin-tooltip" role="tooltip"><b>{familyShort(group.family)}</b><span>n {group.n.toLocaleString()}</span><span>median {number(group.median, distribution.axisPrecision)}</span><span>IQR {number(group.q1, distribution.axisPrecision)}–{number(group.q3, distribution.axisPrecision)}</span><span>range {number(group.min, distribution.axisPrecision)}–{number(group.max, distribution.axisPrecision)}</span></div></button>;
      })}</div></div>;
    })}</div>
    <div className="sdb-inline-legend sdb-family-key">{familyOrder.map((family) => <span key={family}><i style={{ background: colors.get(family) }} />{familyShort(family)}</span>)}</div>
  </Figure>;
}

export default function StatisticsDashboard({ onCompounds, onCompound }: { onCompounds: Navigate; onCompound: (id: string) => void }) {
  const [data, setData] = useState<SweetMetaStatistics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [family, setFamily] = useState('');
  const [hiddenFamilies, setHiddenFamilies] = useState<Set<string>>(new Set());
  const [activeSection, setActiveSection] = useState('composition');
  useEffect(() => { let active = true; fetchSweetMetaStatistics().then((payload) => { if (active) { setData(payload); setError(null); } }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : 'Statistics could not be loaded'); }); return () => { active = false; }; }, [retry]);
  useEffect(() => { const clear = (event: KeyboardEvent) => { if (event.key === 'Escape') setFamily(''); }; window.addEventListener('keydown', clear); return () => window.removeEventListener('keydown', clear); }, []);
  useEffect(() => {
    const nodes = [...document.querySelectorAll<HTMLElement>('.sdb-stat-topic')];
    if (!nodes.length || !('IntersectionObserver' in window)) return;
    const observer = new IntersectionObserver((entries) => { const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]; if (visible) setActiveSection(visible.target.id.replace('statistics-', '')); }, { root: document.querySelector('.sdb-main'), rootMargin: '-20% 0px -65%', threshold: [0, .2, .5] });
    nodes.forEach((node) => observer.observe(node)); return () => observer.disconnect();
  }, [data]);
  useEffect(() => {
    if (!data || !window.location.hash.startsWith('#statistics-')) return;
    const target = document.getElementById(window.location.hash.slice(1));
    if (!target) return;
    const frame = window.requestAnimationFrame(() => target.scrollIntoView?.({ block: 'start' }));
    return () => window.cancelAnimationFrame(frame);
  }, [data]);
  if (!data && !error) return <div className="sdb-page sdb-statistics-page" aria-busy="true"><div className="sdb-stat-skeleton heading" /><div className="sdb-stat-skeleton charts" /></div>;
  if (error || !data) return <div className="sdb-page sdb-statistics-page"><div className="sdb-stat-error" role="alert"><AlertTriangle /><h1>Statistics are unavailable</h1><p>{error}</p><button onClick={() => setRetry((value) => value + 1)}><RefreshCw /> Retry</button></div></div>;

  const colors = new Map(data.composition.level1.map((item, index) => [item.key, FAMILY_COLORS[index % FAMILY_COLORS.length]]));
  const familyOrder = data.composition.level1.map((item) => item.key);
  const level2 = data.composition.level2.filter((item) => !family || item.parent === family);
  const nestedRows = data.composition.level1
    .filter((item) => !family || item.key === family)
    .flatMap((parent) => [
      { kind: 'parent' as const, key: parent.key, label: familyShort(parent.label), parent: parent.key, count: parent.count, percentWithinParent: 100 },
      ...level2.filter((item) => item.parent === parent.key).map((item) => ({ kind: 'child' as const, ...item })),
    ]);
  const compositionL1: EChartsOption = {
    aria: { enabled: true }, grid: { ...baseGrid, left: 12, right: 88, top: 12, bottom: 38 }, tooltip: { ...baseTooltip, trigger: 'item' },
    xAxis: { type: 'value', name: 'Share of 1,296 reviewed compounds (%)', max: 45, nameLocation: 'middle', nameGap: 30, nameTextStyle: baseText, axisLabel: { ...baseText, formatter: '{value}%' }, axisLine: { lineStyle: { color: AXIS, width: .7 } }, axisTick: { lineStyle: { color: AXIS } }, splitLine: { lineStyle: { color: GRID, width: .5 } } },
    yAxis: { type: 'category', inverse: true, data: data.composition.level1.map((item) => familyShort(item.label)), axisLabel: { ...baseText, width: 145, overflow: 'break' }, axisTick: { show: false }, axisLine: { show: false } },
    series: [
      { type: 'bar', barWidth: 4, silent: true, z: 1, itemStyle: { borderRadius: 0 }, data: data.composition.level1.map((item) => ({ value: item.percent, itemStyle: { color: colors.get(item.key), opacity: family && family !== item.key ? .16 : .95 } })) },
      { type: 'scatter', symbolSize: (value: unknown) => 8 + Math.sqrt(Number((value as unknown[])[2])) * .65, z: 3, data: data.composition.level1.map((item) => ({ value: [item.percent, familyShort(item.label), item.count], row: item, itemStyle: { color: colors.get(item.key), opacity: family && family !== item.key ? .22 : 1, borderColor: '#FFFFFF', borderWidth: 1 }, label: { show: true, position: 'right', distance: 5, color: INK, fontFamily: FONT, fontSize: 11, formatter: `${item.count.toLocaleString()} (${number(item.percent, 1)}%)` } })), emphasis: { focus: 'self', scale: 1.2 } },
    ],
  };
  const compositionL2: EChartsOption = {
    aria: { enabled: true }, grid: { ...baseGrid, left: 12, right: 86, top: 12, bottom: 34 }, tooltip: { ...baseTooltip, trigger: 'item', formatter: (raw: unknown) => { const row = (raw as { data?: { row?: SweetMetaStatistics['composition']['level2'][number] } }).data?.row; return row ? `<strong>${escapeHtml(row.label)}</strong><br/>${row.count.toLocaleString()} compounds<br/>${number(row.percentWithinParent, 1)}% of ${escapeHtml(familyShort(row.parent))}<br/>${number(row.percentOverall, 1)}% overall` : ''; } },
    xAxis: { type: 'value', name: 'Compounds', nameLocation: 'middle', nameGap: 27, nameTextStyle: baseText, axisLabel: baseText, splitLine: { lineStyle: { color: GRID } } },
    yAxis: { type: 'category', inverse: true, data: nestedRows.map((item) => item.kind === 'parent' ? `{parent|${item.label}}` : `{child|    ${item.label}}`), axisLabel: { ...baseText, width: 205, overflow: 'truncate', rich: { parent: { fontFamily: FONT, fontWeight: 700, color: INK, fontSize: 10 }, child: { fontFamily: FONT, color: '#5E6C7B', fontSize: 9 } } }, axisTick: { show: false }, axisLine: { show: false } },
    series: [{ type: 'bar', barWidth: family ? 13 : 8, data: nestedRows.map((item, index) => ({ value: item.count, row: item.kind === 'child' ? item : undefined, itemStyle: { color: item.kind === 'parent' ? '#1D4E89' : BLUES[2 + (index % 3)], opacity: item.kind === 'parent' ? 1 : .82 }, label: { show: true, position: 'right', color: item.kind === 'parent' ? '#1D4E89' : AXIS, fontWeight: item.kind === 'parent' ? 700 : 400, fontFamily: FONT, fontSize: 9, formatter: `${item.count}` } })) }],
  };

  const pathRows = data.evidenceCoverage.paths ?? [];
  const sourceGrade = new Map<string, number>(); const gradeFamily = new Map<string, number>();
  pathRows.forEach((row) => { sourceGrade.set(`${row.source}\u001f${row.grade}`, (sourceGrade.get(`${row.source}\u001f${row.grade}`) ?? 0) + row.count); gradeFamily.set(`${row.grade}\u001f${row.family}`, (gradeFamily.get(`${row.grade}\u001f${row.family}`) ?? 0) + row.count); });
  const availableSources = new Set(pathRows.map((row) => row.source));
  const sourceNames = [...SOURCE_ORDER.filter((name) => availableSources.has(name)), ...[...availableSources].filter((name) => !SOURCE_ORDER.includes(name))];
  const familyNames = familyOrder;
  const sankeyTotals = new Map<string, number>();
  pathRows.forEach((row) => { sankeyTotals.set(row.source, (sankeyTotals.get(row.source) ?? 0) + row.count); sankeyTotals.set(row.grade, (sankeyTotals.get(row.grade) ?? 0) + row.count); sankeyTotals.set(row.family, (sankeyTotals.get(row.family) ?? 0) + row.count); });
  const sankeyOption: EChartsOption = {
    aria: { enabled: true }, tooltip: { ...baseTooltip, trigger: 'item', formatter: (raw: unknown) => { const params = raw as { dataType?: string; data?: { source?: string; target?: string; value?: number; name?: string } }; if (params.dataType === 'edge') return `<strong>${escapeHtml(params.data?.source)} → ${escapeHtml(params.data?.target)}</strong><br/>${number(params.data?.value ?? 0)} compounds<br/>${number((params.data?.value ?? 0) * 100 / data.release.publicCompounds, 1)}% of reviewed release`; return `<strong>${escapeHtml(params.data?.name)}</strong>`; } },
    series: [{ type: 'sankey', left: 108, right: 118, top: 24, bottom: 22, nodeWidth: 11, nodeGap: 9, draggable: false, emphasis: { focus: 'adjacency' }, lineStyle: { color: 'source', opacity: .34, curveness: .5 }, itemStyle: { borderColor: '#FFFFFF', borderWidth: 1 }, label: { ...baseText, color: INK, fontSize: 9, lineHeight: 13 }, data: [
      ...sourceNames.map((name, index) => ({ name, itemStyle: { color: BLUES[(index + 1) % BLUES.length] }, label: { position: 'left', align: 'right', formatter: `${sourceShort(name)}\nn = ${number(sankeyTotals.get(name))}` } })),
      ...['E1', 'E2', 'E3'].map((name) => ({ name, itemStyle: { color: GRADE_COLORS[name] }, label: { position: 'left', align: 'right', formatter: `${name}\nn = ${number(sankeyTotals.get(name))}` } })),
      ...familyNames.map((name) => ({ name, itemStyle: { color: colors.get(name) ?? BLUES[2] }, label: { position: 'right', align: 'left', formatter: `${familyShort(name)}\nn = ${number(sankeyTotals.get(name))}` } })),
    ], links: [...[...sourceGrade].map(([key, value]) => { const [source, target] = key.split('\u001f'); return { source, target, value }; }), ...[...gradeFamily].map(([key, value]) => { const [source, target] = key.split('\u001f'); return { source, target, value }; })] }],
  };
  const grades = ['E1', 'E2', 'E3'];
  const familyRows = familyOrder;
  const familyGradeOption: EChartsOption = { aria: { enabled: true }, grid: { ...baseGrid, left: 14, right: 34, top: 52, bottom: 42 }, tooltip: { ...baseTooltip, trigger: 'axis', axisPointer: { type: 'shadow' } }, legend: { top: 4, textStyle: baseText, itemWidth: 12, itemHeight: 8 }, xAxis: { type: 'value', max: 100, axisLabel: { ...baseText, formatter: '{value}%' }, axisLine: { lineStyle: { color: AXIS, width: .7 } }, splitLine: { lineStyle: { color: GRID, width: .5 } } }, yAxis: { type: 'category', inverse: true, data: familyRows.map(familyShort), axisLabel: { ...baseText, width: 140, overflow: 'break' }, axisTick: { show: false }, axisLine: { show: false } }, series: grades.map((grade) => ({ name: grade, type: 'bar', stack: 'grade', barWidth: 22, itemStyle: { color: GRADE_COLORS[grade], borderColor: '#FFFFFF', borderWidth: .8 }, label: { show: true, position: 'inside', fontFamily: FONT, fontSize: 9, color: grade === 'E3' ? INK : '#FFFFFF', formatter: (raw: unknown) => { const count = Number((raw as { data?: { count?: number } }).data?.count ?? 0); return count >= 8 ? String(count) : ''; } }, data: familyRows.map((name) => { const familyTotal = data.composition.level1.find((item) => item.key === name)?.count ?? 0; const evidenceRow = data.evidenceCoverage.familyGrades.find((item) => (item.family === name || item.total === familyTotal) && item.grade === grade); const count = evidenceRow?.count ?? 0; return { value: familyTotal ? count * 100 / familyTotal : 0, count, row: { family: name, grade } }; }) })) };

  const densityOptions = (distribution: SweetMetaStatistics['properties'][number]): EChartsOption => ({ aria: { enabled: true }, grid: { ...baseGrid, left: 62, right: 20, top: 30, bottom: 45 }, tooltip: { ...baseTooltip, trigger: 'axis' }, xAxis: { type: 'value', name: distribution.unit, nameLocation: 'middle', nameGap: 28, nameTextStyle: baseText, axisLabel: baseText, splitLine: { lineStyle: { color: GRID } } }, yAxis: { type: 'value', name: 'Density', nameTextStyle: baseText, axisLabel: baseText, splitLine: { lineStyle: { color: GRID } } }, series: [...distribution.groups].sort((a, b) => familyOrder.indexOf(a.family) - familyOrder.indexOf(b.family)).map((group) => ({ name: familyShort(group.family), type: 'line', showSymbol: false, smooth: .25, lineStyle: { color: colors.get(group.family), width: 1.2 }, areaStyle: { color: colors.get(group.family), opacity: .025 }, emphasis: { focus: 'series', lineStyle: { width: 2.2 } }, data: group.density.map((point) => [point.value, point.density]) })) });
  const moduleOption: EChartsOption = { aria: { enabled: true }, grid: { ...baseGrid, left: 12, right: 76, top: 16, bottom: 40 }, tooltip: { ...baseTooltip, trigger: 'axis', axisPointer: { type: 'line' } }, xAxis: { type: 'value', axisLabel: baseText, axisLine: { lineStyle: { color: AXIS, width: .7 } }, splitLine: { lineStyle: { color: GRID, width: .5 } } }, yAxis: { type: 'category', inverse: true, data: data.evidenceCoverage.modules.map((item) => item.module), axisLabel: { ...baseText, width: 145, overflow: 'break' }, axisTick: { show: false }, axisLine: { show: false } }, series: [{ type: 'bar', barWidth: 3, silent: true, itemStyle: { color: '#6BAED6' }, data: data.evidenceCoverage.modules.map((item) => item.count) }, { type: 'scatter', symbolSize: 10, itemStyle: { color: '#08306B' }, label: { show: true, position: 'right', distance: 6, color: AXIS, formatter: (raw: unknown) => number(Number((raw as { value?: unknown[] }).value?.[0] ?? 0)) }, data: data.evidenceCoverage.modules.map((item) => ({ value: [item.count, item.module], row: item })) }] };
  const coverageFeatures = data.featureCoverageComparison?.[0] ? COVERAGE_FEATURE_ORDER.filter((feature) => feature in data.featureCoverageComparison[0].features) : [];
  const coverageOption: EChartsOption = { aria: { enabled: true }, grid: { left: 128, right: 16, top: 108, bottom: 24 }, tooltip: { ...baseTooltip, formatter: (raw: unknown) => { const params = raw as { value?: [number, number] }; const value = params.value; const row = value ? data.featureCoverageComparison[value[1]] : undefined; return value && row ? `<strong>${escapeHtml(row.resource)}</strong><br/>${escapeHtml(coverageFeatures[value[0]])}: ${row.features[coverageFeatures[value[0]]] ? 'Available' : 'Not represented'}` : ''; } }, xAxis: { type: 'category', position: 'top', data: coverageFeatures, axisLabel: { ...baseText, rotate: 46, interval: 0, color: INK }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } }, yAxis: { type: 'category', inverse: true, data: data.featureCoverageComparison?.map((row) => row.resource) ?? [], axisLabel: { ...baseText, color: INK, width: 116, overflow: 'break' }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: true, lineStyle: { color: GRID, width: .5 } } }, series: [{ name: 'Available', type: 'scatter', symbol: 'circle', symbolSize: 15, itemStyle: { color: '#08519C', borderColor: '#08306B', borderWidth: .7 }, data: (data.featureCoverageComparison ?? []).flatMap((row, y) => coverageFeatures.flatMap((feature, x) => row.features[feature] ? [[x, y]] : [])) }, { name: 'Not represented', type: 'scatter', symbol: 'rect', symbolSize: [12, 2], itemStyle: { color: '#A6A6A6' }, data: (data.featureCoverageComparison ?? []).flatMap((row, y) => coverageFeatures.flatMap((feature, x) => row.features[feature] ? [] : [[x, y]])) }] };
  const jumpItems = [['composition', 'Composition'], ['space', 'Chemical Space'], ['evidence', 'Evidence'], ['properties', 'Properties'], ['coverage', 'Coverage']];
  const toggleFamily = (name: string) => setHiddenFamilies((current) => { const next = new Set(current); if (next.has(name)) next.delete(name); else next.add(name); return next; });
  return <div className="sdb-page sdb-statistics-page">
    <header className="sdb-page-heading compact sdb-stat-heading"><h1>SweetMeta Data Statistics</h1></header>
    <nav className="sdb-stat-jump" aria-label="Statistics sections">{jumpItems.map(([key, label]) => <a key={key} className={activeSection === key ? 'active' : ''} aria-current={activeSection === key ? 'location' : undefined} href={`#statistics-${key}`} onClick={(event) => {
      event.preventDefault();
      const hash = `#statistics-${key}`;
      window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}${hash}`);
      document.getElementById(hash.slice(1))?.scrollIntoView?.({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    }}>{label}</a>)}</nav>

    <Section id="composition" title="SweetClass Composition" note="The reviewed two-level taxonomy: seven structural families and 28 subclasses."><div className="sdb-stat-grid sdb-composition-grid"><Figure eyebrow="SweetClass level 1" title="Structural families" note="Counts use all 1,296 reviewed compounds. Select a family to focus the subclass view."><EChart option={compositionL1} label="SweetClass level-one family composition" onClick={(params) => { const row = params.data as { row?: { key: string } } | undefined; if (row?.row?.key) setFamily((current) => current === row.row?.key ? '' : row.row!.key); }} />{family && <button className="sdb-clear-selection" onClick={() => setFamily('')}>Clear selection: {familyShort(family)}</button>}</Figure><Figure eyebrow="SweetClass level 2" title={family ? `${familyShort(family)} subclasses` : 'All reviewed subclasses'} note="Dark bars show family totals; indented blue bars show reviewed subclasses."><EChart option={compositionL2} label="SweetClass level-two subclass composition" className={family ? '' : 'sdb-echart-tall'} onClick={(params) => { const datum = params.data as { row?: { parent: string; key: string } } | undefined; if (datum?.row) onCompounds({ sweetClassL1: datum.row.parent, sweetClassL2: datum.row.key }); }} /></Figure></div></Section>
    <Section id="space" title="Chemical Space" note="Reviewed ECFP4 UMAP and PCA projections are shown together for direct comparison."><div className="sdb-stat-grid"><ProjectionFigure method="umap" data={data} colors={colors} hidden={hiddenFamilies} onToggle={toggleFamily} onCompound={onCompound} /><ProjectionFigure method="pca" data={data} colors={colors} hidden={hiddenFamilies} onToggle={toggleFamily} onCompound={onCompound} /></div></Section>
    <Section id="evidence" title="Evidence Provenance" note="E1–E3 is the authoritative evidence system in the reviewed v1.0.7 snapshot."><div className="sdb-stat-grid sdb-evidence-grid"><Figure eyebrow="Compound-level lineage" title="Source → evidence → family" note="Hover a node or link to isolate adjacent relationships. Every stage conserves 1,296 compounds."><EChart option={sankeyOption} label="Evidence provenance Sankey diagram" className="sdb-echart-sankey" onClick={(params) => { const datum = params.data as { source?: string; target?: string; name?: string } | undefined; if (params.dataType === 'node' && datum?.name) { if (grades.includes(datum.name)) onCompounds({ evidenceGrade: datum.name }); else if (familyNames.includes(datum.name)) onCompounds({ sweetClassL1: datum.name }); else onCompounds({ sourceCollection: datum.name }); } else if (datum?.source && datum.target) { if (grades.includes(datum.target)) onCompounds({ sourceCollection: datum.source, evidenceGrade: datum.target }); else onCompounds({ evidenceGrade: datum.source, sweetClassL1: datum.target }); } }} /></Figure><Figure eyebrow="Evidence by family" title="Family evidence grades" note="Select a segment to open the exact family and evidence-grade result."><EChart option={familyGradeOption} label="Evidence grades within SweetClass families" onClick={(params) => { const datum = params.data as { row?: { family: string; grade: string } } | undefined; if (datum?.row) onCompounds({ sweetClassL1: datum.row.family, evidenceGrade: datum.row.grade }); }} /></Figure></div></Section>
    <Section id="properties" title="Physicochemical Landscape" note="Parent-normalized RDKit descriptors from the reviewed structures."><div className="sdb-stat-grid"><ViolinFigure distributions={data.properties} colors={colors} onCompounds={onCompounds} />{data.properties.slice(6).map((distribution) => <Figure key={distribution.key} eyebrow="Structural-family density" title={`${distribution.label}${distribution.unit ? ` (${distribution.unit})` : ''}`} note="Hover a curve to isolate one SweetClass family."><EChart option={densityOptions(distribution)} label={`${distribution.label} density by SweetClass family`} /></Figure>)}</div></Section>
    <Section id="coverage" title="Coverage" note="Reviewed information-module totals and the audited feature comparison supplied with v1.0.7."><div className="sdb-stat-grid"><Figure eyebrow="SweetMeta modules" title="Information module coverage" note="Counts come from the reviewed statistics source table and retain each module's native grain."><EChart option={moduleOption} label="SweetMeta information module coverage" /></Figure><Figure eyebrow="Database comparison" title="Feature coverage matrix" note="A check denotes reported coverage; a dash denotes unavailable or not reported in the reviewed comparison."><EChart option={coverageOption} label="Feature coverage comparison across databases" /></Figure></div></Section>
  </div>;
}
