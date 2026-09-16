import { useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  AlertTriangle, ArrowLeft, ArrowRight, BarChart3, Beaker, BookOpen, ChevronDown,
  ChevronLeft, ChevronRight, CircleHelp, Database, Download, ExternalLink,
  FileWarning, Filter, FlaskConical, Home, Library, LockKeyhole, Menu,
  Search, ShieldCheck, TableProperties, X,
} from 'lucide-react';
import { CHEMICAL_SPACE, type ChemicalSpacePoint } from './data/chemicalSpace';
import { DATABASE_COMPOUNDS, DATABASE_METADATA, formatNumber, readable, tierCode } from './data/portalData';
import type { DatabaseCompound, DatabaseSection } from './types';
import './database.css';

const SECTIONS: Array<{ id: DatabaseSection; label: string; icon: typeof Database }> = [
  { id: 'overview', label: 'Home', icon: Home },
  { id: 'compounds', label: 'Browse', icon: Beaker },
  { id: 'evidence', label: 'Evidence', icon: ShieldCheck },
  { id: 'literature', label: 'Literature', icon: Library },
  { id: 'statistics', label: 'Statistics', icon: BarChart3 },
  { id: 'downloads', label: 'Downloads', icon: Download },
  { id: 'guide', label: 'Data Guide', icon: TableProperties },
];

const TIER_INFO = {
  R1: { title: 'High readiness', detail: 'Strong traceability and no significant evidence gap.' },
  R2: { title: 'Traceable', detail: 'Traceable sweet evidence with partial depth or coverage.' },
  R3: { title: 'Dataset supported', detail: 'Supported by a single dataset; independent references are still needed.' },
  R4: { title: 'High-risk identity', detail: 'Connectivity or identity requires manual scientific review.' },
};

const initialState = () => {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get('section') as DatabaseSection | null;
  return {
    section: SECTIONS.some((item) => item.id === requested) ? requested! : 'overview' as DatabaseSection,
    compoundId: params.get('compound'),
    query: params.get('q') ?? '',
    tier: params.get('tier') ?? 'all',
  };
};

const updateUrl = (section: DatabaseSection, compoundId: string | null, search?: { query: string; tier: string }, mode: 'push' | 'replace' = 'push') => {
  const params = new URLSearchParams();
  params.set('section', section);
  if (compoundId) params.set('compound', compoundId);
  if (search?.query) params.set('q', search.query);
  if (search?.tier && search.tier !== 'all') params.set('tier', search.tier);
  window.history[mode === 'push' ? 'pushState' : 'replaceState']({ database: true }, '', `/database?${params}`);
};

const MoleculeImage = ({ compound, small = false }: { compound: DatabaseCompound; small?: boolean }) => {
  const [failed, setFailed] = useState(false);
  const cid = compound.pubchem?.matchStatus === 'verified' ? compound.pubchem.cid : null;
  if (!cid || failed) return <div className={`sdb-structure-empty ${small ? 'small' : ''}`}><FlaskConical /></div>;
  return <img className={`sdb-structure ${small ? 'small' : ''}`} src={`https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/PNG?record_type=2d&image_size=${small ? 140 : 500}x${small ? 140 : 500}`} alt={`${compound.name} verified structure`} onError={() => setFailed(true)} />;
};

const TierBadge = ({ tier }: { tier: string | null }) => {
  const code = tierCode(tier);
  return <span className={`sdb-tier tier-${code.toLowerCase()}`}>{code}</span>;
};

const ReviewBadge = ({ compound }: { compound: DatabaseCompound }) => compound.review.required || compound.pubchem?.matchStatus === 'matched-with-discrepancy'
  ? <span className="sdb-review"><AlertTriangle size={13} /> Manual review</span>
  : <span className="sdb-verified"><ShieldCheck size={13} /> Released</span>;

const EmptyState = ({ icon: Icon, title, children }: { icon: typeof Database; title: string; children: React.ReactNode }) => (
  <div className="sdb-empty-state"><Icon /><h3>{title}</h3><p>{children}</p></div>
);

const DistributionBars = ({ data, total }: { data: Record<string, number>; total: number }) => (
  <div className="sdb-bars">
    {Object.entries(data).sort(([a], [b]) => a.localeCompare(b)).map(([label, count]) => (
      <div className="sdb-bar-row" key={label}>
        <span>{label.startsWith('R') ? <><TierBadge tier={label} /> {readable(label)}</> : readable(label)}</span>
        <div><i style={{ width: `${Math.max(2, count / total * 100)}%` }} /></div>
        <strong>{count.toLocaleString()}</strong>
      </div>
    ))}
  </div>
);

const CompoundLandscape = ({ onSelect }: { onSelect: (id: string) => void }) => {
  const [hovered, setHovered] = useState<{ compound: DatabaseCompound; point: ChemicalSpacePoint } | null>(null);
  const points = useMemo(() => {
    const compoundsById = new Map(DATABASE_COMPOUNDS.map((compound) => [compound.id, compound]));
    return CHEMICAL_SPACE.points.flatMap((point) => {
      const compound = compoundsById.get(point.id);
      return compound ? [{ point, compound }] : [];
    });
  }, []);
  return (
    <section className="sdb-landscape">
      <div className="sdb-section-title"><div><span>Interactive chemical space</span><h2>ECFP4 structural similarity map</h2><p>Each point represents one molecule. Nearby points have similar ECFP4 fingerprints; colors represent deterministic fingerprint-space clusters.</p></div></div>
      <div className="sdb-landscape-canvas">
        <div className="sdb-space-stage">
          <svg viewBox="0 0 1000 400" role="img" aria-label="ECFP4 UMAP structural similarity map">
            <defs><pattern id="space-grid" width="92" height="72" patternUnits="userSpaceOnUse"><path d="M92 0H0V72" fill="none" stroke="#edf1f4" /></pattern></defs>
            <rect x="44" y="20" width="924" height="330" rx="4" fill="url(#space-grid)" className="sdb-space-field" />
            {points.map(({ point, compound }) => {
              const x = 54 + point.x * 904;
              const y = 340 - point.y * 310;
              const show = () => setHovered({ compound, point });
              return <circle key={compound.id} cx={x} cy={y} r={compound.review.required ? 2.25 : 1.7} className={`sdb-dot cluster-${point.cluster.toLowerCase()}`} tabIndex={0} role="button" aria-label={`Inspect ${compound.name}`} onMouseEnter={show} onMouseLeave={() => setHovered(null)} onFocus={show} onBlur={() => setHovered(null)} onClick={() => onSelect(compound.id)} onKeyDown={(event) => event.key === 'Enter' && onSelect(compound.id)} />;
            })}
            <text x="506" y="382" textAnchor="middle" className="sdb-axis-label">UMAP 1</text>
            <text x="18" y="185" transform="rotate(-90 18 185)" textAnchor="middle" className="sdb-axis-label">UMAP 2</text>
          </svg>
          {hovered && <div className={`sdb-space-tooltip ${hovered.point.y > 0.72 ? 'below' : ''}`} role="status" style={{ left: `${17 + hovered.point.x * 66}%`, top: `${6 + (1 - hovered.point.y) * 78}%` }}>
            <div className="sdb-space-tooltip-head"><MoleculeImage compound={hovered.compound} small /><span><strong>{hovered.compound.name}</strong><small>{hovered.compound.id}</small></span></div>
            <dl><div><dt>Molecular formula</dt><dd>{hovered.compound.formula ?? 'Not available'}</dd></div><div><dt>Molecular weight</dt><dd>{formatNumber(hovered.compound.molecularWeight)} Da</dd></div><div><dt>Structural cluster</dt><dd>{hovered.point.cluster}</dd></div><div><dt>Evidence tier</dt><dd><TierBadge tier={hovered.compound.evidence.releaseTier} /></dd></div><div><dt>Assertions</dt><dd>{hovered.compound.evidence.acceptedAssertions}</dd></div></dl>
            <small className="sdb-space-tooltip-action">Click to open record</small>
          </div>}
        </div>
        <div className="sdb-space-footer">
          <div className="sdb-legend">{CHEMICAL_SPACE.metadata.clusters.map((cluster) => <span key={cluster.id}><i className={`cluster-${cluster.id.toLowerCase()}`} /><b>{cluster.id}</b> {cluster.size.toLocaleString()} molecules</span>)}</div>
          <p><span>{CHEMICAL_SPACE.metadata.mappedRecordCount.toLocaleString()} molecules mapped</span><span>ECFP4 · Tanimoto distance · k-medoids · UMAP</span></p>
          <small>Proximity represents local structural similarity. UMAP axes are dimensionless and do not represent sweetness or a physical molecular property.</small>
        </div>
      </div>
    </section>
  );
};

const HERO_MOLECULES = [
  { name: 'Sucralose', file: '/database-assets/sucralose.png' },
  { name: 'Aspartame', file: '/database-assets/aspartame.png' },
  { name: 'Stevioside', file: '/database-assets/stevioside.png' },
  { name: 'Thiophenesaccharin', file: '/database-assets/thiophenesaccharin.png' },
];

const EXAMPLE_COMPOUNDS = [
  { name: 'Sucrose', id: 'CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N' },
  { name: 'Glucose', id: 'CMP_GZCGUPFRVQAUEE-SLPGGIOYSA-N' },
  { name: 'Aspartame', id: 'CMP_IAOZJIPTCAWIRG-QWRGUYRKSA-N' },
];

const Overview = ({ onSection, onSelect, onSearch }: {
  onSection: (section: DatabaseSection) => void;
  onSelect: (id: string) => void;
  onSearch: (query: string, tier: string) => void;
}) => {
  const [query, setQuery] = useState('');
  const [tier, setTier] = useState('all');
  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    onSearch(query.trim(), tier);
  };
  return <div className="sdb-home">
    <section className="sdb-hero">
      <div className="sdb-hero-inner">
        <div className="sdb-hero-copy">
          <h1>SweetMeta</h1>
          <p>Explore traceable identities, evidence readiness, and verified chemical properties across the evolving landscape of sweet entities.</p>
          <form className="sdb-hero-search" onSubmit={submitSearch}>
            <label className="sdb-search-input"><Search size={20} /><input aria-label="Search SweetMeta" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, stable ID, formula, InChIKey, or PubChem CID" /></label>
            <label className="sdb-hero-select"><span>Entity</span><select aria-label="Entity type" defaultValue="all"><option value="all">All entities</option></select><ChevronDown size={15} /></label>
            <label className="sdb-hero-select"><span>Evidence</span><select aria-label="Homepage evidence tier" value={tier} onChange={(event) => setTier(event.target.value)}><option value="all">All tiers</option>{Object.keys(TIER_INFO).map((item) => <option value={item} key={item}>{item}</option>)}</select><ChevronDown size={15} /></label>
            <button type="submit" aria-label="Search database"><Search size={18} /><span>Search</span></button>
          </form>
          <div className="sdb-hero-links"><span>Example:</span>{EXAMPLE_COMPOUNDS.map((example, index) => <span key={example.id}><button onClick={() => onSelect(example.id)}>{example.name}</button>{index < EXAMPLE_COMPOUNDS.length - 1 && ','}</span>)}</div>
        </div>
        <div className="sdb-molecule-stage" aria-label="Verified structures represented in the current release">
          {HERO_MOLECULES.map((molecule, index) => <figure key={molecule.name} className={`molecule-${index + 1}`}><img src={molecule.file} alt={`${molecule.name} structure`} /><figcaption>{molecule.name}</figcaption></figure>)}
          <div className="sdb-stage-label"><ShieldCheck size={17} /><span><strong>{DATABASE_METADATA.pubchemVerified.toLocaleString()}</strong> structures cross-checked</span></div>
        </div>
      </div>
    </section>
    <div className="sdb-home-content">
      <section className="sdb-metrics" aria-label="Current release metrics">
        <button onClick={() => onSection('compounds')}><span>Curated records</span><strong>{DATABASE_METADATA.totalRecords.toLocaleString()}</strong><small>Unique stable entity IDs</small></button>
        <button onClick={() => onSection('evidence')}><span>Accepted assertions</span><strong>{DATABASE_METADATA.acceptedAssertions.toLocaleString()}</strong><small>Aggregated source assertions</small></button>
        <button onClick={() => onSection('statistics')}><span>PubChem verified</span><strong>{DATABASE_METADATA.pubchemVerified.toLocaleString()}</strong><small>Exact-key, cross-checked matches</small></button>
        <button onClick={() => onSection('evidence')}><span>Workbook review flags</span><strong>{DATABASE_METADATA.reviewRequired.toLocaleString()}</strong><small>Source records publicly flagged</small></button>
      </section>
      <section className="sdb-explore">
        <div className="sdb-section-title"><div><span>Explore the portal</span><h2>From identity to evidence</h2><p>Each module reflects the current workbook release. Unavailable evidence remains clearly marked rather than inferred.</p></div></div>
        <div className="sdb-module-grid">
          <button onClick={() => onSection('compounds')}><Beaker /><span><strong>Browse entities</strong><small>Search structures, identifiers, formulae, and verified properties.</small></span><ArrowRight /></button>
          <button onClick={() => onSection('evidence')}><ShieldCheck /><span><strong>Evidence register</strong><small>Inspect public readiness tiers, gaps, and manual-review records.</small></span><ArrowRight /></button>
          <button onClick={() => onSection('literature')}><BookOpen /><span><strong>Literature</strong><small>Review current citation coverage and the next-release schema.</small></span><ArrowRight /></button>
          <button onClick={() => onSection('statistics')}><BarChart3 /><span><strong>Release statistics</strong><small>Understand chemical and evidence coverage at a glance.</small></span><ArrowRight /></button>
        </div>
      </section>
      <CompoundLandscape onSelect={onSelect} />
      <div className="sdb-overview-grid">
        <section><div className="sdb-section-title"><div><span>Release evidence</span><h2>Readiness distribution</h2></div></div><DistributionBars data={DATABASE_METADATA.tierCounts} total={DATABASE_METADATA.totalRecords} /></section>
        <section className="sdb-quality-panel"><div className="sdb-section-title"><div><span>Data integrity</span><h2>Known limitations</h2></div></div><ul><li><FileWarning />Quantitative sweetness and experimental conditions are not present.</li><li><BookOpen />Row-level DOI, PMID, and evidence excerpts are not present.</li><li><CircleHelp />Sweet proteins are planned for a later data release.</li></ul><button onClick={() => onSection('evidence')}>Open evidence quality view <ChevronRight size={16} /></button></section>
      </div>
    </div>
  </div>;
};

const CompoundIndex = ({ onSelect, initialQuery, initialTier }: { onSelect: (id: string) => void; initialQuery: string; initialTier: string }) => {
  const [query, setQuery] = useState(initialQuery);
  const [tier, setTier] = useState(initialTier);
  const [review, setReview] = useState('all');
  const [pubchem, setPubchem] = useState('all');
  const [page, setPage] = useState(1);
  const pageSize = 25;
  const filtered = useMemo(() => {
    const q = query.trim().toLocaleLowerCase();
    return DATABASE_COMPOUNDS.filter((compound) => {
      const searchable = [compound.id, compound.name, compound.inchiKey, compound.formula, compound.pubchem?.cid, compound.pubchem?.iupacName].filter(Boolean).join(' ').toLocaleLowerCase();
      return (!q || searchable.includes(q))
        && (tier === 'all' || tierCode(compound.evidence.releaseTier) === tier)
        && (review === 'all' || (review === 'required') === compound.review.required)
        && (pubchem === 'all' || (pubchem === 'matched') === Boolean(compound.pubchem));
    });
  }, [pubchem, query, review, tier]);
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const visible = filtered.slice((page - 1) * pageSize, page * pageSize);
  return (
    <div className="sdb-page">
      <header className="sdb-page-heading compact"><div><span className="sdb-kicker">Compound index</span><h1>Browse the current release</h1><p>Search stable IDs, preferred names, formulae, InChIKeys, or verified PubChem identifiers.</p></div></header>
      <div className="sdb-filterbar">
        <label className="sdb-search"><Search size={18} /><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Search compounds" aria-label="Search compounds" />{query && <button title="Clear search" onClick={() => { setQuery(''); setPage(1); }}><X size={16} /></button>}</label>
        <label><Filter size={16} /><select aria-label="Evidence tier" value={tier} onChange={(event) => { setTier(event.target.value); setPage(1); }}><option value="all">All evidence tiers</option>{Object.keys(TIER_INFO).map((item) => <option value={item} key={item}>{item}</option>)}</select></label>
        <label><select aria-label="Review status" value={review} onChange={(event) => { setReview(event.target.value); setPage(1); }}><option value="all">All review states</option><option value="required">Manual review</option><option value="released">Released</option></select></label>
        <label><select aria-label="PubChem status" value={pubchem} onChange={(event) => { setPubchem(event.target.value); setPage(1); }}><option value="all">All PubChem states</option><option value="matched">PubChem matched</option><option value="unmatched">Not matched</option></select></label>
      </div>
      <div className="sdb-result-meta"><strong>{filtered.length.toLocaleString()}</strong> records <span>Source: {DATABASE_METADATA.sourceWorkbook}</span></div>
      <div className="sdb-table-wrap"><table className="sdb-table"><thead><tr><th>Compound</th><th>Formula</th><th>MW</th><th>Evidence</th><th>Assertions</th><th>Status</th><th>PubChem</th></tr></thead><tbody>{visible.map((compound) => <tr key={compound.id} onClick={() => onSelect(compound.id)}><td><div className="sdb-compound-cell"><MoleculeImage compound={compound} small /><span><strong>{compound.name}</strong><small>{compound.id}</small></span></div></td><td className="sdb-mono">{compound.formula ?? 'Not available'}</td><td>{formatNumber(compound.molecularWeight)}</td><td><TierBadge tier={compound.evidence.releaseTier} /></td><td>{compound.evidence.acceptedAssertions}</td><td><ReviewBadge compound={compound} /></td><td>{compound.pubchem?.cid ? <span className="sdb-pubchem-cell"><a href={compound.pubchem.sourceUrl ?? '#'} onClick={(event) => event.stopPropagation()} target="_blank" rel="noreferrer">CID {compound.pubchem.cid}<ExternalLink size={13} /></a>{compound.pubchem.matchStatus !== 'verified' && <span className="sdb-discrepancy"><AlertTriangle size={12} /> Discrepancy</span>}</span> : <span className="sdb-muted">Not matched</span>}</td></tr>)}</tbody></table></div>
      {!visible.length && <EmptyState icon={Search} title="No matching compounds">Adjust the search term or clear one of the filters.</EmptyState>}
      <div className="sdb-pagination"><button disabled={page === 1} onClick={() => setPage((value) => value - 1)}><ChevronLeft size={17} /> Previous</button><span>Page {page} of {pageCount}</span><button disabled={page === pageCount} onClick={() => setPage((value) => value + 1)}>Next <ChevronRight size={17} /></button></div>
    </div>
  );
};

const Evidence = ({ onSelect }: { onSelect: (id: string) => void }) => {
  const reviewQueue = DATABASE_COMPOUNDS.filter((compound) => compound.review.required).slice(0, 20);
  return <div className="sdb-page"><header className="sdb-page-heading compact"><div><span className="sdb-kicker">Evidence register</span><h1>Evidence readiness and review status</h1><p>All evidence tiers are public. Tiers describe release readiness, not measured sweetness intensity or clinical certainty.</p></div></header>
    <div className="sdb-tier-grid">{Object.entries(TIER_INFO).map(([tier, info]) => <article key={tier}><TierBadge tier={tier} /><strong>{info.title}</strong><p>{info.detail}</p><span>{Object.entries(DATABASE_METADATA.tierCounts).filter(([key]) => key.startsWith(tier)).reduce((sum, [, value]) => sum + value, 0)} records</span></article>)}</div>
    <section className="sdb-data-section"><div className="sdb-section-title"><div><span>Evidence gaps</span><h2>Current release gap profile</h2><p>Gap labels are copied directly from the source workbook.</p></div></div><DistributionBars data={DATABASE_METADATA.gapCounts} total={DATABASE_METADATA.totalRecords} /></section>
    <section className="sdb-data-section"><div className="sdb-section-title"><div><span>Quality control</span><h2>Manual review queue</h2><p>Showing the first 20 of {DATABASE_METADATA.reviewRequired} flagged records. The full ID list is included in the acceptance report.</p></div></div><div className="sdb-review-list">{reviewQueue.map((compound) => <button key={compound.id} onClick={() => onSelect(compound.id)}><AlertTriangle /><span><strong>{compound.name}</strong><small>{compound.id} · {readable(compound.review.identityStatus)}</small></span><ChevronRight /></button>)}</div></section>
  </div>;
};

const Literature = () => <div className="sdb-page"><header className="sdb-page-heading compact"><div><span className="sdb-kicker">Literature registry</span><h1>Compound-linked literature</h1><p>The portal is ready for DOI, PMID, citation metadata, matched excerpts, and evidence-to-compound relationships.</p></div></header><EmptyState icon={BookOpen} title="No row-level literature links in this release">The source workbook contains evidence readiness and accepted assertion counts, but it does not contain paper-level identifiers or excerpts. This module intentionally remains empty until traceable records are supplied.</EmptyState><section className="sdb-schema"><h2>Required fields for the next data release</h2><div><span>compound_id</span><span>DOI or PMID</span><span>title, authors, year, journal</span><span>evidence excerpt</span><span>assertion type</span><span>curation status</span></div></section></div>;

const Statistics = () => {
  const buckets = [0, 150, 300, 450, 600, 900, Infinity];
  const labels = ['<150', '150–299', '300–449', '450–599', '600–899', '900+'];
  const weights = labels.map((label, index) => ({ label, count: DATABASE_COMPOUNDS.filter((item) => item.molecularWeight !== null && item.molecularWeight >= buckets[index] && item.molecularWeight < buckets[index + 1]).length }));
  const max = Math.max(...weights.map((item) => item.count), 1);
  return <div className="sdb-page"><header className="sdb-page-heading compact"><div><span className="sdb-kicker">Release statistics</span><h1>Coverage at a glance</h1><p>All charts are calculated from the current workbook release and verified enrichment records.</p></div></header><div className="sdb-metrics"><div><span>Entity types</span><strong>1</strong><small>Extensible model; proteins pending</small></div><div><span>PubChem matched</span><strong>{DATABASE_METADATA.pubchemMatched}</strong><small>{(DATABASE_METADATA.pubchemMatched / DATABASE_METADATA.totalRecords * 100).toFixed(1)}% coverage</small></div><div><span>Single-assertion records</span><strong>{DATABASE_COMPOUNDS.filter((item) => item.evidence.acceptedAssertions === 1).length}</strong><small>Need deeper evidence coverage</small></div><div><span>Missing heavy atoms</span><strong>{DATABASE_COMPOUNDS.filter((item) => item.heavyAtomCount === null).length}</strong><small>Source workbook values</small></div></div><div className="sdb-stat-grid"><section><div className="sdb-section-title"><div><span>Composition</span><h2>Molecular weight distribution</h2></div></div><div className="sdb-columns">{weights.map((item) => <div key={item.label}><strong>{item.count}</strong><i style={{ height: `${Math.max(3, item.count / max * 100)}%` }} /><span>{item.label}</span></div>)}</div></section><section><div className="sdb-section-title"><div><span>Evidence</span><h2>Readiness distribution</h2></div></div><DistributionBars data={DATABASE_METADATA.tierCounts} total={DATABASE_METADATA.totalRecords} /></section></div></div>;
};

const Downloads = () => <div className="sdb-page"><header className="sdb-page-heading compact"><div><span className="sdb-kicker">Data access</span><h1>Downloads</h1><p>Release metadata is visible, while public file downloads are currently disabled by policy.</p></div></header><div className="sdb-download-list"><article><Database /><span><strong>Source workbook</strong><small>{DATABASE_METADATA.sourceWorkbook} · {DATABASE_METADATA.totalRecords} records</small></span><button disabled><LockKeyhole size={15} /> Restricted</button></article><article><FileWarning /><span><strong>Data quality report</strong><small>Missing fields, review queue, and enrichment coverage</small></span><button disabled><LockKeyhole size={15} /> Restricted</button></article><article><Download /><span><strong>Filtered compound export</strong><small>CSV export for current search results</small></span><button disabled><LockKeyhole size={15} /> Restricted</button></article></div><div className="sdb-policy-note"><LockKeyhole /><div><strong>Download access is not enabled</strong><p>This state is intentional and can be changed later without altering the database schema or compound portal.</p></div></div></div>;

const DataGuide = () => <div className="sdb-page"><header className="sdb-page-heading compact"><div><span className="sdb-kicker">Data guide</span><h1>How to read SweetMeta</h1><p>Definitions, provenance, and release boundaries for interpreting the current portal responsibly.</p></div></header>
  <section className="sdb-guide-intro"><Database /><div><strong>Current release scope</strong><p>The current workbook contains {DATABASE_METADATA.totalRecords.toLocaleString()} small-molecule records. SweetMeta is the product name, not an entity-type restriction: the schema is designed to add sweet proteins and other entity classes in later releases.</p></div></section>
  <div className="sdb-guide-grid">
    <section><div className="sdb-section-title"><div><span>Core fields</span><h2>Available now</h2></div></div><dl className="sdb-guide-list"><div><dt>Identity</dt><dd>Stable ID, preferred name, InChIKey, canonical tautomer key</dd></div><div><dt>Structure</dt><dd>Formula, molecular weight, charge, heavy atoms, SMILES</dd></div><div><dt>Evidence</dt><dd>Release tier, evidence gap, priority score, accepted assertion count</dd></div><div><dt>External enrichment</dt><dd>PubChem CID and properties retained separately from source values</dd></div><div><dt>Quality control</dt><dd>Identity status, manual-review flag, and review note</dd></div></dl></section>
    <section><div className="sdb-section-title"><div><span>Release tiers</span><h2>R1–R4 meaning</h2></div></div><div className="sdb-guide-tiers">{Object.entries(TIER_INFO).map(([tier, info]) => <div key={tier}><TierBadge tier={tier} /><span><strong>{info.title}</strong><small>{info.detail}</small></span></div>)}</div></section>
  </div>
  <section className="sdb-data-section"><div className="sdb-section-title"><div><span>Provenance policy</span><h2>Source and enrichment remain distinct</h2><p>Workbook values are the release source of truth. PubChem values are accepted only after structure-key validation and are displayed as external enrichment; discrepancies are flagged for scientific review rather than silently overwritten.</p></div></div><div className="sdb-provenance-flow"><span>Source workbook<strong>{DATABASE_METADATA.sourceWorkbook}</strong></span><ArrowRight /><span>Validation<strong>Identity and property checks</strong></span><ArrowRight /><span>Public portal<strong>Released or visibly flagged</strong></span></div></section>
  <section className="sdb-data-section"><div className="sdb-section-title"><div><span>Not yet supplied</span><h2>Fields reserved for future releases</h2></div></div><div className="sdb-schema"><div><span>sweet protein identity</span><span>quantitative sweetness</span><span>sensory conditions</span><span>DOI / PMID</span><span>evidence excerpts</span><span>food applications</span><span>receptor evidence</span><span>safety and regulation</span></div></div></section>
</div>;

const Detail = ({ compound, onBack }: { compound: DatabaseCompound; onBack: () => void }) => (
  <div className="sdb-page sdb-detail"><button className="sdb-back" onClick={onBack}><ArrowLeft size={17} /> Back to compounds</button><header className="sdb-detail-header"><div className="sdb-detail-image"><MoleculeImage compound={compound} /></div><div><div className="sdb-detail-badges"><TierBadge tier={compound.evidence.releaseTier} /><ReviewBadge compound={compound} />{compound.pubchem?.matchStatus === 'verified' ? <span className="sdb-pubchem-ok"><ShieldCheck size={13} /> PubChem verified</span> : compound.pubchem ? <span className="sdb-discrepancy"><AlertTriangle size={13} /> PubChem discrepancy</span> : null}</div><h1>{compound.name}</h1><p className="sdb-mono">{compound.id}</p><dl className="sdb-inline-properties"><div><dt>Formula</dt><dd>{compound.formula ?? 'Not available'}</dd></div><div><dt>Molecular weight</dt><dd>{formatNumber(compound.molecularWeight)} Da</dd></div><div><dt>InChIKey</dt><dd>{compound.inchiKey ?? 'Not available'}</dd></div><div><dt>Entity type</dt><dd>{readable(compound.entityType)}</dd></div></dl></div></header>
    {(compound.review.required || compound.pubchem?.matchStatus === 'matched-with-discrepancy') && <div className="sdb-review-callout"><AlertTriangle /><div><strong>Manual scientific review required</strong><p>{compound.pubchem?.matchStatus === 'matched-with-discrepancy' ? 'The external identifier match exposed a source-field discrepancy. Source values were not overwritten; resolve the preferred name and structure identity before release.' : compound.review.note ?? 'No review note was supplied.'}</p></div></div>}
    <div className="sdb-detail-grid"><section><div className="sdb-section-title"><div><span>Evidence summary</span><h2>Sweet evidence readiness</h2></div></div><dl className="sdb-definition-list"><div><dt>Release tier</dt><dd>{readable(compound.evidence.releaseTier)}</dd></div><div><dt>Accepted assertions</dt><dd>{compound.evidence.acceptedAssertions}</dd></div><div><dt>Evidence gap</dt><dd>{readable(compound.evidence.releaseGap)}</dd></div><div><dt>Priority score</dt><dd>{formatNumber(compound.evidence.priorityScore, 0)}</dd></div></dl><p className="sdb-caveat">The workbook does not yet provide assertion-level measurements, conditions, or citations. This summary must not be interpreted as a quantitative sweetness value.</p></section><section><div className="sdb-section-title"><div><span>Structure identity</span><h2>Source identifiers</h2></div></div><dl className="sdb-definition-list"><div><dt>Preferred name source</dt><dd>{compound.nameSource ?? 'Not available'}</dd></div><div><dt>Identity status</dt><dd>{readable(compound.review.identityStatus)}</dd></div><div><dt>Canonical tautomer InChIKey</dt><dd className="sdb-mono">{compound.canonicalTautomerInchiKey ?? 'Not available'}</dd></div><div><dt>Formal charge</dt><dd>{formatNumber(compound.formalCharge, 0)}</dd></div></dl></section></div>
    <section className="sdb-data-section"><div className="sdb-section-title"><div><span>Structure strings</span><h2>Chemical representation</h2></div></div><dl className="sdb-code-list"><div><dt>Isomeric SMILES</dt><dd>{compound.isomericSmiles ?? 'Not available'}</dd></div><div><dt>Canonical SMILES</dt><dd>{compound.canonicalSmiles ?? 'Not available'}</dd></div></dl></section>
    <section className="sdb-data-section"><div className="sdb-section-title"><div><span>External enrichment</span><h2>PubChem properties</h2><p>External values are displayed separately from the source workbook and require an exact InChIKey match.</p></div>{compound.pubchem?.sourceUrl && <a href={compound.pubchem.sourceUrl} target="_blank" rel="noreferrer">Open PubChem <ExternalLink size={15} /></a>}</div>{compound.pubchem ? <dl className="sdb-property-grid"><div><dt>PubChem CID</dt><dd>{compound.pubchem.cid}</dd></div><div><dt>XLogP</dt><dd>{formatNumber(compound.pubchem.xlogp)}</dd></div><div><dt>TPSA</dt><dd>{formatNumber(compound.pubchem.tpsa)} Å²</dd></div><div><dt>H-bond donors</dt><dd>{formatNumber(compound.pubchem.hBondDonorCount, 0)}</dd></div><div><dt>H-bond acceptors</dt><dd>{formatNumber(compound.pubchem.hBondAcceptorCount, 0)}</dd></div><div><dt>Rotatable bonds</dt><dd>{formatNumber(compound.pubchem.rotatableBondCount, 0)}</dd></div><div className="wide"><dt>IUPAC name</dt><dd>{compound.pubchem.iupacName ?? 'Not available'}</dd></div><div className="wide"><dt>Validation</dt><dd>{compound.pubchem.matchStatus === 'verified' ? 'Exact InChIKey, formula, molecular weight, and heavy-atom cross-check passed.' : 'Matched, with at least one source-field discrepancy requiring review.'}</dd></div></dl> : <EmptyState icon={Database} title="No verified PubChem match">No PubChem property record was accepted for this exact InChIKey in the current enrichment run.</EmptyState>}</section>
    <section className="sdb-data-section"><div className="sdb-section-title"><div><span>Literature and applications</span><h2>Evidence details</h2></div></div><EmptyState icon={BookOpen} title="Detailed evidence is not available">Literature citations, sensory conditions, food applications, safety, regulation, receptor evidence, and model predictions are not present in the current workbook.</EmptyState></section>
  </div>
);

const DatabaseInterface = ({ onClose }: { onClose?: () => void }) => {
  const state = initialState();
  const [section, setSection] = useState<DatabaseSection>(state.section);
  const [compoundId, setCompoundId] = useState<string | null>(state.compoundId);
  const [query, setQuery] = useState(state.query);
  const [tier, setTier] = useState(state.tier);
  const [menuOpen, setMenuOpen] = useState(false);
  const compound = compoundId ? DATABASE_COMPOUNDS.find((item) => item.id === compoundId) ?? null : null;
  useEffect(() => { const onPop = () => { const next = initialState(); setSection(next.section); setCompoundId(next.compoundId); setQuery(next.query); setTier(next.tier); setMenuOpen(false); }; window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop); }, []);
  const resetScroll = () => { const main = document.querySelector<HTMLElement>('.sdb-main'); if (main) main.scrollTop = 0; };
  const navigate = (next: DatabaseSection) => { setSection(next); setCompoundId(null); setQuery(''); setTier('all'); setMenuOpen(false); updateUrl(next, null); resetScroll(); };
  const search = (nextQuery: string, nextTier: string) => { setSection('compounds'); setCompoundId(null); setQuery(nextQuery); setTier(nextTier); setMenuOpen(false); updateUrl('compounds', null, { query: nextQuery, tier: nextTier }); resetScroll(); };
  const select = (id: string) => { setSection('compounds'); setCompoundId(id); updateUrl('compounds', id, { query, tier }); resetScroll(); };
  const back = () => { setCompoundId(null); updateUrl('compounds', null, { query, tier }); };
  const leaveDatabase = () => {
    if (onClose) onClose();
    else {
      window.history.pushState({ feature: null }, '', '/');
      window.dispatchEvent(new PopStateEvent('popstate'));
    }
  };
  const activeLabel = compound ? 'Entity record' : SECTIONS.find((item) => item.id === section)?.label;
  return <div className="sdb-shell">
    <header className="sdb-product-header">
      <button className="sdb-product-brand" onClick={() => navigate('overview')} aria-label="SweetMeta home"><span className="sdb-brand-mark"><Database /></span><span><strong>SweetMeta</strong><small>Evidence-led sweet knowledgebase</small></span></button>
      <nav className={menuOpen ? 'open' : ''} aria-label="SweetMeta navigation">{SECTIONS.map(({ id, label }) => <button key={id} className={section === id && !compound ? 'active' : ''} onClick={() => navigate(id)}>{label}{id === 'downloads' && <LockKeyhole className="sdb-nav-lock" />}</button>)}</nav>
      <div className="sdb-header-actions"><button className="sdb-return" onClick={leaveDatabase}><ArrowLeft /> SweetSeek</button><button className="sdb-menu" onClick={() => setMenuOpen((value) => !value)} aria-label={menuOpen ? 'Close database menu' : 'Open database menu'}>{menuOpen ? <X /> : <Menu />}</button></div>
    </header>
    <div className="sdb-mobile-context"><span>{activeLabel}</span><small>{DATABASE_METADATA.totalRecords.toLocaleString()} records</small></div>
    <main className="sdb-main overflow-auto">{compound ? <Detail compound={compound} onBack={back} /> : section === 'overview' ? <Overview onSection={navigate} onSelect={select} onSearch={search} /> : section === 'compounds' ? <CompoundIndex onSelect={select} initialQuery={query} initialTier={tier} /> : section === 'evidence' ? <Evidence onSelect={select} /> : section === 'literature' ? <Literature /> : section === 'statistics' ? <Statistics /> : section === 'downloads' ? <Downloads /> : <DataGuide />}</main>
  </div>;
};

export default DatabaseInterface;
