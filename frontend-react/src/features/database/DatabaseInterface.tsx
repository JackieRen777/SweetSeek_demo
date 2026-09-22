import { lazy, Suspense, useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  AlertTriangle, ArrowLeft, ArrowUpDown, BarChart3, Beaker, BookOpen, ChevronDown,
  ChevronLeft, ChevronRight, CircleHelp, Cuboid, Database, Download, ExternalLink,
  FileWarning, Filter, FlaskConical, Home, Library, LockKeyhole, Menu,
  Search, ShieldCheck, X,
} from 'lucide-react';
import { CHEMICAL_SPACE, type ChemicalSpacePoint } from './data/chemicalSpace';
import { DATABASE_COMPOUNDS, DATABASE_METADATA, formatNumber, readable, tierCode } from './data/portalData';
import LITERATURE_SUMMARY from './data/literatureSummary.generated.json';
import type { DatabaseCompound, DatabaseSection } from './types';
import { fetchSweetMetaCompound, fetchSweetMetaCompounds, fetchSweetMetaLiterature, type SweetMetaCompoundDetail, type SweetMetaLiteratureRecord } from './sweetmetaApi';
import { loadLiteratureData, RELATIONSHIP_LABELS, type CompoundPaperLink, type LiteratureData, type LiteratureRelationship } from './literature';
import Molecule3DViewer, { preloadMolecule3D } from './components/Molecule3DViewer';
import StatisticsDashboard from './components/StatisticsDashboard';
import './database.css';

const ChemicalSpace3D = lazy(() => import('./components/ChemicalSpace3D'));

const SECTIONS: Array<{ id: DatabaseSection; label: string; icon: typeof Database }> = [
  { id: 'overview', label: 'Home', icon: Home },
  { id: 'compounds', label: 'Browse', icon: Beaker },
  { id: 'literature', label: 'Literature', icon: Library },
  { id: 'statistics', label: 'Statistics', icon: BarChart3 },
  { id: 'downloads', label: 'Downloads', icon: Download },
];

const DETAIL_SECTIONS = [
  { id: 'overview', label: 'Overview', icon: CircleHelp },
  { id: 'sweetness', label: 'Relative Sweetness', icon: FlaskConical },
  { id: 'structure', label: 'Structure & Identifiers', icon: Cuboid },
  { id: 'properties', label: 'Physicochemical Properties', icon: Beaker },
  { id: 'similar', label: 'Similar Compounds', icon: Database },
  { id: 'literature-evidence', label: 'Literature & Evidence', icon: BookOpen },
  { id: 'sources', label: 'Data Sources', icon: Library },
] as const;

type DetailSection = typeof DETAIL_SECTIONS[number]['id'];

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
    domain: params.get('domain') ?? '',
    foodGroup: params.get('foodGroup') ?? '',
    sweetnessMinLog10: params.get('sweetnessMinLog10') ?? '',
    sweetnessMaxLog10: params.get('sweetnessMaxLog10') ?? '',
    qualityMetric: params.get('qualityMetric') ?? '',
    qualityState: params.get('qualityState') ?? '',
    literatureYearFrom: params.get('yearFrom') ?? '',
    literatureYearTo: params.get('yearTo') ?? '',
    compoundFamily: params.get('compoundFamily') ?? 'all',
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
  const cid = compound.pubchem?.matchStatus === 'verified' ? compound.pubchem.cid : null;
  const smiles = compound.pubchem?.smiles ?? compound.isomericSmiles ?? compound.canonicalSmiles;
  const localSource = smiles ? `/database-data/structures-2d/${compound.id}.svg` : null;
  const remoteSource = cid ? `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/PNG?record_type=2d&image_size=${small ? 140 : 500}x${small ? 140 : 500}` : null;
  const [source, setSource] = useState(localSource ?? remoteSource);
  useEffect(() => setSource(localSource ?? remoteSource), [localSource, remoteSource]);
  if (!source) return <div className={`sdb-structure-empty ${small ? 'small' : ''}`}><FlaskConical /></div>;
  return <img className={`sdb-structure ${small ? 'small' : ''}`} src={source} alt={`${compound.name} verified structure`} onError={() => setSource(source === localSource ? remoteSource : null)} />;
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

const CompoundLandscape = ({ onSelect }: { onSelect: (id: string) => void }) => {
  const [mode, setMode] = useState<'2d' | '3d'>('2d');
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
      <div className="sdb-landscape-heading"><h2 className="sdb-landscape-title">ECFP4 Molecular Similarity Landscape</h2><div className="sdb-space-mode" role="group" aria-label="Map dimension"><button type="button" className={mode === '2d' ? 'active' : ''} aria-pressed={mode === '2d'} onClick={() => setMode('2d')}>2D</button><button type="button" className={mode === '3d' ? 'active' : ''} aria-pressed={mode === '3d'} onClick={() => setMode('3d')}>3D</button></div></div>
      <div className="sdb-landscape-canvas">
        {mode === '3d' ? <Suspense fallback={<div className="sdb-space-3d-state" role="status">Loading 3D molecular space...</div>}><ChemicalSpace3D onSelect={onSelect} /></Suspense> : <div className="sdb-space-stage">
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
        </div>}
        <div className="sdb-space-footer">
          <div className="sdb-legend">{CHEMICAL_SPACE.metadata.clusters.map((cluster) => <span key={cluster.id}><i className={`cluster-${cluster.id.toLowerCase()}`} /><b>{cluster.id}</b> {cluster.size.toLocaleString()} molecules</span>)}</div>
          <p><span>{CHEMICAL_SPACE.metadata.mappedRecordCount.toLocaleString()} molecules mapped</span><span>ECFP4 · Tanimoto distance · k-medoids · UMAP</span></p>
          <small>Each point represents one molecule. Nearby points have similar ECFP4 fingerprints; colors represent deterministic fingerprint-space clusters.</small>
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

const Overview = ({ onSelect, onSearch }: {
  onSelect: (id: string) => void;
  onSearch: (query: string) => void;
}) => {
  const [query, setQuery] = useState('');
  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    onSearch(query.trim());
  };
  return <div className="sdb-home">
    <section className="sdb-hero">
      <div className="sdb-hero-inner">
        <div className="sdb-hero-copy">
          <h1>SweetMeta</h1>
          <p>Explore traceable identities, evidence readiness, and verified chemical properties across the evolving landscape of sweet entities.</p>
          <form className="sdb-hero-search" onSubmit={submitSearch}>
            <label className="sdb-search-input"><Search size={20} /><input aria-label="Search SweetMeta" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, stable ID, formula, InChIKey, or PubChem CID" /></label>
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
      <section className="sdb-release-summary" aria-labelledby="release-summary-heading">
        <h2 className="sdb-release-summary-heading" id="release-summary-heading">SweetMeta Database Composition</h2>
        <div className="sdb-release-cards">
          <article><span className="sdb-release-icon"><FlaskConical /></span><div><h3>Sweet molecules</h3><strong>{DATABASE_METADATA.totalRecords.toLocaleString()}</strong><p>Curated molecular records</p></div></article>
          <article><span className="sdb-release-icon"><ShieldCheck /></span><div><h3>Verified structures</h3><strong>{DATABASE_METADATA.pubchemVerified.toLocaleString()}</strong><p>Exact-key validated structures</p></div></article>
          <article><span className="sdb-release-icon"><BookOpen /></span><div><h3>Literature-linked molecules</h3><strong>{LITERATURE_SUMMARY.linkedCompoundCount.toLocaleString()}</strong><p>Molecules linked to curated publications</p></div></article>
          <article><span className="sdb-release-icon"><Library /></span><div><h3>Indexed publications</h3><strong>{LITERATURE_SUMMARY.indexedPaperCount.toLocaleString()}</strong><p>Publications in the SweetSeek corpus</p></div></article>
        </div>
      </section>
      <CompoundLandscape onSelect={onSelect} />
    </div>
  </div>;
};

const CompoundIndex = ({ onSelect, initialQuery, initialTier, initialDrilldown }: { onSelect: (id: string) => void; initialQuery: string; initialTier: string; initialDrilldown: { domain: string; foodGroup: string; sweetnessMinLog10: string; sweetnessMaxLog10: string; qualityMetric: string; qualityState: string } }) => {
  const [query, setQuery] = useState(initialQuery);
  const [tier, setTier] = useState(initialTier);
  const [review, setReview] = useState('all');
  const [pubchem, setPubchem] = useState('all');
  const [page, setPage] = useState(1);
  const [drilldown, setDrilldown] = useState(initialDrilldown);
  const pageSize = 25;
  const [remote, setRemote] = useState<{ items: DatabaseCompound[]; total: number; pageCount: number } | null>(null);
  const [remoteError, setRemoteError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    fetchSweetMetaCompounds({
      query, page, pageSize, tier, review,
      domain: drilldown.domain,
      foodGroup: drilldown.foodGroup,
      sweetnessMinLog10: drilldown.sweetnessMinLog10 === '' ? undefined : Number(drilldown.sweetnessMinLog10),
      sweetnessMaxLog10: drilldown.sweetnessMaxLog10 === '' ? undefined : Number(drilldown.sweetnessMaxLog10),
      qualityMetric: drilldown.qualityMetric,
      qualityState: drilldown.qualityState,
    })
      .then((payload) => {
        if (!active) return;
        setRemote({
          items: payload.items.map((item) => ({
            id: item.id,
            entityType: 'small-molecule',
            name: item.name ?? item.id,
            nameSource: null,
            inchiKey: item.inchiKey ?? null,
            canonicalTautomerInchiKey: null,
            isomericSmiles: item.isomericSmiles ?? null,
            canonicalSmiles: item.canonicalSmiles ?? null,
            formula: item.formula ?? null,
            molecularWeight: item.molecularWeight ?? null,
            formalCharge: item.formalCharge ?? null,
            heavyAtomCount: item.heavyAtomCount ?? null,
            createdAt: null,
            evidence: { baselineTier: null, releaseTier: item.releaseTier, baselineGap: null, releaseGap: item.releaseGap, priorityScore: null, acceptedAssertions: 0 },
            review: { required: item.reviewRequired === 1, identityStatus: null, note: null },
            pubchem: null,
            chembl: null,
          })),
          total: payload.total,
          pageCount: payload.pageCount,
        });
        setRemoteError(null);
      })
      .catch((error: unknown) => {
        if (active) setRemoteError(error instanceof Error ? error.message : 'SweetMeta API unavailable');
      });
    return () => { active = false; };
  }, [drilldown, page, pageSize, query, review, tier]);
  const filtered = useMemo(() => {
    if (remote) return remote.items;
    const q = query.trim().toLocaleLowerCase();
    return DATABASE_COMPOUNDS.filter((compound) => {
      const searchable = [compound.id, compound.name, compound.inchiKey, compound.formula, compound.pubchem?.cid, compound.pubchem?.iupacName].filter(Boolean).join(' ').toLocaleLowerCase();
      return (!q || searchable.includes(q))
        && (tier === 'all' || tierCode(compound.evidence.releaseTier) === tier)
        && (review === 'all' || (review === 'required') === compound.review.required)
        && (pubchem === 'all' || (pubchem === 'matched') === Boolean(compound.pubchem));
    });
  }, [pubchem, query, remote, review, tier]);
  const pageCount = remote?.pageCount ?? Math.max(1, Math.ceil(filtered.length / pageSize));
  const visible = remote ? filtered : filtered.slice((page - 1) * pageSize, page * pageSize);
  return (
    <div className="sdb-page">
      <header className="sdb-page-heading compact"><div><span className="sdb-kicker">Compound index</span><h1>Browse the current release</h1><p>Search stable IDs, preferred names, formulae, InChIKeys, or verified PubChem identifiers.</p></div></header>
      <div className="sdb-filterbar">
        <label className="sdb-search"><Search size={18} /><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Search compounds" aria-label="Search compounds" />{query && <button title="Clear search" onClick={() => { setQuery(''); setPage(1); }}><X size={16} /></button>}</label>
        <label className="sdb-flat-select"><Filter size={16} /><select aria-label="Evidence tier" value={tier} onChange={(event) => { setTier(event.target.value); setPage(1); }}><option value="all">All evidence tiers</option>{Object.keys(TIER_INFO).map((item) => <option value={item} key={item}>{item}</option>)}</select><ChevronDown className="sdb-select-chevron" aria-hidden="true" /></label>
        <label className="sdb-flat-select"><select aria-label="Review status" value={review} onChange={(event) => { setReview(event.target.value); setPage(1); }}><option value="all">All review states</option><option value="required">Manual review</option><option value="released">Released</option></select><ChevronDown className="sdb-select-chevron" aria-hidden="true" /></label>
        <label className="sdb-flat-select"><select aria-label="PubChem status" value={pubchem} onChange={(event) => { setPubchem(event.target.value); setPage(1); }}><option value="all">All PubChem states</option><option value="matched">PubChem matched</option><option value="unmatched">Not matched</option></select><ChevronDown className="sdb-select-chevron" aria-hidden="true" /></label>
      </div>
      {Object.values(drilldown).some(Boolean) && <div className="sdb-drilldown-banner" role="status"><span>Statistics filter: {[drilldown.domain, drilldown.foodGroup, drilldown.qualityMetric, drilldown.qualityState].filter(Boolean).map(readable).join(' · ') || 'Relative sweetness range'}</span><button onClick={() => { setDrilldown({ domain: '', foodGroup: '', sweetnessMinLog10: '', sweetnessMaxLog10: '', qualityMetric: '', qualityState: '' }); setPage(1); }}>Clear filter</button></div>}
      <div className="sdb-result-meta"><strong>{(remote?.total ?? filtered.length).toLocaleString()}</strong> records <span>Source: {remote ? 'SweetMeta SQLite API' : DATABASE_METADATA.sourceWorkbook}</span></div>
      {remoteError && <div className="sdb-inline-notice" role="status">Live SQLite API unavailable; showing the bundled release snapshot.</div>}
      <div className="sdb-table-wrap"><table className="sdb-table"><thead><tr><th>Compound</th><th>Formula</th><th>MW</th><th>Evidence</th><th>Assertions</th><th>Status</th><th>PubChem</th></tr></thead><tbody>{visible.map((compound) => <tr key={compound.id} onClick={() => onSelect(compound.id)}><td><div className="sdb-compound-cell"><MoleculeImage compound={compound} small /><span><strong>{compound.name}</strong><small>{compound.id}</small></span></div></td><td className="sdb-mono">{compound.formula ?? 'Not available'}</td><td>{formatNumber(compound.molecularWeight)}</td><td><TierBadge tier={compound.evidence.releaseTier} /></td><td>{compound.evidence.acceptedAssertions}</td><td><ReviewBadge compound={compound} /></td><td>{compound.pubchem?.cid ? <span className="sdb-pubchem-cell"><a href={compound.pubchem.sourceUrl ?? '#'} onClick={(event) => event.stopPropagation()} target="_blank" rel="noreferrer">CID {compound.pubchem.cid}<ExternalLink size={13} /></a>{compound.pubchem.matchStatus !== 'verified' && <span className="sdb-discrepancy"><AlertTriangle size={12} /> Discrepancy</span>}</span> : <span className="sdb-muted">Not matched</span>}</td></tr>)}</tbody></table></div>
      {!visible.length && <EmptyState icon={Search} title="No matching compounds">Adjust the search term or clear one of the filters.</EmptyState>}
      <div className="sdb-pagination"><button disabled={page === 1} onClick={() => setPage((value) => value - 1)}><ChevronLeft size={17} /> Previous</button><span>Page {page} of {pageCount}</span><button disabled={page === pageCount} onClick={() => setPage((value) => value + 1)}>Next <ChevronRight size={17} /></button></div>
    </div>
  );
};

const useLiteratureData = () => {
  const [data, setData] = useState<LiteratureData | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    loadLiteratureData().then((payload) => { if (active) setData(payload); }).catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : 'Literature data could not be loaded.'); });
    return () => { active = false; };
  }, []);
  return { data, error };
};

const LiteratureLinks = ({ links, data, onSelect }: { links: CompoundPaperLink[]; data: LiteratureData; onSelect: (id: string) => void }) => {
  const [expanded, setExpanded] = useState<string | null>(null);
  return <div className="sdb-literature-list">
    {links.map((link) => {
      const paper = data.papers[link.paperId];
      const compound = DATABASE_COMPOUNDS.find((item) => item.id === link.compoundId);
      if (!paper || !compound) return null;
      const open = expanded === link.linkId;
      return <article className={open ? 'open' : ''} key={link.linkId}>
        <div className="sdb-literature-row">
          <button className="sdb-lit-expand" onClick={() => setExpanded(open ? null : link.linkId)} aria-expanded={open} title={open ? 'Hide evidence' : 'Show evidence'}><ChevronDown size={17} /></button>
          <button className="sdb-lit-compound" onClick={() => onSelect(compound.id)}><strong>{compound.name}</strong><small>{compound.id}</small></button>
          <span className={`sdb-relation relation-${link.relationshipType}`}>{RELATIONSHIP_LABELS[link.relationshipType]}</span>
          <div className="sdb-lit-citation"><strong>{paper.title}</strong><small>{[paper.journal, paper.year].filter(Boolean).join(' · ') || 'Publication details unavailable'}</small></div>
          <div className="sdb-lit-identifiers">{paper.doi ? <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer">DOI <ExternalLink size={12} /></a> : <span>DOI unavailable</span>}{paper.pmid ? <a href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/`} target="_blank" rel="noreferrer">PMID {paper.pmid} <ExternalLink size={12} /></a> : <span>PMID unavailable</span>}</div>
        </div>
        {open && <div className="sdb-lit-evidence"><div><span>Why linked</span><strong>{RELATIONSHIP_LABELS[link.relationshipType]} via {link.matchMethod.replaceAll('_', ' ')}</strong></div><blockquote>{link.evidenceExcerpt || 'Evidence excerpt unavailable.'}</blockquote><dl><div><dt>PDF page</dt><dd>{link.pageNumber ?? 'Title record'}</dd></div><div><dt>Matched term</dt><dd>{link.matchedAlias}</dd></div><div><dt>Confidence</dt><dd>{Math.round(link.confidence * 100)}%</dd></div><div><dt>Review status</dt><dd>Auto high confidence</dd></div></dl></div>}
      </article>;
    })}
  </div>;
};

type LiteratureSort = 'compound' | 'family' | 'title' | 'journal' | 'year' | 'pmid' | 'doi';

const LiteratureTable = ({ links, data, onSelect, sort, sortDirection, onSort }: { links: CompoundPaperLink[]; data: LiteratureData; onSelect: (id: string) => void; sort: LiteratureSort; sortDirection: 'asc' | 'desc'; onSort: (sort: LiteratureSort) => void }) => (
  <div className="sdb-literature-table-wrap">
    <table className="sdb-literature-table">
      <thead><tr>
        {([['compound', 'Compound'], ['family', 'Family'], ['title', 'Article Title'], ['journal', 'Journal'], ['year', 'Year'], ['pmid', 'PubMed ID'], ['doi', 'DOI']] as const).map(([value, label]) => <th key={value} aria-sort={sort === value ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}><button type="button" className={sort === value ? 'active' : ''} onClick={() => onSort(value)}><span>{label}</span><ArrowUpDown size={13} /></button></th>)}
      </tr></thead>
      <tbody>{links.map((link) => {
        const paper = data.papers[link.paperId];
        const compound = DATABASE_COMPOUNDS.find((item) => item.id === link.compoundId);
        if (!paper || !compound) return null;
        return <tr key={link.linkId}>
          <td><button className="sdb-lit-table-compound" onClick={() => onSelect(compound.id)}>{compound.name}</button></td>
          <td>{paper.family ?? <span className="sdb-lit-not-curated">Not curated</span>}</td>
          <td className="sdb-lit-table-title">{paper.title}</td>
          <td>{paper.journal ?? <span className="sdb-muted">Not available</span>}</td>
          <td>{paper.year ?? <span className="sdb-muted">—</span>}</td>
          <td>{paper.pmid ? <a href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/`} target="_blank" rel="noreferrer">{paper.pmid} <ExternalLink size={12} /></a> : <span className="sdb-muted">Not available</span>}</td>
          <td>{paper.doi ? <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer">{paper.doi} <ExternalLink size={12} /></a> : <span className="sdb-muted">Not available</span>}</td>
        </tr>;
      })}</tbody>
    </table>
  </div>
);

const COMPOUND_FAMILIES = ['analytical-methods', 'chlorinated-sucrose', 'high-intensity-natural', 'high-intensity-synthetic', 'natural-sweeteners', 'nutrition-metabolism', 'other-uncertain', 'receptor-mechanism', 'reviews-general', 'safety-toxicology', 'sensory-methods', 'sugars-polyols', 'sweet-proteins-peptides', 'taste-modifiers-synergy'];

const SqliteLiterature = ({ rows, total, page, pageCount, queryInput, recentYears, compoundFamily, yearRange, onQueryInput, onSearch, onRecentYears, onCompoundFamily, onClearYearRange, onPage }: { rows: SweetMetaLiteratureRecord[]; total: number; page: number; pageCount: number; queryInput: string; recentYears: number; compoundFamily: string; yearRange?: { from: string; to: string }; onQueryInput: (value: string) => void; onSearch: () => void; onRecentYears: (value: number) => void; onCompoundFamily: (value: string) => void; onClearYearRange?: () => void; onPage: (value: number) => void }) => <div className="sdb-page sdb-literature-page">
  <header className="sdb-page-heading sdb-literature-heading compact"><div><h1>Literature evidence</h1><p>Search 1,735 SweetMeta literature records. Compound links are shown only after review and acceptance.</p></div></header>
  <div className="sdb-lit-toolbar">
    <form className="sdb-search sdb-lit-search" onSubmit={(event) => { event.preventDefault(); onSearch(); }}><Search size={18} /><input value={queryInput} onChange={(event) => onQueryInput(event.target.value)} placeholder="Title, author, journal, PubMed ID, or DOI" aria-label="Search SQLite literature" /><button type="submit">Search</button></form>
    <div className="sdb-lit-filter-group" aria-label="Literature filters">
      <label className="sdb-year-range"><span><Filter size={15} />Recent years</span><div className="sdb-year-slider"><input type="range" min="0" max="20" step="5" value={recentYears} onChange={(event) => onRecentYears(Number(event.target.value))} aria-label="Recent publication years" /><div className="sdb-year-marks" aria-hidden="true"><span>All</span><span>5</span><span>10</span><span>15</span><span>20</span></div></div><strong>{recentYears === 0 ? 'All years' : `Last ${recentYears} years`}</strong></label>
      <label className="sdb-family-filter"><span>Compound family</span><div><select aria-label="compound_family" value={compoundFamily} onChange={(event) => onCompoundFamily(event.target.value)}><option value="all">All families</option>{COMPOUND_FAMILIES.map((value) => <option key={value} value={value}>{readable(value)}</option>)}</select><ChevronDown aria-hidden="true" /></div></label>
    </div>
  </div>
  {yearRange?.from && <div className="sdb-drilldown-banner" role="status"><span>Publication interval: {yearRange.from}-{yearRange.to || 'present'}</span><button onClick={onClearYearRange}>Clear interval</button></div>}
  <div className="sdb-result-meta"><strong>{total.toLocaleString()}</strong> literature records</div>
  <div className="sdb-table-wrap"><table className="sdb-table sdb-literature-registry"><thead><tr><th>ID</th><th>Article title</th><th>Journal</th><th>Year</th><th>compound_family</th><th>PubMed ID</th><th>DOI</th></tr></thead><tbody>{rows.map((row) => <tr key={row.record_id}><td><span className="sdb-record-id">{row.record_id}</span></td><td><strong>{row.title}</strong>{Boolean(row.reviewed_link_count) && <span className="sdb-reviewed-tag">Reviewed</span>}</td><td>{row.journal ?? 'Not available'}</td><td>{row.year ?? 'Not available'}</td><td><span className="sdb-family-tag">{readable(row.compound_family ?? 'other-uncertain')}</span></td><td>{row.pmid ? <a href={`https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(row.pmid)}/`} target="_blank" rel="noreferrer">{row.pmid} <ExternalLink size={13} /></a> : 'Not available'}</td><td>{row.doi ? <a className="sdb-doi-link" href={`https://doi.org/${encodeURIComponent(row.doi)}`} target="_blank" rel="noreferrer">{row.doi} <ExternalLink size={13} /></a> : 'Not available'}</td></tr>)}</tbody></table></div>
  {!rows.length && <EmptyState icon={Search} title="No matching literature">Adjust the search term or year filter.</EmptyState>}
  <div className="sdb-pagination"><button disabled={page === 1} onClick={() => onPage(page - 1)}><ChevronLeft size={17} /> Previous</button><span>Page {page} of {pageCount}</span><button disabled={page >= pageCount} onClick={() => onPage(page + 1)}>Next <ChevronRight size={17} /></button></div>
</div>;

const Literature = ({ onSelect, initialYearFrom = '', initialYearTo = '', initialCompoundFamily = 'all' }: { onSelect: (id: string) => void; initialYearFrom?: string; initialYearTo?: string; initialCompoundFamily?: string }) => {
  const { data, error } = useLiteratureData();
  const [sqliteRows, setSqliteRows] = useState<SweetMetaLiteratureRecord[] | null>(null);
  const [sqlitePage, setSqlitePage] = useState(1);
  const [sqlitePageCount, setSqlitePageCount] = useState(1);
  const [sqliteTotal, setSqliteTotal] = useState(0);
  const [sqliteQuery, setSqliteQuery] = useState('');
  const [sqliteQueryInput, setSqliteQueryInput] = useState('');
  const [sqliteRecentYears, setSqliteRecentYears] = useState(0);
  const [sqliteCompoundFamily, setSqliteCompoundFamily] = useState(initialCompoundFamily);
  const [sqliteYearRange, setSqliteYearRange] = useState({ from: initialYearFrom, to: initialYearTo });
  useEffect(() => {
    let active = true;
    const currentYear = new Date().getFullYear();
    const yearFrom = sqliteYearRange.from ? Number(sqliteYearRange.from) : sqliteRecentYears ? currentYear - sqliteRecentYears + 1 : undefined;
    const yearTo = sqliteYearRange.to ? Number(sqliteYearRange.to) : undefined;
    fetchSweetMetaLiterature({ query: sqliteQuery, yearFrom, yearTo, compoundFamily: sqliteCompoundFamily, page: sqlitePage, pageSize: 25 }).then((payload) => {
      if (!active) return;
      setSqliteRows(payload.items); setSqlitePageCount(payload.pageCount); setSqliteTotal(payload.total);
    }).catch(() => { if (active) setSqliteRows(null); });
    return () => { active = false; };
  }, [sqlitePage, sqliteQuery, sqliteRecentYears, sqliteCompoundFamily, sqliteYearRange]);
  const [query, setQuery] = useState('');
  const [relationship, setRelationship] = useState('all');
  const [year, setYear] = useState('all');
  const [status, setStatus] = useState('all');
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<LiteratureSort>('compound');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const pageSize = 25;
  const rows = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLocaleLowerCase();
    const filtered = data.links.filter((link) => {
      const paper = data.papers[link.paperId];
      const compound = DATABASE_COMPOUNDS.find((item) => item.id === link.compoundId);
      const searchable = [compound?.name, compound?.id, paper?.family, paper?.title, paper?.journal, paper?.doi, paper?.pmid].filter(Boolean).join(' ').toLocaleLowerCase();
      return (!q || searchable.includes(q))
        && (relationship === 'all' || link.relationshipType === relationship)
        && (year === 'all' || String(paper?.year) === year)
        && (status === 'all' || link.reviewStatus === status);
    });
    const value = (link: CompoundPaperLink) => {
      const paper = data.papers[link.paperId];
      const compound = DATABASE_COMPOUNDS.find((item) => item.id === link.compoundId);
      return String(sort === 'compound' ? compound?.name ?? '' : sort === 'family' ? paper?.family ?? '' : paper?.[sort] ?? '');
    };
    return filtered.sort((a, b) => value(a).localeCompare(value(b), undefined, { numeric: true }) * (sortDirection === 'asc' ? 1 : -1));
  }, [data, query, relationship, sort, sortDirection, status, year]);
  const changeSort = (next: LiteratureSort) => {
    if (sort === next) setSortDirection((value) => value === 'asc' ? 'desc' : 'asc');
    else { setSort(next); setSortDirection('asc'); }
    setPage(1);
  };
  const years = useMemo(() => data ? [...new Set(Object.values(data.papers).flatMap((paper) => paper.year ? [paper.year] : []))].sort((a, b) => b - a) : [], [data]);
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  const visible = rows.slice((page - 1) * pageSize, page * pageSize);
  if (sqliteRows) return <SqliteLiterature rows={sqliteRows} total={sqliteTotal} page={sqlitePage} pageCount={sqlitePageCount} queryInput={sqliteQueryInput} recentYears={sqliteRecentYears} compoundFamily={sqliteCompoundFamily} yearRange={sqliteYearRange} onQueryInput={setSqliteQueryInput} onSearch={() => { setSqliteQuery(sqliteQueryInput.trim()); setSqlitePage(1); }} onRecentYears={(value) => { setSqliteRecentYears(value); setSqliteYearRange({ from: '', to: '' }); setSqlitePage(1); }} onCompoundFamily={(value) => { setSqliteCompoundFamily(value); setSqlitePage(1); }} onClearYearRange={() => { setSqliteYearRange({ from: '', to: '' }); setSqlitePage(1); }} onPage={setSqlitePage} />;
  if (error) return <div className="sdb-page"><EmptyState icon={FileWarning} title="Literature data could not be loaded">{error}</EmptyState></div>;
  if (!data) return <div className="sdb-page"><EmptyState icon={BookOpen} title="Loading literature registry">Reading the compound-paper evidence index.</EmptyState></div>;
  return <div className="sdb-page sdb-literature-page">
    <header className="sdb-page-heading compact"><div><span className="sdb-kicker">Literature registry</span><h1>Compound-linked literature</h1><p>High-confidence links from the local SweetSeek corpus. Background-only candidates remain outside the public count until manual review.</p></div></header>
    <div className="sdb-metrics sdb-lit-metrics"><div><span>Linked papers</span><strong>{data.metadata.linkedPaperCount.toLocaleString()}</strong><small>of {data.metadata.sourcePaperCount.toLocaleString()} indexed</small></div><div><span>Covered compounds</span><strong>{data.metadata.linkedCompoundCount.toLocaleString()}</strong><small>high-confidence public links</small></div><div><span>DOI / PMID</span><strong>{data.metadata.doiCount} / {data.metadata.pmidCount}</strong><small>exact identifiers</small></div><div><span>Review queue</span><strong>{data.metadata.reviewCandidateCount.toLocaleString()}</strong><small>not public</small></div></div>
    <div className="sdb-filterbar sdb-lit-filters">
      <label className="sdb-search"><Search size={18} /><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Compound, title, DOI, PMID, journal" aria-label="Search literature" />{query && <button title="Clear search" onClick={() => { setQuery(''); setPage(1); }}><X size={16} /></button>}</label>
      <label><Filter size={16} /><select aria-label="Relationship" value={relationship} onChange={(event) => { setRelationship(event.target.value); setPage(1); }}><option value="all">All relationships</option>{Object.entries(RELATIONSHIP_LABELS).filter(([value]) => value !== 'background_mention').map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label><select aria-label="Publication year" value={year} onChange={(event) => { setYear(event.target.value); setPage(1); }}><option value="all">All years</option>{years.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
      <label><select aria-label="Evidence status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="all">All evidence states</option><option value="auto_high_confidence">Auto high confidence</option></select></label>
    </div>
    <div className="sdb-result-meta"><strong>{rows.length.toLocaleString()}</strong> public compound-paper links <span>{data.metadata.publicLinkCount.toLocaleString()} in this release</span></div>
    {visible.length ? <LiteratureTable links={visible} data={data} onSelect={onSelect} sort={sort} sortDirection={sortDirection} onSort={changeSort} /> : <EmptyState icon={Search} title="No matching literature">Adjust the search term or clear one of the filters.</EmptyState>}
    <div className="sdb-pagination"><button disabled={page === 1} onClick={() => setPage((value) => value - 1)}><ChevronLeft size={17} /> Previous</button><span>Page {Math.min(page, pageCount)} of {pageCount}</span><button disabled={page >= pageCount} onClick={() => setPage((value) => value + 1)}>Next <ChevronRight size={17} /></button></div>
  </div>;
};

const CompoundLiterature = ({ compound, onSelect }: { compound: DatabaseCompound; onSelect: (id: string) => void }) => {
  const { data, error } = useLiteratureData();
  const [tab, setTab] = useState<'core' | 'comparators' | 'synthesis' | 'background'>('core');
  if (error) return <EmptyState icon={FileWarning} title="Literature data could not be loaded">{error}</EmptyState>;
  if (!data) return <EmptyState icon={BookOpen} title="Loading linked literature">Reading traceable paper-level evidence.</EmptyState>;
  const compoundLinks = data.links.filter((link) => link.compoundId === compound.id);
  const groups: Record<typeof tab, LiteratureRelationship[]> = {
    core: ['primary_subject', 'tested_sweetener', 'receptor_ligand'],
    comparators: ['comparator_control'],
    synthesis: ['synthesis_production'],
    background: ['background_mention'],
  };
  const counts = Object.fromEntries(Object.entries(groups).map(([key, relationships]) => [key, compoundLinks.filter((link) => relationships.includes(link.relationshipType)).length]));
  const visible = compoundLinks.filter((link) => groups[tab].includes(link.relationshipType));
  return <div className="sdb-compound-literature">
    <div className="sdb-lit-tabs" role="tablist" aria-label="Literature evidence groups">
      {([['core', 'Core evidence'], ['comparators', 'Comparators'], ['synthesis', 'Synthesis & production'], ['background', 'Background mentions']] as const).map(([value, label]) => <button role="tab" aria-selected={tab === value} className={tab === value ? 'active' : ''} key={value} onClick={() => setTab(value)}>{label}<span>{counts[value]}</span></button>)}
    </div>
    {visible.length ? <LiteratureLinks links={visible} data={data} onSelect={onSelect} /> : <EmptyState icon={BookOpen} title="No accepted links in this category">{tab === 'background' ? 'Background-only mentions are held in the manual review queue and are not published as formal evidence.' : 'No high-confidence local paper association has been accepted for this category.'}</EmptyState>}
  </div>;
};

const Downloads = () => <div className="sdb-page"><header className="sdb-page-heading compact"><div><span className="sdb-kicker">Data access</span><h1>Downloads</h1><p>Release metadata is visible, while public file downloads are currently disabled by policy.</p></div></header><div className="sdb-download-list"><article><Database /><span><strong>Source workbook</strong><small>{DATABASE_METADATA.sourceWorkbook} · {DATABASE_METADATA.totalRecords} records</small></span><button disabled><LockKeyhole size={15} /> Restricted</button></article><article><FileWarning /><span><strong>Data quality report</strong><small>Missing fields, review queue, and enrichment coverage</small></span><button disabled><LockKeyhole size={15} /> Restricted</button></article><article><Download /><span><strong>Filtered compound export</strong><small>CSV export for current search results</small></span><button disabled><LockKeyhole size={15} /> Restricted</button></article></div><div className="sdb-policy-note"><LockKeyhole /><div><strong>Download access is not enabled</strong><p>This state is intentional and can be changed later without altering the database schema or compound portal.</p></div></div></div>;

const Detail = ({ compound, onBack, onSelect, sqliteDetail, detailError }: { compound: DatabaseCompound; onBack: () => void; onSelect: (id: string) => void; sqliteDetail: SweetMetaCompoundDetail | null; detailError: string | null }) => {
  const [structureMode, setStructureMode] = useState<'2d' | '3d'>('2d');
  const [activeSection, setActiveSection] = useState<DetailSection>('overview');
  const neighbors = (CHEMICAL_SPACE.neighbors?.[compound.id] ?? []).flatMap((neighbor) => {
    const match = DATABASE_COMPOUNDS.find((item) => item.id === neighbor.id);
    return match ? [{ compound: match, similarity: neighbor.similarity }] : [];
  });
  const viewerCid = compound.pubchem?.matchStatus === 'verified' ? compound.pubchem.cid : null;
  const viewerSmiles = compound.pubchem?.smiles ?? compound.isomericSmiles ?? compound.canonicalSmiles;
  useEffect(() => {
    if (viewerCid && viewerSmiles) preloadMolecule3D(viewerCid, viewerSmiles);
  }, [viewerCid, viewerSmiles]);
  useEffect(() => setActiveSection('overview'), [compound.id]);

  const renderSection = () => {
    switch (activeSection) {
      case 'sweetness':
        return <section className="sdb-data-section sdb-record-section"><div className="sdb-section-title"><div><span>Relative Sweetness</span><h2>Quantitative sweetness</h2></div></div>{sqliteDetail?.evidence.measurements.length ? <div className="sdb-detail-grid">{sqliteDetail.evidence.measurements.map((measurement, index) => <dl className="sdb-definition-list" key={String(measurement.measurement_id ?? index)}><div><dt>Relative sweetness</dt><dd>{String(measurement.relative_sweetness ?? 'Not available')}</dd></div><div><dt>Reference</dt><dd>{String(measurement.reference_compound ?? 'Not available')}</dd></div><div><dt>Reference concentration</dt><dd>{String(measurement.reference_concentration ?? 'Not available')}</dd></div><div><dt>Status</dt><dd>{readable(String(measurement.measurement_status ?? ''))}</dd></div><div><dt>Evidence reference</dt><dd>{String(measurement.evidence_reference ?? 'Not available')}</dd></div></dl>)}</div> : <EmptyState icon={CircleHelp} title="Relative sweetness is not available">No reviewed quantitative sweetness measurement is linked to this record in the current SQLite release.</EmptyState>}</section>;
      case 'structure':
        return <section className="sdb-data-section sdb-record-section"><div className="sdb-section-title"><div><span>Structure &amp; Identifiers</span><h2>Chemical representation</h2></div></div><dl className="sdb-code-list"><div><dt>Isomeric SMILES</dt><dd>{compound.isomericSmiles ?? 'Not available'}</dd></div><div><dt>Canonical SMILES</dt><dd>{compound.canonicalSmiles ?? 'Not available'}</dd></div><div><dt>Canonical tautomer InChIKey</dt><dd>{compound.canonicalTautomerInchiKey ?? 'Not available'}</dd></div></dl></section>;
      case 'properties':
        return <section className="sdb-data-section sdb-record-section"><div className="sdb-section-title"><div><span>Physicochemical Properties</span><h2>Source and PubChem values</h2><p>External values remain separate and require an exact InChIKey match.</p></div>{compound.pubchem?.sourceUrl && <a href={compound.pubchem.sourceUrl} target="_blank" rel="noreferrer">Open PubChem <ExternalLink size={15} /></a>}</div><dl className="sdb-property-grid"><div><dt>Formal charge</dt><dd>{formatNumber(compound.formalCharge, 0)}</dd></div><div><dt>Heavy atom count</dt><dd>{formatNumber(compound.heavyAtomCount, 0)}</dd></div><div><dt>XLogP</dt><dd>{formatNumber(compound.pubchem?.xlogp ?? null)}</dd></div><div><dt>TPSA</dt><dd>{compound.pubchem?.tpsa === null || compound.pubchem?.tpsa === undefined ? 'Not available' : `${formatNumber(compound.pubchem.tpsa)} Å²`}</dd></div><div><dt>H-bond donors</dt><dd>{formatNumber(compound.pubchem?.hBondDonorCount ?? null, 0)}</dd></div><div><dt>H-bond acceptors</dt><dd>{formatNumber(compound.pubchem?.hBondAcceptorCount ?? null, 0)}</dd></div><div><dt>Rotatable bonds</dt><dd>{formatNumber(compound.pubchem?.rotatableBondCount ?? null, 0)}</dd></div><div className="wide"><dt>IUPAC name</dt><dd>{compound.pubchem?.iupacName ?? 'Not available'}</dd></div></dl></section>;
      case 'similar':
        return <section className="sdb-data-section sdb-record-section"><div className="sdb-section-title"><div><span>Similar Compounds</span><h2>ECFP4 structural neighbors</h2><p>Tanimoto similarity calculated from 2,048-bit radius-2 Morgan fingerprints.</p></div></div>{neighbors.length ? <div className="sdb-similar-grid">{neighbors.map((item) => <button key={item.compound.id} onClick={() => onSelect(item.compound.id)}><MoleculeImage compound={item.compound} small /><span><strong>{item.compound.name}</strong><small>{item.compound.formula ?? 'Formula not available'}</small></span><b>{Math.round(item.similarity * 100)}%</b></button>)}</div> : <EmptyState icon={Beaker} title="Similar compounds are not available">A valid structure fingerprint is required to calculate molecular neighbors.</EmptyState>}</section>;
      case 'literature-evidence':
        return <section className="sdb-data-section sdb-record-section"><div className="sdb-section-title"><div><span>Literature &amp; Evidence</span><h2>Traceable supporting records</h2><p>SQLite evidence is shown first; the bundled relationship index remains available as a fallback.</p></div></div>{sqliteDetail?.evidence.tasteAssertions.length ? <div className="sdb-detail-grid">{sqliteDetail.evidence.tasteAssertions.map((assertion, index) => <dl className="sdb-definition-list" key={String(assertion.assertion_id ?? index)}><div><dt>Taste</dt><dd>{String(assertion.normalized_taste ?? 'Not available')}</dd></div><div><dt>Polarity</dt><dd>{String(assertion.assertion_polarity ?? 'Not available')}</dd></div><div><dt>Status</dt><dd>{String(assertion.assertion_status ?? 'Not available')}</dd></div><div><dt>Source evidence</dt><dd>{String(assertion.evidence_reference ?? 'Not available')}</dd></div></dl>)}</div> : null}{sqliteDetail?.literatureReview?.reviewRequiredCount ? <div className="sdb-inline-notice" role="status">Additional candidate literature links are pending review ({sqliteDetail.literatureReview.reviewRequiredCount}).</div> : null}{sqliteDetail?.literature.length ? <div className="sdb-literature-list">{sqliteDetail.literature.slice(0, 8).map((paper) => <article key={paper.record_id}><div className="sdb-literature-row"><div className="sdb-lit-citation"><strong>{paper.title}</strong><small>{[paper.relation_type, paper.journal, paper.year].filter(Boolean).join(' · ') || 'Publication details unavailable'}</small>{paper.evidence_excerpt && <small>{paper.evidence_excerpt}</small>}</div>{paper.pmid && <a href={`https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(paper.pmid)}/`} target="_blank" rel="noreferrer">PMID {paper.pmid} <ExternalLink size={13} /></a>}{paper.doi && <a href={`https://doi.org/${encodeURIComponent(paper.doi)}`} target="_blank" rel="noreferrer">DOI <ExternalLink size={13} /></a>}</div></article>)}</div> : <CompoundLiterature compound={compound} onSelect={onSelect} />}</section>;
      case 'sources':
        return <section className="sdb-data-section sdb-record-section"><div className="sdb-section-title"><div><span>Data Sources</span><h2>Provenance</h2></div></div><div className="sdb-source-list"><div><strong>SweetMeta SQLite</strong><span>{sqliteDetail ? 'Live release API' : 'Offline snapshot'}</span><small>{sqliteDetail ? 'Current read-only database response' : 'Bundled JSON fallback; not guaranteed current'}</small></div><div><strong>Food associations</strong><span>{sqliteDetail ? `${sqliteDetail.food.count} records` : 'Not available'}</span><small>Food occurrence records linked to this compound</small></div><div><strong>Regulatory evaluations</strong><span>{sqliteDetail ? `${sqliteDetail.regulatory.count} records` : 'Not available'}</span><small>Regulatory records are not safety conclusions</small></div><div><strong>Receptor activities</strong><span>{sqliteDetail ? `${sqliteDetail.receptors.count} records` : 'Not available'}</span><small>Activity records from linked assays</small></div><div><strong>PubChem</strong>{compound.pubchem?.sourceUrl ? <a href={compound.pubchem.sourceUrl} target="_blank" rel="noreferrer">Exact-key enrichment <ExternalLink size={13} /></a> : <span>Not available</span>}<small>Properties and structure conformer</small></div><div><strong>ChEMBL</strong>{compound.chembl ? <a href={compound.chembl.sourceUrl} target="_blank" rel="noreferrer">{compound.chembl.id} <ExternalLink size={13} /></a> : <span>Not available</span>}<small>Unique exact full-InChIKey identity match</small></div></div></section>;
      default:
        return <section className="sdb-data-section sdb-record-section"><div className="sdb-section-title"><div><span>Overview</span><h2>Evidence and identity status</h2></div></div>{detailError && <div className="sdb-inline-notice" role="status">SQLite detail unavailable; showing offline snapshot data. {detailError}</div>}<div className="sdb-detail-grid"><dl className="sdb-definition-list"><div><dt>Release tier</dt><dd>{readable(compound.evidence.releaseTier)}</dd></div><div><dt>Accepted assertions</dt><dd>{sqliteDetail ? sqliteDetail.evidence.tasteAssertions.length : compound.evidence.acceptedAssertions}</dd></div><div><dt>Evidence gap</dt><dd>{readable(compound.evidence.releaseGap)}</dd></div><div><dt>Priority score</dt><dd>{formatNumber(compound.evidence.priorityScore, 0)}</dd></div></dl><dl className="sdb-definition-list"><div><dt>QC sweet status</dt><dd>{String(sqliteDetail?.quality.qc_sweet_status ?? 'Not available')}</dd></div><div><dt>QC evidence tier</dt><dd>{String(sqliteDetail?.quality.qc_evidence_tier ?? 'Not available')}</dd></div><div><dt>Manual review</dt><dd>{compound.review.required ? 'Required' : 'Not flagged'}</dd></div><div><dt>Created at</dt><dd>{compound.createdAt ?? 'Not available'}</dd></div></dl></div></section>;
    }
  };
  return <div className="sdb-page sdb-detail">
    <button className="sdb-back" onClick={onBack}><ArrowLeft size={17} /> Back to compounds</button>
    <header className="sdb-detail-header">
      <div className="sdb-structure-panel">
        <div className="sdb-structure-toolbar"><span>Chemical structure</span><div role="group" aria-label="Structure view"><button className={structureMode === '2d' ? 'active' : ''} onClick={() => setStructureMode('2d')}>2D</button><button className={structureMode === '3d' ? 'active' : ''} onClick={() => setStructureMode('3d')}><Cuboid size={13} />3D</button></div></div>
        <div className="sdb-detail-image">{structureMode === '2d' ? <MoleculeImage compound={compound} /> : viewerCid && viewerSmiles ? <Molecule3DViewer key={compound.id} cid={viewerCid} name={compound.name} smiles={viewerSmiles} /> : <div className="db-structure-message"><strong>3D conformer unavailable</strong><span>A verified PubChem structure is required for this view.</span></div>}</div>
      </div>
      <div className="sdb-detail-summary">
        <div className="sdb-detail-badges"><TierBadge tier={compound.evidence.releaseTier} /><ReviewBadge compound={compound} />{compound.pubchem?.matchStatus === 'verified' ? <span className="sdb-pubchem-ok"><ShieldCheck size={13} /> PubChem verified</span> : compound.pubchem ? <span className="sdb-discrepancy"><AlertTriangle size={13} /> PubChem discrepancy</span> : null}</div>
        <h1>{compound.name}</h1><p className="sdb-mono">{compound.id}</p>
        <dl className="sdb-core-properties">
          <div><dt>ChEMBL ID</dt><dd>{compound.chembl ? <a href={compound.chembl.sourceUrl} target="_blank" rel="noreferrer">{compound.chembl.id}<ExternalLink size={13} /></a> : 'Not available'}</dd></div>
          <div><dt>PubChem CID</dt><dd>{compound.pubchem?.cid && compound.pubchem.sourceUrl ? <a href={compound.pubchem.sourceUrl} target="_blank" rel="noreferrer">CID {compound.pubchem.cid}<ExternalLink size={13} /></a> : 'Not available'}</dd></div>
          <div className="wide"><dt>SMILES</dt><dd className="sdb-mono">{compound.isomericSmiles ?? compound.canonicalSmiles ?? 'Not available'}</dd></div>
          <div className="wide"><dt>InChIKey</dt><dd className="sdb-mono">{compound.inchiKey ?? 'Not available'}</dd></div>
          <div><dt>Molecular formula</dt><dd>{compound.formula ?? 'Not available'}</dd></div>
          <div><dt>Molecular weight</dt><dd>{compound.molecularWeight === null ? 'Not available' : `${formatNumber(compound.molecularWeight)} Da`}</dd></div>
          <div><dt>Source</dt><dd>{compound.nameSource ?? 'Not available'}</dd></div>
          <div><dt>Entity type</dt><dd>{readable(compound.entityType)}</dd></div>
        </dl>
      </div>
    </header>
    {(compound.review.required || compound.pubchem?.matchStatus === 'matched-with-discrepancy') && <div className="sdb-review-callout"><AlertTriangle /><div><strong>Manual scientific review required</strong><p>{compound.pubchem?.matchStatus === 'matched-with-discrepancy' ? 'The external identifier match exposed a source-field discrepancy. Source values were not overwritten; resolve the preferred name and structure identity before release.' : compound.review.note ?? 'No review note was supplied.'}</p></div></div>}
    <div className="sdb-record-layout">
      <nav className="sdb-record-nav" aria-label="Compound record sections">
        <span className="sdb-record-nav-title">Compound profile</span>
        {DETAIL_SECTIONS.map(({ id, label, icon: Icon }) => <button key={id} type="button" className={activeSection === id ? 'active' : ''} aria-current={activeSection === id ? 'page' : undefined} onClick={() => setActiveSection(id)}><Icon /> <span>{label}</span></button>)}
      </nav>
      <div className="sdb-record-content" id={`record-panel-${activeSection}`} aria-live="polite">
        {renderSection()}
      </div>
    </div>
  </div>;
};

const mergeSqliteCompound = (base: DatabaseCompound, detail: SweetMetaCompoundDetail): DatabaseCompound => {
  const source = detail.compound as Record<string, unknown>;
  return {
    ...base,
    name: String(source.preferred_name ?? base.name),
    inchiKey: String(source.parent_inchikey ?? base.inchiKey ?? ''),
    isomericSmiles: source.parent_isomeric_smiles ? String(source.parent_isomeric_smiles) : base.isomericSmiles,
    canonicalSmiles: source.parent_canonical_smiles ? String(source.parent_canonical_smiles) : base.canonicalSmiles,
    formula: source.molecular_formula ? String(source.molecular_formula) : base.formula,
    molecularWeight: typeof source.molecular_weight === 'number' ? source.molecular_weight : base.molecularWeight,
    formalCharge: typeof source.formal_charge === 'number' ? source.formal_charge : base.formalCharge,
    heavyAtomCount: typeof source.heavy_atom_count === 'number' ? source.heavy_atom_count : base.heavyAtomCount,
    evidence: {
      ...base.evidence,
      releaseTier: typeof detail.release.release_tier === 'string' ? detail.release.release_tier : base.evidence.releaseTier,
      releaseGap: typeof detail.release.release_gap === 'string' ? detail.release.release_gap : base.evidence.releaseGap,
      acceptedAssertions: detail.evidence.tasteAssertions.length,
    },
    review: {
      ...base.review,
      required: Boolean(detail.release.manual_review_required),
      note: typeof detail.release.status_note === 'string' ? detail.release.status_note : base.review.note,
    },
  };
};

const DatabaseInterface = ({ onClose }: { onClose?: () => void }) => {
  const state = initialState();
  const [section, setSection] = useState<DatabaseSection>(state.section);
  const [compoundId, setCompoundId] = useState<string | null>(state.compoundId);
  const [query, setQuery] = useState(state.query);
  const [tier, setTier] = useState(state.tier);
  const [routeState, setRouteState] = useState(state);
  const [menuOpen, setMenuOpen] = useState(false);
  const compound = compoundId ? DATABASE_COMPOUNDS.find((item) => item.id === compoundId) ?? null : null;
  const [sqliteDetail, setSqliteDetail] = useState<SweetMetaCompoundDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  useEffect(() => {
    if (!compoundId) { setSqliteDetail(null); setDetailError(null); return; }
    let active = true;
    setSqliteDetail(null); setDetailError(null);
    fetchSweetMetaCompound(compoundId).then((data) => { if (active) setSqliteDetail(data); }).catch((error: unknown) => { if (active) setDetailError(error instanceof Error ? error.message : 'SQLite detail request failed'); });
    return () => { active = false; };
  }, [compoundId]);
  useEffect(() => { const onPop = () => { const next = initialState(); setRouteState(next); setSection(next.section); setCompoundId(next.compoundId); setQuery(next.query); setTier(next.tier); setMenuOpen(false); }; window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop); }, []);
  const resetScroll = () => { const main = document.querySelector<HTMLElement>('.sdb-main'); if (main) main.scrollTop = 0; };
  const navigate = (next: DatabaseSection) => { setSection(next); setCompoundId(null); setQuery(''); setTier('all'); setMenuOpen(false); updateUrl(next, null); setRouteState(initialState()); resetScroll(); };
  const search = (nextQuery: string) => { setSection('compounds'); setCompoundId(null); setQuery(nextQuery); setTier('all'); setMenuOpen(false); updateUrl('compounds', null, { query: nextQuery, tier: 'all' }); setRouteState(initialState()); resetScroll(); };
  const select = (id: string) => { setSection('compounds'); setCompoundId(id); updateUrl('compounds', id, { query, tier }); resetScroll(); };
  const back = () => { setCompoundId(null); updateUrl('compounds', null, { query, tier }); };
  const openStatisticsResult = (target: 'compounds' | 'literature', values: Record<string, string | number | null | undefined>) => {
    const params = new URLSearchParams({ section: target });
    Object.entries(values).forEach(([key, value]) => { if (value !== null && value !== undefined && value !== '') params.set(key, String(value)); });
    window.history.pushState({ database: true }, '', `/database?${params}`);
    const next = initialState();
    setRouteState(next); setSection(next.section); setCompoundId(null); setQuery(next.query); setTier(next.tier); resetScroll();
  };
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
    <main className="sdb-main overflow-auto">{compound ? <Detail compound={sqliteDetail ? mergeSqliteCompound(compound, sqliteDetail) : compound} sqliteDetail={sqliteDetail} detailError={detailError} onBack={back} onSelect={select} /> : section === 'overview' ? <Overview onSelect={select} onSearch={search} /> : section === 'compounds' ? <CompoundIndex key={window.location.search} onSelect={select} initialQuery={query} initialTier={tier} initialDrilldown={{ domain: routeState.domain, foodGroup: routeState.foodGroup, sweetnessMinLog10: routeState.sweetnessMinLog10, sweetnessMaxLog10: routeState.sweetnessMaxLog10, qualityMetric: routeState.qualityMetric, qualityState: routeState.qualityState }} /> : section === 'literature' ? <Literature key={window.location.search} onSelect={select} initialYearFrom={routeState.literatureYearFrom} initialYearTo={routeState.literatureYearTo} initialCompoundFamily={routeState.compoundFamily} /> : section === 'statistics' ? <StatisticsDashboard onCompounds={(values) => openStatisticsResult('compounds', values)} onLiterature={(values) => openStatisticsResult('literature', values)} /> : <Downloads />}</main>
  </div>;
};

export default DatabaseInterface;
