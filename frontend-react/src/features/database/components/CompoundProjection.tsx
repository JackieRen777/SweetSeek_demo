import { useEffect, useMemo, useRef, useState } from 'react';
import * as echarts from 'echarts/core';
import type { EChartsCoreOption, EChartsType } from 'echarts/core';
import { ScatterChart } from 'echarts/charts';
import { AriaComponent, GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { fetchSweetMetaProjectionContext, type SweetMetaProjectionContext } from '../sweetmetaApi';

echarts.use([AriaComponent, CanvasRenderer, GridComponent, ScatterChart, TooltipComponent]);

const FONT = 'Arial, "Helvetica Neue", sans-serif';

export default function CompoundProjection({ compoundId, onCompound }: { compoundId: string; onCompound: (id: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useRef<EChartsType | null>(null);
  const [method, setMethod] = useState<'umap' | 'pca'>('umap');
  const [request, setRequest] = useState<{ compoundId: string; data: SweetMetaProjectionContext | null; error: string }>({ compoundId, data: null, error: '' });
  const data = request.compoundId === compoundId ? request.data : null;
  const error = request.compoundId === compoundId ? request.error : '';

  useEffect(() => {
    let active = true;
    void fetchSweetMetaProjectionContext(compoundId)
      .then((payload) => { if (active) setRequest({ compoundId, data: payload, error: '' }); })
      .catch((reason: unknown) => { if (active) setRequest({ compoundId, data: null, error: reason instanceof Error ? reason.message : 'Projection context is unavailable' }); });
    return () => { active = false; };
  }, [compoundId]);

  const option = useMemo<EChartsCoreOption>(() => {
    const points = data?.points.filter((point) => point.method === method) ?? [];
    const background = points.filter((point) => !point.selected).map((point) => ({ value: [point.x, point.y], row: point }));
    const selected = points.filter((point) => point.selected).map((point) => ({ value: [point.x, point.y], row: point }));
    return {
      animationDuration: 220,
      aria: { enabled: true, description: `${method.toUpperCase()} context for the selected compound within ${data?.family ?? 'its SweetClass family'}.` },
      grid: { left: 58, right: 22, top: 24, bottom: 54, containLabel: true },
      tooltip: {
        confine: true,
        backgroundColor: '#fff', borderColor: '#c9d2d8', borderWidth: 1,
        textStyle: { color: '#202124', fontFamily: FONT, fontSize: 11 },
        formatter: (raw: unknown) => {
          const row = (raw as { data?: { row?: SweetMetaProjectionContext['points'][number] } }).data?.row;
          return row ? `<strong>${row.name}</strong><br/>${row.sweetClassLevel2}<br/>${row.x.toFixed(3)}, ${row.y.toFixed(3)}` : '';
        },
      },
      xAxis: { type: 'value', name: method === 'umap' ? 'UMAP 1' : 'PC 1', nameLocation: 'middle', nameGap: 31, nameTextStyle: { fontFamily: FONT, color: '#3c4043', fontSize: 11 }, axisLabel: { fontFamily: FONT, color: '#626b73', fontSize: 10 }, splitLine: { lineStyle: { color: '#d9dedf', width: .6 } } },
      yAxis: { type: 'value', name: method === 'umap' ? 'UMAP 2' : 'PC 2', nameLocation: 'middle', nameGap: 42, nameTextStyle: { fontFamily: FONT, color: '#3c4043', fontSize: 11 }, axisLabel: { fontFamily: FONT, color: '#626b73', fontSize: 10 }, splitLine: { lineStyle: { color: '#d9dedf', width: .6 } } },
      series: [
        { name: 'Same SweetClass family', type: 'scatter', symbolSize: 6, itemStyle: { color: '#6baed6', opacity: .42 }, emphasis: { itemStyle: { opacity: 1, color: '#2171b5' } }, data: background },
        { name: 'Selected compound', type: 'scatter', symbolSize: 16, z: 5, itemStyle: { color: '#08306b', borderColor: '#fff', borderWidth: 2 }, data: selected },
      ],
    };
  }, [data, method]);

  useEffect(() => {
    if (!ref.current || navigator.userAgent.toLowerCase().includes('jsdom')) return;
    const chart = echarts.init(ref.current, undefined, { renderer: 'canvas' });
    instance.current = chart;
    const resize = new ResizeObserver(() => chart.resize());
    resize.observe(ref.current);
    chart.on('click', (params) => {
      const row = (params.data as { row?: SweetMetaProjectionContext['points'][number] } | undefined)?.row;
      if (row?.id && row.id !== compoundId) onCompound(row.id);
    });
    return () => { resize.disconnect(); chart.dispose(); instance.current = null; };
  }, [compoundId, onCompound]);

  useEffect(() => { instance.current?.setOption(option, { notMerge: true }); }, [option]);

  return <div className="sdb-detail-projection">
    <div className="sdb-segmented" role="group" aria-label="Projection method">
      <button type="button" className={method === 'umap' ? 'active' : ''} aria-pressed={method === 'umap'} onClick={() => setMethod('umap')}>UMAP</button>
      <button type="button" className={method === 'pca' ? 'active' : ''} aria-pressed={method === 'pca'} onClick={() => setMethod('pca')}>PCA</button>
    </div>
    {error ? <div className="sdb-projection-message">{error}</div> : <div ref={ref} className="sdb-projection-chart" role="img" aria-label={`${method.toUpperCase()} chemical-space context`} />}
    <p>Family context: <strong>{data?.family ?? 'Loading reviewed projection...'}</strong>. Axes are dimensionless and do not encode sweetness or receptor activity.</p>
  </div>;
}
