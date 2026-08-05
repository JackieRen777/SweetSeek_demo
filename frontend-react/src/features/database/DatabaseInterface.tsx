import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { CHEMICAL_SPACE, CHEMICAL_SPACE_BY_CID } from './data/chemicalSpace';
import { loadCompounds } from './data/compoundData';
import type { CompoundFilters, DatabaseView, SimilarCompound, SweetCompound } from './types';
import { DEFAULT_FILTERS, filterAndSortCompounds, formatValue, getReferenceUrl, getSimilarCompounds, getSweetnessTier } from './utils';
import './database.css';

const Molecule3DViewer = lazy(() => import('./components/Molecule3DViewer'));

const SECTIONS = [
  ['overview', 'Overview'], ['sweetness', 'Relative Sweetness'], ['identifiers', 'Structure & Identifiers'],
  ['properties', 'Physicochemical Properties'], ['similar', 'Similar Compounds'],
  ['literature', 'Literature & Evidence'], ['sources', 'Data Sources'],
] as const;

const readNumber = (params: URLSearchParams, key: string) => {
  const raw = params.get(key);
  if (raw === null || raw === '') return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
};

const readUrlState = (): { view: DatabaseView; cid: number | null; filters: CompoundFilters } => {
  const params = new URLSearchParams(window.location.search);
  const requestedView = params.get('view');
  const view: DatabaseView = requestedView === 'atlas' || requestedView === 'list'
    ? requestedView : window.innerWidth < 768 ? 'list' : 'atlas';
  const sort = params.get('sort');
  return {
    view,
    cid: readNumber(params, 'cid'),
    filters: {
      ...DEFAULT_FILTERS,
      query: params.get('q') ?? '',
      sweetnessMin: readNumber(params, 'sweetMin'), sweetnessMax: readNumber(params, 'sweetMax'),
      mwMin: readNumber(params, 'mwMin'), mwMax: readNumber(params, 'mwMax'),
      logpMin: readNumber(params, 'logpMin'), logpMax: readNumber(params, 'logpMax'),
      sort: sort === 'sweetness' || sort === 'mw' || sort === 'logp' ? sort : 'name',
      direction: params.get('dir') === 'desc' ? 'desc' as const : 'asc' as const,
    },
  };
};

const INITIAL_URL_STATE = readUrlState();

const writeUrl = (view: DatabaseView, filters: CompoundFilters, cid: number | null, mode: 'push' | 'replace') => {
  const params = new URLSearchParams();
  params.set('view', view);
  if (filters.query) params.set('q', filters.query);
  if (filters.sweetnessMin !== null) params.set('sweetMin', String(filters.sweetnessMin));
  if (filters.sweetnessMax !== null) params.set('sweetMax', String(filters.sweetnessMax));
  if (filters.mwMin !== null) params.set('mwMin', String(filters.mwMin));
  if (filters.mwMax !== null) params.set('mwMax', String(filters.mwMax));
  if (filters.logpMin !== null) params.set('logpMin', String(filters.logpMin));
  if (filters.logpMax !== null) params.set('logpMax', String(filters.logpMax));
  if (filters.sort !== 'name') params.set('sort', filters.sort);
  if (filters.direction !== 'asc') params.set('dir', filters.direction);
  if (cid !== null) params.set('cid', String(cid));
  window.history[mode === 'push' ? 'pushState' : 'replaceState']({ database: true }, '', `/database?${params}`);
};

const MoleculeImage = ({ compound, compact = false }: { compound: SweetCompound; compact?: boolean }) => {
  const urls = useMemo(() => {
    const candidates: string[] = [];
    const isSmallMolecule = Boolean(compound.smiles);
    const imageSize = compact ? 180 : 700;
    if (compound.structure2dUrl) candidates.push(compound.structure2dUrl);
    if (isSmallMolecule) candidates.push(`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${compound.cid}/PNG?record_type=2d&image_size=${imageSize}x${imageSize}`);
    return candidates;
  }, [compact, compound.cid, compound.smiles, compound.structure2dUrl]);
  const [failure, setFailure] = useState({ cid: compound.cid, index: 0 });
  const index = failure.cid === compound.cid ? failure.index : 0;
  if (!urls[index]) return <div className="db-structure-fallback"><span>Structure unavailable</span></div>;
  return <img className={compact ? 'db-molecule-image compact' : 'db-molecule-image'} src={urls[index]} alt={`${compound.name} 2D structure`} loading={compact ? 'lazy' : 'eager'} decoding="async" fetchPriority={compact ? 'auto' : 'high'} onError={() => setFailure({ cid: compound.cid, index: index + 1 })} />;
};

const Value = ({ value, suffix = '', digits = 2 }: { value: number | string | null; suffix?: string; digits?: number }) => (
  <span className={value === null ? 'db-missing' : ''}>{formatValue(value, digits)}{value === null ? '' : suffix}</span>
);

const sweetnessClass = (value: number | null) => `db-relative-sweetness tier-${getSweetnessTier(value)}`;

const FilterPanel = ({ filters, onChange, onClear }: {
  filters: CompoundFilters; onChange: (patch: Partial<CompoundFilters>) => void; onClear: () => void;
}) => {
  const numeric = (key: keyof CompoundFilters, value: string) => onChange({ [key]: value === '' ? null : Number(value) });
  return (
    <div className="db-filter-panel" data-testid="filter-panel">
      <div className="db-filter-heading"><span>Range filters</span><button onClick={onClear}>Clear all</button></div>
      <div className="db-filter-grid">
        <label>Sweetness<input aria-label="Minimum sweetness" type="number" placeholder="Min" value={filters.sweetnessMin ?? ''} onChange={(event) => numeric('sweetnessMin', event.target.value)} /><input aria-label="Maximum sweetness" type="number" placeholder="Max" value={filters.sweetnessMax ?? ''} onChange={(event) => numeric('sweetnessMax', event.target.value)} /></label>
        <label>Molecular weight<input aria-label="Minimum molecular weight" type="number" placeholder="Min" value={filters.mwMin ?? ''} onChange={(event) => numeric('mwMin', event.target.value)} /><input aria-label="Maximum molecular weight" type="number" placeholder="Max" value={filters.mwMax ?? ''} onChange={(event) => numeric('mwMax', event.target.value)} /></label>
        <label>LogP<input aria-label="Minimum LogP" type="number" placeholder="Min" value={filters.logpMin ?? ''} onChange={(event) => numeric('logpMin', event.target.value)} /><input aria-label="Maximum LogP" type="number" placeholder="Max" value={filters.logpMax ?? ''} onChange={(event) => numeric('logpMax', event.target.value)} /></label>
      </div>
    </div>
  );
};

const SweetnessAtlas = ({ compounds, onSelect }: { compounds: SweetCompound[]; onSelect: (cid: number) => void }) => {
  const usable = compounds.filter((compound) => CHEMICAL_SPACE_BY_CID.has(compound.cid));
  const [hovered, setHovered] = useState<SweetCompound | null>(null);
  const saved = (() => { try { return JSON.parse(sessionStorage.getItem('sweetness-atlas-transform') ?? '{}'); } catch { return {}; } })() as { zoom?: number; x?: number; y?: number };
  const [zoom, setZoom] = useState(saved.zoom ?? 1);
  const [pan, setPan] = useState({ x: saved.x ?? 0, y: saved.y ?? 0 });
  const drag = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const color = (value: number | null) => {
    const tier = getSweetnessTier(value);
    return { unknown: '#a7b0b4', 'below-sucrose': '#8d999f', low: '#3f8b67', medium: '#d59a2f', high: '#d4514a' }[tier];
  };
  useEffect(() => sessionStorage.setItem('sweetness-atlas-transform', JSON.stringify({ zoom, ...pan })), [zoom, pan]);
  const reset = () => { setZoom(1); setPan({ x: 0, y: 0 }); };
  return (
    <section className="db-atlas" aria-label="Chemical Structure Space" data-testid="sweetness-atlas">
      <div className="db-panel-title">
        <div><span className="db-eyebrow">Structure fingerprint map</span><h2>Chemical Structure Space</h2><p>Small molecules positioned by PubChem fingerprint similarity; color represents relative sweetness.</p></div>
        <div className="db-atlas-actions"><span>{usable.length} of {compounds.length} visible records plotted</span><button onClick={() => setZoom((value) => Math.min(3.5, value * 1.2))}>Zoom in</button><button onClick={() => setZoom((value) => Math.max(.7, value / 1.2))}>Zoom out</button><button onClick={reset}>Reset view</button></div>
      </div>
      <div className="db-atlas-stage">
        {!usable.length ? <div className="db-empty"><h3>No fingerprinted small molecules match these filters</h3><p>Clear or widen the filters to restore the chemical space.</p></div> : (
          <svg viewBox="0 0 1000 560" role="img" aria-label={`${usable.length} compounds plotted by structural fingerprint similarity`}
            onPointerDown={(event) => { drag.current = { x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y }; event.currentTarget.setPointerCapture(event.pointerId); }}
            onPointerMove={(event) => { if (drag.current) setPan({ x: drag.current.panX + event.clientX - drag.current.x, y: drag.current.panY + event.clientY - drag.current.y }); }}
            onPointerUp={() => { drag.current = null; }}>
            <defs><pattern id="db-grid" width="50" height="50" patternUnits="userSpaceOnUse"><path d="M 50 0 L 0 0 0 50" fill="none" stroke="#dbe4ea" strokeWidth="1" /></pattern></defs>
            <rect width="1000" height="560" fill="url(#db-grid)" />
            <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
              <line x1="82" y1="490" x2="950" y2="490" stroke="#64748b" strokeWidth="1.5" /><line x1="82" y1="40" x2="82" y2="490" stroke="#64748b" strokeWidth="1.5" />
              {usable.map((compound) => {
                const point = CHEMICAL_SPACE_BY_CID.get(compound.cid)!;
                const x = 110 + point.x * 810;
                const y = 465 - point.y * 395;
                return <g key={compound.cid} className="db-atlas-node" transform={`translate(${x} ${y})`} onPointerDown={(event) => event.stopPropagation()} onMouseEnter={() => setHovered(compound)} onMouseLeave={() => setHovered(null)} onClick={() => onSelect(compound.cid)} role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') onSelect(compound.cid); }} aria-label={`Open ${compound.name}`}>
                  <circle r="9" fill={color(compound.sweetness)} stroke="white" strokeWidth="3" /><circle r="13" fill="none" stroke={color(compound.sweetness)} strokeOpacity=".2" />
                </g>;
              })}
              <text x="510" y="535" textAnchor="middle" className="db-axis-label">Chemical space dimension 1</text>
              <text x="25" y="270" transform="rotate(-90 25 270)" textAnchor="middle" className="db-axis-label">Chemical space dimension 2</text>
            </g>
          </svg>
        )}
        {hovered && <div className="db-atlas-tooltip"><MoleculeImage compound={hovered} compact /><div><strong>{hovered.name}</strong><span>CID {hovered.cid}</span><dl><div><dt>Relative sweetness</dt><dd className={sweetnessClass(hovered.sweetness)}>{formatValue(hovered.sweetness)}</dd></div><div><dt>MW</dt><dd>{formatValue(hovered.mw)}</dd></div><div><dt>LogP</dt><dd>{formatValue(hovered.logp)}</dd></div></dl></div></div>}
        <div className="db-sweetness-legend"><span><i className="below" />&lt; 1</span><span><i className="low" />1–&lt;10</span><span><i className="medium" />10–1,000</span><span><i className="high" />&gt; 1,000</span></div>
      </div>
      <div className="db-atlas-note"><span>{CHEMICAL_SPACE.metadata.fingerprint}; {CHEMICAL_SPACE.metadata.distance}; {CHEMICAL_SPACE.metadata.method}. {CHEMICAL_SPACE.excluded.length} records without a valid small-molecule fingerprint are excluded.</span></div>
    </section>
  );
};

const sortLabel = (label: string, field: CompoundFilters['sort'], filters: CompoundFilters) => filters.sort === field ? `${label} (${filters.direction === 'asc' ? 'ascending' : 'descending'})` : label;

const CompoundTable = ({ compounds, filters, onSort, onSelect, onCompare, compared }: {
  compounds: SweetCompound[]; filters: CompoundFilters; onSort: (field: CompoundFilters['sort']) => void;
  onSelect: (cid: number) => void; onCompare: (compound: SweetCompound) => void; compared: number[];
}) => {
  if (!compounds.length) return <div className="db-empty"><h3>No compounds found</h3><p>Try a different name, CID, formula, or range.</p></div>;
  return (
    <section className="db-list-panel">
      <div className="db-list-summary"><div><h2>Compound index</h2><p>{compounds.length} records in the current result set</p></div></div>
      <div className="db-table-wrap"><table><thead><tr><th>Compound</th><th>CID</th><th>Formula</th><th><button onClick={() => onSort('mw')}>{sortLabel('MW', 'mw', filters)}</button></th><th><button onClick={() => onSort('logp')}>{sortLabel('LogP', 'logp', filters)}</button></th><th><button onClick={() => onSort('sweetness')}>{sortLabel('Relative sweetness', 'sweetness', filters)}</button></th><th><span className="sr-only">Actions</span></th></tr></thead>
        <tbody>{compounds.map((compound) => <tr key={compound.cid}><td><button className="db-compound-link" onClick={() => onSelect(compound.cid)}><MoleculeImage compound={compound} compact /><span><strong>{compound.name}</strong><small>{compound.category ?? 'Unclassified'}</small></span></button></td><td className="db-mono">{compound.cid}</td><td className="db-mono"><Value value={compound.formula} /></td><td><Value value={compound.mw} /></td><td><Value value={compound.logp} /></td><td><span className={sweetnessClass(compound.sweetness)}><Value value={compound.sweetness} /></span></td><td><button className={compared.includes(compound.cid) ? 'db-text-action active' : 'db-text-action'} onClick={() => onCompare(compound)}>{compared.includes(compound.cid) ? 'Selected' : 'Compare'}</button></td></tr>)}</tbody></table></div>
      <div className="db-mobile-list">{compounds.map((compound) => <article key={compound.cid}><button className="db-mobile-main" onClick={() => onSelect(compound.cid)}><MoleculeImage compound={compound} compact /><span><strong>{compound.name}</strong><small>CID {compound.cid} · {compound.formula}</small><em className={sweetnessClass(compound.sweetness)}>{formatValue(compound.sweetness)}× sucrose</em></span></button><button className="db-mobile-compare" onClick={() => onCompare(compound)}>{compared.includes(compound.cid) ? 'Selected' : 'Compare'}</button></article>)}</div>
    </section>
  );
};

const SimilarityNetwork = ({ target, neighbors, onSelect }: { target: SweetCompound; neighbors: SimilarCompound[]; onSelect: (cid: number) => void }) => {
  const [hovered, setHovered] = useState<SimilarCompound | null>(null);
  if (neighbors.length < 3) return <div className="db-empty compact"><h3>Not enough comparable properties</h3><p>At least three shared measured properties are required.</p></div>;
  return <div className="db-network-wrap"><svg className="db-network" viewBox="0 0 760 480" role="img" aria-label={`Property similarity network for ${target.name}`}>
    {neighbors.map((neighbor, index) => { const angle = (index / neighbors.length) * Math.PI * 2 - Math.PI / 2; const radius = index % 2 ? 180 : 150; const x = 380 + Math.cos(angle) * radius; const y = 240 + Math.sin(angle) * radius; return <g key={`edge-${neighbor.compound.cid}`}><line x1="380" y1="240" x2={x} y2={y} stroke={neighbor.sweetnessProximity && neighbor.sweetnessProximity > .65 ? '#ef766c' : '#9fb6c6'} strokeWidth={1 + neighbor.propertySimilarity * 3} strokeOpacity=".65" /></g>; })}
    <g transform="translate(380 240)"><circle r="50" fill="#1f5268" /><text textAnchor="middle" y="4" className="db-network-center">{target.name.slice(0, 14)}</text></g>
    {neighbors.map((neighbor, index) => { const angle = (index / neighbors.length) * Math.PI * 2 - Math.PI / 2; const radius = index % 2 ? 180 : 150; const x = 380 + Math.cos(angle) * radius; const y = 240 + Math.sin(angle) * radius; return <g key={neighbor.compound.cid} className="db-network-node" transform={`translate(${x} ${y})`} onMouseEnter={() => setHovered(neighbor)} onMouseLeave={() => setHovered(null)} onClick={() => onSelect(neighbor.compound.cid)} role="button" tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') onSelect(neighbor.compound.cid); }}><circle r="31" fill="white" stroke="#5b8294" strokeWidth="2" /><text textAnchor="middle" y="4">{neighbor.compound.name.slice(0, 11)}</text></g>; })}
  </svg>{hovered && <div className="db-network-tooltip"><strong>{hovered.compound.name}</strong><span>Property similarity {Math.round(hovered.propertySimilarity * 100)}%</span><span>Sweetness proximity {hovered.sweetnessProximity === null ? 'Not available' : `${Math.round(hovered.sweetnessProximity * 100)}%`}</span><small>{hovered.sharedProperties} shared measured properties</small></div>}<div className="db-network-key"><span><i className="property" /> Property similarity</span><span><i className="sweet" /> High sweetness proximity</span></div></div>;
};

const StructureDisplay = ({ compound }: { compound: SweetCompound }) => {
  const supports3D = Boolean(compound.smiles);
  const [mode, setMode] = useState<'2d' | '3d'>(() => sessionStorage.getItem('sweetness-structure-mode') === '3d' && supports3D ? '3d' : '2d');
  const selectMode = (next: '2d' | '3d') => { setMode(next); sessionStorage.setItem('sweetness-structure-mode', next); };
  return <div className="db-structure-viewer">
    <div className="db-structure-toggle" aria-label="Structure view">
      <button className={mode === '2d' ? 'active' : ''} onClick={() => selectMode('2d')}>2D</button>
      <button className={mode === '3d' ? 'active' : ''} disabled={!supports3D} onClick={() => selectMode('3d')}>3D</button>
    </div>
    <div className="db-structure-canvas">{mode === '2d' ? <MoleculeImage compound={compound} /> : <Suspense fallback={<div className="db-structure-message"><strong>Preparing 3D viewer</strong></div>}><Molecule3DViewer cid={compound.cid} name={compound.name} smiles={compound.smiles ?? ''} /></Suspense>}</div>
    <div className="db-structure-audit"><span>{mode === '2d' ? 'High-resolution 2D depiction' : 'PubChem 3D conformer'}</span><strong>Pending curator verification</strong></div>
  </div>;
};

const LiteratureReferenceCard = ({ reference, index }: { reference: SweetCompound['references'][number]; index: number }) => {
  const url = getReferenceUrl(reference);
  const body = <>
    <div className="db-reference-index">{String(index + 1).padStart(2, '0')}</div>
    <div className="db-reference-content">
      <div className="db-reference-status">{reference.relation === 'curated-evidence' ? 'Curated evidence' : 'Indexed mention'}</div>
      <h3>{reference.title}</h3>
      {reference.authors.length > 0 && <p>{reference.authors.join(', ')}</p>}
      <div className="db-reference-meta"><span>{reference.journal ?? 'Journal not available'}</span><strong>{reference.year ?? 'Year not available'}</strong></div>
      {reference.excerpt && <blockquote>{reference.excerpt}</blockquote>}
      {reference.relatedFields.length > 0 && <div className="db-reference-fields">{reference.relatedFields.map((field) => <span key={field}>{field}</span>)}</div>}
    </div>
    {url && <span className="db-reference-open">{reference.doi ? 'Open DOI' : 'Open PubMed'}</span>}
  </>;
  return <article className={url ? 'has-link' : ''}>{url ? <a href={url} target="_blank" rel="noreferrer">{body}</a> : body}</article>;
};

const CompoundDetail = ({ compound, compounds, onBack, onSelect, onCompare, isCompared }: {
  compound: SweetCompound; compounds: SweetCompound[]; onBack: () => void; onSelect: (cid: number) => void;
  onCompare: (compound: SweetCompound) => void; isCompared: boolean;
}) => {
  const similar = useMemo(() => getSimilarCompounds(compound, compounds), [compound, compounds]);
  const completeness = [compound.formula, compound.mw, compound.sweetness, compound.smiles, compound.logp, compound.tpsa, compound.hbondDonor, compound.hbondAcceptor, compound.rotatableBond, compound.heavyAtom].filter((value) => value !== null).length;
  const properties = [['Molecular weight', compound.mw, ' g/mol'], ['XLogP', compound.logp, ''], ['TPSA', compound.tpsa, ' Å²'], ['H-bond donors', compound.hbondDonor, ''], ['H-bond acceptors', compound.hbondAcceptor, ''], ['Rotatable bonds', compound.rotatableBond, ''], ['Heavy atoms', compound.heavyAtom, ''], ['QED', compound.qed, ''], ['SA score', compound.saScore, '']] as const;
  return <div className="db-detail" data-testid="compound-detail">
    <header className="db-detail-toolbar"><button className="db-back-button" onClick={onBack}>Back to explore</button><span>Sweetness Database / CID {compound.cid}</span></header>
    <div className="db-detail-grid"><aside className="db-section-nav" aria-label="Compound detail sections">{SECTIONS.map(([id, label]) => <a key={id} href={`#${id}`}>{label}</a>)}</aside>
      <main className="db-detail-main">
        <section className="db-detail-hero" id="overview"><div className="db-detail-structure"><StructureDisplay compound={compound} /></div><div className="db-detail-heading"><span className="db-eyebrow">CID {compound.cid} · {compound.category ?? 'Category not curated'}</span><h1>{compound.name}</h1><p>{compound.description ?? 'Description not yet curated for this prototype record.'}</p><div className="db-hero-metrics"><div><span>Relative sweetness</span><strong className={sweetnessClass(compound.sweetness)}>{formatValue(compound.sweetness)}</strong><small>× sucrose reference</small></div><div><span>Molecular formula</span><strong className="db-mono">{formatValue(compound.formula)}</strong><small>{formatValue(compound.mw)} g/mol</small></div><div><span>Record coverage</span><strong>{completeness}/10</strong><small>core fields populated</small></div></div><button className={isCompared ? 'db-primary-button selected' : 'db-primary-button'} onClick={() => onCompare(compound)}>{isCompared ? 'Added to compare' : 'Add to compare'}</button></div></section>
        <section className="db-detail-section" id="sweetness"><div className="db-section-heading"><div><h2>Relative Sweetness</h2><p>Reported potency relative to sucrose under the source dataset convention.</p></div></div><div className={`db-sweetness-display tier-${getSweetnessTier(compound.sweetness)}`}><div><span>Relative sweetness</span><strong className={sweetnessClass(compound.sweetness)}>{formatValue(compound.sweetness)}</strong><small>Sucrose = 1</small></div><div className="db-sweetness-bands"><span className="below">Below sucrose<strong>&lt; 1</strong></span><span className="low">Low<strong>1–&lt;10</strong></span><span className="medium">Medium<strong>10–1,000</strong></span><span className="high">High<strong>&gt; 1,000</strong></span></div></div></section>
        <section className="db-detail-section" id="identifiers"><div className="db-section-heading"><div><h2>Structure & Identifiers</h2><p>Only verified identifiers from the source record are displayed.</p></div></div><dl className="db-identifier-list"><div><dt>Canonical SMILES</dt><dd>{formatValue(compound.smiles)}</dd></div><div><dt>Isomeric SMILES</dt><dd>{formatValue(compound.isomericSmiles)}</dd></div><div><dt>InChIKey</dt><dd>{formatValue(compound.inchiKey)}</dd></div><div><dt>IUPAC name</dt><dd>{formatValue(compound.iupacName)}{compound.iupacName === null && <small className="db-field-note">The test workbook contains a placeholder rather than a verified IUPAC name.</small>}</dd></div></dl></section>
        <section className="db-detail-section" id="properties"><div className="db-section-heading"><div><h2>Physicochemical Properties</h2><p>Values supplied by the current source record; verification status is stated under Data Sources.</p></div></div><div className="db-property-grid">{properties.map(([label, value, suffix]) => <div key={label}><span>{label}</span><strong><Value value={value} suffix={suffix} /></strong></div>)}</div></section>
        <section className="db-detail-section" id="similar"><div className="db-section-heading"><div><h2>Similar Compounds</h2><p>Nearest neighbors by standardized properties; sweetness proximity is shown separately.</p></div></div><SimilarityNetwork target={compound} neighbors={similar} onSelect={onSelect} /></section>
        <section className="db-detail-section" id="literature"><div className="db-section-heading"><div><h2>Literature & Evidence</h2><p>Papers whose indexed text explicitly mentions this compound. A mention is discoverability evidence, not proof of a scientific claim.</p></div></div>{compound.references.length ? <div className="db-reference-list">{compound.references.map((reference, index) => <LiteratureReferenceCard key={`${reference.doi ?? reference.pubmedId ?? reference.title}-${index}`} reference={reference} index={index} />)}</div> : <div className="db-evidence-empty"><div><strong>Literature links not yet available</strong><p>The current compound dataset has no structured RAG-to-compound links. Mention cards will appear here once the new database exports title, authors, year, journal, DOI or PubMed ID, and the matched excerpt.</p></div></div>}</section>
        <section className="db-detail-section" id="sources"><div className="db-section-heading"><div><h2>Data Sources</h2><p>Provenance for the values displayed on this page.</p></div></div><div className="db-source-row"><div><strong>{compound.source.label}</strong><span>Source type: {compound.source.kind}</span><p>{compound.source.kind === 'prototype-workbook' ? 'This test record contains unverified prototype values and must not be treated as a curated chemical record.' : 'CID is used as the stable record identifier. Missing values are preserved rather than inferred.'}</p></div></div></section>
      </main></div>
  </div>;
};

const ComparePanel = ({ compounds, onClose, onRemove, onClear }: { compounds: SweetCompound[]; onClose: () => void; onRemove: (cid: number) => void; onClear: () => void }) => {
  const rows: Array<[string, (compound: SweetCompound) => number | string | null, string]> = [
    ['Relative sweetness', (c) => c.sweetness, '×'], ['Molecular weight', (c) => c.mw, ' g/mol'], ['LogP', (c) => c.logp, ''], ['TPSA', (c) => c.tpsa, ' Å²'], ['H-bond donors', (c) => c.hbondDonor, ''], ['H-bond acceptors', (c) => c.hbondAcceptor, ''], ['Rotatable bonds', (c) => c.rotatableBond, ''], ['Category', (c) => c.category ?? 'Not curated', ''], ['Data source', (c) => c.source.label, ''],
  ];
  return <div className="db-compare-modal" role="dialog" aria-modal="true" aria-label="Compound comparison"><div className="db-compare-sheet"><header><div><span className="db-eyebrow">Side-by-side analysis</span><h2>Compare compounds</h2><p>{compounds.length} of 3 selected</p></div><div><button onClick={onClear}>Clear all</button><button className="db-close-button" onClick={onClose}>Close</button></div></header><div className="db-compare-table"><div className="db-compare-row heading"><strong>Property</strong>{compounds.map((compound) => <div key={compound.cid}><MoleculeImage compound={compound} compact /><strong>{compound.name}</strong><span>CID {compound.cid}</span><button title={`Remove ${compound.name}`} onClick={() => onRemove(compound.cid)}>Remove</button></div>)}</div>{rows.map(([label, getter, suffix]) => <div className="db-compare-row" key={label}><strong>{label}</strong>{compounds.map((compound) => <span key={compound.cid}><Value value={getter(compound)} suffix={suffix} /></span>)}</div>)}</div></div></div>;
};

const DatabaseInterface = () => {
  const initial = INITIAL_URL_STATE;
  const [compounds, setCompounds] = useState<SweetCompound[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<DatabaseView>(initial.view);
  const [filters, setFilters] = useState<CompoundFilters>(initial.filters);
  const [selectedCid, setSelectedCid] = useState<number | null>(initial.cid);
  const [showFilters, setShowFilters] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [compared, setCompared] = useState<number[]>(() => { try { return JSON.parse(sessionStorage.getItem('sweetness-compare') ?? '[]'); } catch { return []; } });
  useEffect(() => { loadCompounds().then((result) => { setCompounds(result.compounds); setLoading(false); }); }, []);
  useEffect(() => { const pop = () => { const state = readUrlState(); setView(state.view); setFilters(state.filters); setSelectedCid(state.cid); }; window.addEventListener('popstate', pop); return () => window.removeEventListener('popstate', pop); }, []);
  useEffect(() => sessionStorage.setItem('sweetness-compare', JSON.stringify(compared)), [compared]);
  const visible = useMemo(() => filterAndSortCompounds(compounds, filters), [compounds, filters]);
  const selected = selectedCid === null ? null : compounds.find((compound) => compound.cid === selectedCid) ?? null;
  const comparedCompounds = compared.map((cid) => compounds.find((compound) => compound.cid === cid)).filter((compound): compound is SweetCompound => Boolean(compound));
  const updateFilters = (patch: Partial<CompoundFilters>) => { const next = { ...filters, ...patch }; setFilters(next); writeUrl(view, next, selectedCid, 'replace'); };
  const changeView = (next: DatabaseView) => { setView(next); writeUrl(next, filters, null, 'push'); setSelectedCid(null); };
  const select = (cid: number) => {
    sessionStorage.setItem('sweetness-database-scroll', String(document.querySelector('.db-shell')?.scrollTop ?? 0));
    setSelectedCid(cid);
    writeUrl(view, filters, cid, 'push');
    requestAnimationFrame(() => { const shell = document.querySelector('.db-shell'); if (shell) shell.scrollTop = 0; });
  };
  const back = () => { setSelectedCid(null); writeUrl(view, filters, null, 'push'); requestAnimationFrame(() => { const shell = document.querySelector('.db-shell'); if (shell) shell.scrollTop = Number(sessionStorage.getItem('sweetness-database-scroll') ?? 0); }); };
  const toggleCompare = (compound: SweetCompound) => { if (compared.includes(compound.cid)) { setCompared((items) => items.filter((cid) => cid !== compound.cid)); return; } if (compared.length >= 3) { setNotice('Comparison is limited to three compounds. Remove one before adding another.'); window.setTimeout(() => setNotice(null), 3500); return; } setCompared((items) => [...items, compound.cid]); };
  const sort = (field: CompoundFilters['sort']) => updateFilters({ sort: field, direction: filters.sort === field && filters.direction === 'asc' ? 'desc' : 'asc' });
  if (loading) return <div className="db-loading"><span>Loading Sweetness Database</span></div>;
  if (selected) return <div className="db-shell overflow-auto"><CompoundDetail compound={selected} compounds={compounds} onBack={back} onSelect={select} onCompare={toggleCompare} isCompared={compared.includes(selected.cid)} />{notice && <div className="db-toast" role="status">{notice}</div>}{compared.length > 0 && <CompareDock compounds={comparedCompounds} onOpen={() => setCompareOpen(true)} onRemove={(cid) => setCompared((items) => items.filter((item) => item !== cid))} />}{compareOpen && <ComparePanel compounds={comparedCompounds} onClose={() => setCompareOpen(false)} onRemove={(cid) => setCompared((items) => items.filter((item) => item !== cid))} onClear={() => setCompared([])} />}</div>;
  const measured = compounds.filter((compound) => compound.sweetness !== null).length;
  const descriptorComplete = compounds.filter((compound) => [compound.mw, compound.logp, compound.tpsa].every((value) => value !== null)).length;
  return <div className="db-shell overflow-auto"><div className="db-workbench">
    <div className="db-controls"><div className="db-search"><input aria-label="Search compounds" placeholder="Search by compound name, CID, alias, or formula" value={filters.query} onChange={(event) => updateFilters({ query: event.target.value })} />{filters.query && <button title="Clear search" onClick={() => updateFilters({ query: '' })}>Clear</button>}</div><button className={showFilters ? 'db-filter-button active' : 'db-filter-button'} onClick={() => setShowFilters((value) => !value)}>Filters</button><div className="db-view-toggle" aria-label="Database view"><button className={view === 'atlas' ? 'active' : ''} onClick={() => changeView('atlas')}>Chemical space</button><button className={view === 'list' ? 'active' : ''} onClick={() => changeView('list')}>List</button></div></div>
    {showFilters && <FilterPanel filters={filters} onChange={updateFilters} onClear={() => updateFilters({ ...DEFAULT_FILTERS, query: filters.query })} />}
    <div className="db-stats"><div><span><strong>{compounds.length}</strong> prototype records</span></div><div><span><strong>{measured}</strong> with sweetness data</span></div><div><span><strong>{descriptorComplete}</strong> with descriptor values</span></div><div><span><strong>{visible.length}</strong> currently visible</span></div></div>
    {view === 'atlas' ? <SweetnessAtlas compounds={visible} onSelect={select} /> : <CompoundTable compounds={visible} filters={filters} onSort={sort} onSelect={select} onCompare={toggleCompare} compared={compared} />}
  </div>{notice && <div className="db-toast" role="status">{notice}</div>}{compared.length > 0 && <CompareDock compounds={comparedCompounds} onOpen={() => setCompareOpen(true)} onRemove={(cid) => setCompared((items) => items.filter((item) => item !== cid))} />}{compareOpen && <ComparePanel compounds={comparedCompounds} onClose={() => setCompareOpen(false)} onRemove={(cid) => setCompared((items) => items.filter((item) => item !== cid))} onClear={() => setCompared([])} />}</div>;
};

const CompareDock = ({ compounds, onOpen, onRemove }: { compounds: SweetCompound[]; onOpen: () => void; onRemove: (cid: number) => void }) => <div className="db-compare-dock"><div className="db-dock-title"><span><strong>Compare</strong><small>{compounds.length}/3 selected</small></span></div><div className="db-dock-items">{compounds.map((compound) => <span key={compound.cid}>{compound.name}<button title={`Remove ${compound.name}`} onClick={() => onRemove(compound.cid)}>Remove</button></span>)}</div><button className="db-compare-open" onClick={onOpen}>Compare now</button></div>;

export default DatabaseInterface;
