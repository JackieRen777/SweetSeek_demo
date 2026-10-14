import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import {
  AlertTriangle, ArrowLeft, ArrowUpDown, Atom, BarChart3, Beaker, BookOpen, Check, ChevronDown,
  ChevronLeft, ChevronRight, CircleHelp, Cuboid, Database, Download, ExternalLink,
  FileCheck2, FileWarning, Filter, FlaskConical, Home, Library, Menu,
  Network, Search, ShieldCheck, X, Copy,
} from 'lucide-react';
import { CHEMICAL_SPACE } from './data/chemicalSpace';
import { DATABASE_COMPOUNDS, DATABASE_METADATA, formatNumber, readable, tierCode } from './data/portalData';
import LITERATURE_SUMMARY from './data/literatureSummary.generated.json';
import LiteratureEvidenceTable from './components/LiteratureTable';
import type { DatabaseCompound, DatabaseSection } from './types';
import { fetchSweetMetaCompound, fetchSweetMetaCompounds, fetchSweetMetaDownloads, fetchSweetMetaLiterature, type SweetMetaCompoundDetail, type SweetMetaDataRecord, type SweetMetaDownloads, type SweetMetaLiteratureRecord } from './sweetmetaApi';
import { loadLiteratureData, RELATIONSHIP_LABELS, type CompoundPaperLink, type LiteratureData } from './literature';
import Molecule3DViewer, { preloadMolecule3D } from './components/Molecule3DViewer';
import CompoundProjection from './components/CompoundProjection';
import StatisticsDashboard from './components/StatisticsDashboard';
import './database.css';

const SECTIONS: Array<{ id: DatabaseSection; label: string; icon: typeof Database }> = [
  { id: 'overview', label: 'Home', icon: Home },
  { id: 'compounds', label: 'Browse', icon: Beaker },
  { id: 'literature', label: 'Literature', icon: Library },
  { id: 'statistics', label: 'Statistics', icon: BarChart3 },
  { id: 'downloads', label: 'Downloads', icon: Download },
];

const DETAIL_SECTIONS = [
  { id: 'basic', label: 'Overview', icon: CircleHelp, group: 'Compound profile' },
  { id: 'sweetness', label: 'Sweetness & evidence', icon: FlaskConical, group: 'Compound profile' },
  { id: 'chemical-space', label: 'Chemical space', icon: Network, group: 'Compound profile' },
  { id: 'literature', label: 'Literature', icon: BookOpen, group: 'Evidence' },
  { id: 'linked', label: 'Linked records', icon: FileCheck2, group: 'Evidence' },
  { id: 'structure', label: 'Structure & similarity', icon: Cuboid, group: 'Structure quality' },
  { id: 'quality', label: 'QC & review', icon: ShieldCheck, group: 'Structure quality' },
] as const;

type DetailSection = typeof DETAIL_SECTIONS[number]['id'];

const LEGACY_DETAIL_PANELS: Record<string, DetailSection> = {
  classification: 'basic', properties: 'basic', provenance: 'sweetness',
  food: 'linked', receptors: 'linked', regulatory: 'linked', similar: 'structure',
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
    sweetClassL1: params.get('sweetClassL1') ?? '',
    sweetClassL2: params.get('sweetClassL2') ?? '',
    evidenceGrade: params.get('evidenceGrade') ?? '',
    sourceCollection: params.get('sourceCollection') ?? '',
    mwMin: params.get('mwMin') ?? '', mwMax: params.get('mwMax') ?? '',
    clogpMin: params.get('clogpMin') ?? '', clogpMax: params.get('clogpMax') ?? '',
    tpsaMin: params.get('tpsaMin') ?? '', tpsaMax: params.get('tpsaMax') ?? '',
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
  const [failure, setFailure] = useState<{ id: string; source: 'local' | 'remote' } | null>(null);
  const failed = failure?.id === compound.id ? failure.source : null;
  const source = failed === 'local' ? remoteSource : failed === 'remote' ? null : localSource ?? remoteSource;
  if (!source) return <div className={`sdb-structure-empty ${small ? 'small' : ''}`}><FlaskConical /></div>;
  return <img className={`sdb-structure ${small ? 'small' : ''}`} src={source} alt={`${compound.name} verified structure`} onError={() => setFailure({ id: compound.id, source: source === localSource ? 'local' : 'remote' })} />;
};

const ReviewBadge = ({ compound }: { compound: DatabaseCompound }) => compound.review.required || compound.pubchem?.matchStatus === 'matched-with-discrepancy'
  ? <span className="sdb-review"><AlertTriangle size={13} /> Manual review</span>
  : <span className="sdb-verified"><ShieldCheck size={13} /> Released</span>;

const EmptyState = ({ icon: Icon, title, children }: { icon: typeof Database; title: string; children: React.ReactNode }) => (
  <div className="sdb-empty-state"><Icon /><h3>{title}</h3><p>{children}</p></div>
);

const HERO_STATISTICS_SLIDES = [
  { title: 'SweetClass Composition', section: 'Composition', image: '/database-assets/statistics-preview/sweetclass-composition.png' },
  { title: 'PCA Molecular Space', section: 'Chemical space', image: '/database-assets/statistics-preview/pca-molecular-space.png' },
  { title: 'Evidence Provenance', section: 'Evidence', image: '/database-assets/statistics-preview/evidence-provenance.png' },
  { title: 'Family Evidence Grades', section: 'Evidence', image: '/database-assets/statistics-preview/family-evidence-grades.png' },
  { title: 'Physicochemical Landscape', section: 'Properties', image: '/database-assets/statistics-preview/physicochemical-landscape.png' },
] as const;

const HeroStatisticsPreview = ({ onOpen }: { onOpen: () => void }) => {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const direction = useRef<1 | -1>(1);
  useEffect(() => {
    if (paused || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
    const timer = window.setInterval(() => setIndex((current) => {
      if (current === HERO_STATISTICS_SLIDES.length - 1) direction.current = -1;
      if (current === 0) direction.current = 1;
      return current + direction.current;
    }), 4200);
    return () => window.clearInterval(timer);
  }, [paused]);
  return <section className="sdb-hero-stat-preview" aria-roledescription="carousel" aria-label="SweetMeta Statistics previews" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setPaused(false); }}>
    <button type="button" className="sdb-hero-stat-plot" onClick={onOpen} aria-label={`Open ${HERO_STATISTICS_SLIDES[index].title} in Statistics`}>
      {HERO_STATISTICS_SLIDES.map((item, itemIndex) => <img key={item.title} className={itemIndex === index ? 'active' : ''} src={item.image} alt={item.title} aria-hidden={itemIndex !== index} />)}
    </button>
  </section>;
};

const EXAMPLE_COMPOUNDS = [
  { name: 'Sucrose', id: 'CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N' },
  { name: 'Glucose', id: 'CMP_GZCGUPFRVQAUEE-SLPGGIOYSA-N' },
  { name: 'Aspartame', id: 'CMP_IAOZJIPTCAWIRG-QWRGUYRKSA-N' },
];

const BUNDLED_DISPLAY_IDS = new Map(
  DATABASE_COMPOUNDS.map((compound, index) => [compound.id, String(index + 1).padStart(6, '0')]),
);

const compactIdentifiers = (values: string[] | undefined) => {
  if (!values?.length) return { label: '—', title: undefined };
  return {
    label: values.length === 1 ? values[0] : `${values[0]} +${values.length - 1}`,
    title: values.join(', '),
  };
};

const Overview = ({ onSelect, onSearch, onStatistics }: {
  onSelect: (id: string) => void;
  onSearch: (query: string) => void;
  onStatistics: () => void;
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
        <HeroStatisticsPreview onOpen={onStatistics} />
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
    </div>
  </div>;
};

type BrowseDrilldown = { domain: string; foodGroup: string; sweetnessMinLog10: string; sweetnessMaxLog10: string; qualityMetric: string; qualityState: string; sweetClassL1: string; sweetClassL2: string; evidenceGrade: string; sourceCollection: string; mwMin: string; mwMax: string; clogpMin: string; clogpMax: string; tpsaMin: string; tpsaMax: string };
const EMPTY_BROWSE_DRILLDOWN: BrowseDrilldown = { domain: '', foodGroup: '', sweetnessMinLog10: '', sweetnessMaxLog10: '', qualityMetric: '', qualityState: '', sweetClassL1: '', sweetClassL2: '', evidenceGrade: '', sourceCollection: '', mwMin: '', mwMax: '', clogpMin: '', clogpMax: '', tpsaMin: '', tpsaMax: '' };

const SWEETCLASS_TAXONOMY: Record<string, string[]> = {
  'Peptide and amino-acid sweeteners': ['Amino acids and amino-acid derivatives', 'Aspartic-acid derivatives', 'Dipeptide and hybrid-peptide sweeteners', 'Peptide sweeteners'],
  'Glycosidic natural sweeteners': ['Fatty-acyl glycosides', 'Flavonoid glycosides', 'Other O- and C-glycosides', 'Steroidal glycosides', 'Steviol glycosides', 'Triterpene and saponin glycosides'],
  'Aromatic, phenolic and flavonoid sweeteners': ['Benzoic- and phenylpropanoic-acid derivatives', 'Chalcones and dihydrochalcones', 'Flavonoids and flavans', 'N-Phenylureas', 'Other aromatic sweeteners', 'Phenols and methoxyphenols'],
  'Heterocyclic and other specialised sweeteners': ['Heterocyclic sweeteners', 'Other specialised structures'],
  'Sulfur- and nitrogen-containing synthetic sweeteners': ['Cyclamate-type sweeteners', 'Saccharin and related oxathiazinones', 'Sulfamates and sulfuric-acid monoamides', 'Sulfanilides'],
  'Carbohydrates, rare sugars and polyols': ['Monosaccharides and rare sugars', 'Oligosaccharides', 'Other carbohydrate derivatives', 'Sugar alcohols and polyols'],
  'Non-glycosidic terpenoid, steroid and lipid-like sweeteners': ['Fatty acids and lipid-like sweeteners', 'Non-glycosidic steroids'],
};
const SWEETCLASS_FAMILIES = Object.keys(SWEETCLASS_TAXONOMY);

const CompoundIndex = ({ onSelect, initialQuery, initialTier, initialDrilldown }: { onSelect: (id: string) => void; initialQuery: string; initialTier: string; initialDrilldown: BrowseDrilldown }) => {
  const [query, setQuery] = useState(initialQuery);
  const [tier] = useState(initialTier);
  const [page, setPage] = useState(1);
  const [drilldown, setDrilldown] = useState(initialDrilldown);
  const [advancedOpen, setAdvancedOpen] = useState(() => Boolean(
    initialDrilldown.sweetClassL2 || initialDrilldown.mwMin || initialDrilldown.mwMax
    || initialDrilldown.clogpMin || initialDrilldown.clogpMax
    || initialDrilldown.tpsaMin || initialDrilldown.tpsaMax,
  ));
  const pageSize = 25;
  const [remote, setRemote] = useState<{ items: DatabaseCompound[]; total: number; pageCount: number } | null>(null);
  const [remoteError, setRemoteError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    fetchSweetMetaCompounds({
      query, page, pageSize, tier,
      domain: drilldown.domain,
      foodGroup: drilldown.foodGroup,
      sweetnessMinLog10: drilldown.sweetnessMinLog10 === '' ? undefined : Number(drilldown.sweetnessMinLog10),
      sweetnessMaxLog10: drilldown.sweetnessMaxLog10 === '' ? undefined : Number(drilldown.sweetnessMaxLog10),
      qualityMetric: drilldown.qualityMetric,
      qualityState: drilldown.qualityState,
      sweetClassL1: drilldown.sweetClassL1,
      sweetClassL2: drilldown.sweetClassL2,
      evidenceGrade: drilldown.evidenceGrade,
      sourceCollection: drilldown.sourceCollection,
      mwMin: drilldown.mwMin === '' ? undefined : Number(drilldown.mwMin), mwMax: drilldown.mwMax === '' ? undefined : Number(drilldown.mwMax),
      clogpMin: drilldown.clogpMin === '' ? undefined : Number(drilldown.clogpMin), clogpMax: drilldown.clogpMax === '' ? undefined : Number(drilldown.clogpMax),
      tpsaMin: drilldown.tpsaMin === '' ? undefined : Number(drilldown.tpsaMin), tpsaMax: drilldown.tpsaMax === '' ? undefined : Number(drilldown.tpsaMax),
    })
      .then((payload) => {
        if (!active) return;
        setRemote({
          items: payload.items.map((item) => ({
            id: item.id,
            displayId: item.displayId,
            casNumbers: item.casNumbers,
            browsePubchemCid: item.pubchemCid,
            chemicalClass: item.chemicalClass,
            sourceNames: item.sourceNames,
            reviewedSourceNames: item.reviewedSourceNames,
            sourceCollection: item.sourceCollection,
            sweetClassLevel1: item.sweetClassLevel1,
            sweetClassLevel2: item.sweetClassLevel2,
            evidenceGrade: item.evidenceGrade,
            reviewedProperties: { clogp: item.clogp, tpsa: item.tpsa, rotatableBonds: item.rotatableBonds, hba: item.hba, hbd: item.hbd },
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
  }, [drilldown, page, pageSize, query, tier]);
  const filtered = useMemo(() => {
    if (remote) return remote.items;
    const q = query.trim().toLocaleLowerCase();
    return DATABASE_COMPOUNDS.filter((compound) => {
      const searchable = [compound.id, compound.name, compound.inchiKey, compound.formula, compound.pubchem?.cid, compound.pubchem?.iupacName].filter(Boolean).join(' ').toLocaleLowerCase();
      return (!q || searchable.includes(q))
        && (tier === 'all' || tierCode(compound.evidence.releaseTier) === tier);
    });
  }, [query, remote, tier]);
  const pageCount = remote?.pageCount ?? Math.max(1, Math.ceil(filtered.length / pageSize));
  const visible = remote ? filtered : filtered.slice((page - 1) * pageSize, page * pageSize);
  return (
    <div className="sdb-page">
      <header className="sdb-page-heading compact"><div><span className="sdb-kicker">Compound index</span><h1>Browse the current release</h1><p>Search IDs, names, CAS numbers, formulae, InChIKeys, or verified PubChem identifiers.</p></div></header>
      <div className="sdb-filterbar">
        <label className="sdb-search"><Search size={18} /><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Search compounds" aria-label="Search compounds" />{query && <button title="Clear search" onClick={() => { setQuery(''); setPage(1); }}><X size={16} /></button>}</label>
        <label className="sdb-flat-select"><Filter size={16} /><select aria-label="SweetClass family" value={drilldown.sweetClassL1} onChange={(event) => { setDrilldown((value) => ({ ...value, sweetClassL1: event.target.value, sweetClassL2: '' })); setPage(1); }}><option value="">All SweetClass families</option>{SWEETCLASS_FAMILIES.map((family) => <option key={family}>{family}</option>)}</select><ChevronDown className="sdb-select-chevron" aria-hidden="true" /></label>
        <label className="sdb-flat-select"><select aria-label="Evidence grade" value={drilldown.evidenceGrade} onChange={(event) => { setDrilldown((value) => ({ ...value, evidenceGrade: event.target.value })); setPage(1); }}><option value="">All provenance grades</option><option value="E1">E1 · primary</option><option value="E2">E2 · supported</option><option value="E3">E3 · database curated</option></select><ChevronDown className="sdb-select-chevron" aria-hidden="true" /></label>
        <button type="button" className={`sdb-more-filters ${advancedOpen ? 'active' : ''}`} aria-expanded={advancedOpen} aria-controls="browse-advanced-filters" onClick={() => setAdvancedOpen((value) => !value)}><Filter size={15} /> More filters <ChevronDown size={14} /></button>
      </div>
      {advancedOpen && <div className="sdb-advanced-filters" id="browse-advanced-filters">
        <label className="sdb-advanced-select"><span>SweetClass level 2</span><select aria-label="SweetClass subclass" value={drilldown.sweetClassL2} disabled={!drilldown.sweetClassL1} onChange={(event) => { setDrilldown((value) => ({ ...value, sweetClassL2: event.target.value })); setPage(1); }}><option value="">{drilldown.sweetClassL1 ? 'All subclasses in family' : 'Select a level-1 family first'}</option>{(SWEETCLASS_TAXONOMY[drilldown.sweetClassL1] ?? []).map((subclass) => <option key={subclass}>{subclass}</option>)}</select><ChevronDown aria-hidden="true" /></label>
        {([['MW', 'mwMin', 'mwMax'], ['cLogP', 'clogpMin', 'clogpMax'], ['TPSA', 'tpsaMin', 'tpsaMax']] as const).map(([label, minKey, maxKey]) => <fieldset className="sdb-property-range" key={label}><legend>{label}</legend><label><span>Min</span><input type="number" step="any" aria-label={`${label} minimum`} value={drilldown[minKey]} onChange={(event) => { setDrilldown((value) => ({ ...value, [minKey]: event.target.value })); setPage(1); }} /></label><i>to</i><label><span>Max</span><input type="number" step="any" aria-label={`${label} maximum`} value={drilldown[maxKey]} onChange={(event) => { setDrilldown((value) => ({ ...value, [maxKey]: event.target.value })); setPage(1); }} /></label></fieldset>)}
        <button type="button" className="sdb-clear-advanced" onClick={() => { setDrilldown((value) => ({ ...value, sweetClassL2: '', mwMin: '', mwMax: '', clogpMin: '', clogpMax: '', tpsaMin: '', tpsaMax: '' })); setPage(1); }}>Reset properties</button>
      </div>}
      {Object.values(drilldown).some(Boolean) && <div className="sdb-drilldown-banner" role="status"><span>Active filters: {[drilldown.domain, drilldown.foodGroup, drilldown.sourceCollection, drilldown.sweetClassL1, drilldown.sweetClassL2, drilldown.evidenceGrade, drilldown.qualityMetric, drilldown.qualityState].filter(Boolean).map(readable).join(' · ') || 'Numeric range'}</span><button onClick={() => { setDrilldown(EMPTY_BROWSE_DRILLDOWN); setPage(1); }}>Clear filters</button></div>}
      <div className="sdb-result-meta"><strong>{(remote?.total ?? filtered.length).toLocaleString()}</strong> records <span>Source: {remote ? 'SweetMeta SQLite API' : DATABASE_METADATA.sourceWorkbook}</span></div>
      {remoteError && <div className="sdb-inline-notice" role="status">Live SQLite API unavailable; showing the bundled release snapshot.</div>}
      <div className="sdb-table-wrap sdb-catalog-table-wrap"><table className="sdb-table sdb-catalog-table"><thead><tr><th>ID</th><th>Name</th><th>Formula</th><th>SweetClass</th><th>Evidence grade</th><th>MW</th><th>Source</th></tr></thead><tbody>{visible.map((compound) => {
        const sources = compactIdentifiers(compound.sourceNames);
        const displayId = compound.displayId ?? BUNDLED_DISPLAY_IDS.get(compound.id) ?? '—';
        return <tr key={compound.id} onClick={() => onSelect(compound.id)}>
          <td><span className="sdb-display-id">{displayId}</span></td>
          <td><button type="button" className="sdb-compound-name" onClick={() => onSelect(compound.id)}>{compound.name}</button></td>
          <td className="sdb-mono">{compound.formula ?? '—'}</td>
          <td title={compound.sweetClassLevel2 ?? undefined}><strong>{compound.sweetClassLevel1 ?? compound.chemicalClass ?? '—'}</strong><small>{compound.sweetClassLevel2}</small></td>
          <td><span className="sdb-tier">{compound.evidenceGrade ?? '—'}</span></td>
          <td>{formatNumber(compound.molecularWeight)} Da</td>
          <td title={(compound.reviewedSourceNames ?? compound.sourceNames)?.join(', ')}>{compound.sourceCollection ?? sources.label}</td>
        </tr>;
      })}</tbody></table></div>
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
          {paper.journal && <td>{paper.journal}</td>}
          {!paper.journal && <td><span className="sdb-muted">—</span></td>}
          {paper.year && <td>{paper.year}</td>}
          {!paper.year && <td><span className="sdb-muted">—</span></td>}
          {paper.pmid ? (
            <td><a href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/`} target="_blank" rel="noreferrer">{paper.pmid} <ExternalLink size={12} /></a></td>
          ) : (
            <td><span className="sdb-muted">—</span></td>
          )}
          {paper.doi ? (
            <td><a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer">{paper.doi} <ExternalLink size={12} /></a></td>
          ) : (
            <td><span className="sdb-muted">—</span></td>
          )}
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

const Downloads = () => {
  const [data, setData] = useState<SweetMetaDownloads | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { void fetchSweetMetaDownloads().then(setData).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Downloads unavailable')); }, []);
  const size = (bytes: number) => bytes >= 1_000_000 ? `${(bytes / 1_000_000).toFixed(1)} MB` : `${Math.ceil(bytes / 1000)} KB`;
  return <div className="sdb-page relative"><div className="relative z-0"><header className="sdb-page-heading compact"><div><span className="sdb-kicker">Data access</span><h1>Downloads</h1><p>SweetMeta v1.0.7 reviewed snapshot, dated 2026-10-05. Files are served from the allowlisted release package.</p></div></header>{error && <div className="sdb-inline-notice">{error}</div>}<div className="sdb-download-list">{data?.items.map((item) => <article key={item.key}><Database /><span><strong>{item.label}</strong><small>{item.filename} · {size(item.bytes)} · {data.recordCount.toLocaleString()} compounds</small><code>SHA-256 {item.sha256}</code></span><a className="sdb-download-button" href={item.url} download><Download size={15} /> Download</a></article>)}</div><div className="sdb-policy-note"><FileWarning /><div><strong>E1-E3 and R1-R4 are separate systems</strong><p>The data dictionary defines provenance grades, release readiness, units, sources, and null-value rules.</p></div></div></div><div className="absolute inset-0 backdrop-blur-md bg-white/70 flex items-center justify-center z-10"><div className="text-center"><p className="text-2xl font-bold text-slate-700">Temporarily unavailable</p></div></div></div>;
};

const RecordTable = ({ title, records }: { title: string; records: SweetMetaDataRecord[] }) => {
  const [sortKey, setSortKey] = useState('');
  const [descending, setDescending] = useState(false);
  if (!records.length) return null;
  const columns = [...new Set(records.flatMap((record) => Object.keys(record)))].filter((key) => key !== 'raw_json').slice(0, 7);
  const sorted = [...records].sort((a, b) => {
    if (!sortKey) return 0;
    const result = String(a[sortKey] ?? '').localeCompare(String(b[sortKey] ?? ''), undefined, { numeric: true, sensitivity: 'base' });
    return descending ? -result : result;
  });
  const changeSort = (column: string) => {
    if (sortKey === column) setDescending((value) => !value);
    else { setSortKey(column); setDescending(false); }
  };
  if (records.length <= 3) return <section className="sdb-record-table sdb-record-table-visible sdb-record-cards"><header><strong>{title}</strong><span>{records.length}</span></header><div>{records.map((record, index) => <dl key={index}>{columns.map((column) => <div key={column}><dt>{readable(column)}</dt><dd>{record[column] === null || record[column] === undefined || record[column] === '' ? '—' : String(record[column])}</dd></div>)}</dl>)}</div></section>;
  const table = <div className="sdb-table-wrap"><table className="sdb-table"><thead><tr>{columns.map((column) => <th key={column}><button type="button" onClick={() => changeSort(column)}>{readable(column)} <ArrowUpDown size={11} /></button></th>)}</tr></thead><tbody>{sorted.slice(0, 100).map((record, index) => <tr key={index}>{columns.map((column) => <td key={column}>{record[column] === null || record[column] === undefined || record[column] === '' ? '—' : String(record[column])}</td>)}</tr>)}</tbody></table></div>;
  if (records.length <= 8) return <section className="sdb-record-table sdb-record-table-visible"><header><strong>{title}</strong><span>{records.length}</span></header>{table}</section>;
  return <details className="sdb-record-table"><summary>{title} <span>{records.length}</span></summary>{table}</details>;
};

const SweetnessMeasurements = ({ records }: { records: SweetMetaDataRecord[] }) => <div className="sdb-measurement-list">
  {records.map((record, index) => {
    const relative = typeof record.relative_sweetness === 'number' ? record.relative_sweetness : null;
    const logValue = typeof record.log10_relative_sweetness === 'number' ? record.log10_relative_sweetness : null;
    return <article className="sdb-measurement" key={String(record.measurement_id ?? index)}>
      <div className="sdb-measurement-value"><span>Relative sweetness</span><strong>{relative === null ? 'Not reported' : `${formatNumber(relative, relative >= 100 ? 0 : 1)}×`}</strong><small>{logValue === null ? 'Original log10 value unavailable' : `log10 value ${formatNumber(logValue, 2)}`}</small></div>
      <dl>
        <div><dt>Reference compound</dt><dd>{String(record.reference_compound ?? 'Not reported')}</dd></div>
        <div><dt>Reference concentration</dt><dd>{String(record.reference_concentration ?? 'Not reported')}</dd></div>
        <div><dt>Measurement status</dt><dd>{String(record.measurement_status ?? 'Not reported')}</dd></div>
        <div><dt>Evidence reference</dt><dd>{String(record.evidence_reference ?? 'Not available')}</dd></div>
      </dl>
      <details className="sdb-record-metadata"><summary>Record metadata</summary><dl><div><dt>Measurement ID</dt><dd>{String(record.measurement_id ?? '—')}</dd></div><div><dt>Source</dt><dd>{String(record.source_id ?? '—')}</dd></div><div><dt>Source record</dt><dd>{String(record.source_record_id ?? '—')}</dd></div></dl></details>
    </article>;
  })}
</div>;

const TasteAssertions = ({ records }: { records: SweetMetaDataRecord[] }) => <section className="sdb-assertions">
  <header><div><span>Taste assertions</span><strong>Accepted source-level records</strong></div><b>{records.length}</b></header>
  <div className="sdb-assertion-list">{records.map((record, index) => <article key={String(record.assertion_id ?? index)}>
    <div className="sdb-assertion-taste"><strong>{String(record.source_taste_text ?? record.normalized_taste ?? 'Taste not specified')}</strong><span>{String(record.normalized_taste ?? 'Unclassified')}</span></div>
    <div><span>Status</span><strong>{String(record.assertion_status ?? 'Not reported')}</strong></div>
    <div><span>Source</span><strong>{String(record.source_id ?? 'Not reported')}</strong></div>
    <p>{String(record.evidence_reference ?? 'No bibliographic reference supplied')}</p>
  </article>)}</div>
</section>;

const DetailSectionTitle = ({ eyebrow, title, note }: { eyebrow: string; title: string; note?: string }) => <div className="sdb-section-title"><div><span>{eyebrow}</span><h2>{title}</h2>{note && <p>{note}</p>}</div></div>;

const CopyValue = ({ label, value }: { label: string; value: string | null | undefined }) => {
  const [copied, setCopied] = useState(false);
  const shown = value || 'Not available';
  return <div className="sdb-copy-row"><span><small>{label}</small><code>{shown}</code></span>{value && <button type="button" title={`Copy ${label}`} aria-label={`Copy ${label}`} onClick={() => { void navigator.clipboard?.writeText(value); setCopied(true); window.setTimeout(() => setCopied(false), 1200); }}>{copied ? <Check /> : <Copy />}</button>}</div>;
};

const externalIdUrl = (namespace: string, value: string) => {
  const key = namespace.toLowerCase();
  if (key === 'pubchemcid') return `https://pubchem.ncbi.nlm.nih.gov/compound/${encodeURIComponent(value)}`;
  if (key === 'chembl') return `https://www.ebi.ac.uk/chembl/explore/compound/${encodeURIComponent(value)}`;
  if (key === 'cas') return `https://commonchemistry.cas.org/detail?cas_rn=${encodeURIComponent(value)}`;
  if (key === 'iuphar_ligand') return `https://www.guidetopharmacology.org/GRAC/LigandDisplayForward?ligandId=${encodeURIComponent(value)}`;
  return null;
};

const Detail = ({ compound, onBack, onSelect, sqliteDetail, detailError }: { compound: DatabaseCompound; onBack: () => void; onSelect: (id: string) => void; sqliteDetail: SweetMetaCompoundDetail | null; detailError: string | null }) => {
  const panelParam = new URLSearchParams(window.location.search).get('panel');
  const requestedPanel: DetailSection | null = panelParam ? (LEGACY_DETAIL_PANELS[panelParam] ?? (DETAIL_SECTIONS.some((item) => item.id === panelParam) ? panelParam as DetailSection : null)) : null;
  const [activeSection, setActiveSection] = useState<DetailSection>(requestedPanel ?? 'basic');
  const [structureMode, setStructureMode] = useState<'2d' | '3d'>('2d');
  const neighbors = (CHEMICAL_SPACE.neighbors?.[compound.id] ?? []).flatMap((neighbor) => {
    const match = DATABASE_COMPOUNDS.find((item) => item.id === neighbor.id);
    return match ? [{ compound: match, similarity: neighbor.similarity }] : [];
  });
  const viewerCid = compound.pubchem?.matchStatus === 'verified' ? compound.pubchem.cid : null;
  const viewerSmiles = compound.pubchem?.smiles ?? compound.isomericSmiles ?? compound.canonicalSmiles;
  const classification = sqliteDetail?.classification;
  const provenance = sqliteDetail?.provenance;
  const grade = provenance?.evidence_grade ?? compound.evidenceGrade ?? null;
  const aliases = (sqliteDetail?.aliases ?? []).map((item) => item.alias).filter((item) => item && item.toLocaleLowerCase() !== compound.name.toLocaleLowerCase());
  const externalIds = sqliteDetail?.externalIds ?? [];
  const casNumbers = [...new Set([...externalIds.filter((item) => item.namespace.toLowerCase() === 'cas').map((item) => item.external_id), ...(compound.casNumbers ?? [])])];
  const pubchemId = externalIds.find((item) => item.namespace.toLowerCase() === 'pubchemcid')?.external_id ?? (compound.pubchem?.cid ? String(compound.pubchem.cid) : compound.browsePubchemCid ?? null);
  const chemblId = externalIds.find((item) => item.namespace.toLowerCase() === 'chembl')?.external_id ?? compound.chembl?.id ?? null;
  const modules = sqliteDetail?.modules ?? { sweetness: sqliteDetail?.evidence.measurements.length ?? 0, literature: sqliteDetail?.literature.length ?? 0, food: sqliteDetail?.food.count ?? 0, receptors: sqliteDetail?.receptors.count ?? 0, regulatory: sqliteDetail?.regulatory.count ?? 0, conflicts: sqliteDetail?.evidence.conflicts.length ?? 0 };

  useEffect(() => { if (viewerCid && viewerSmiles) preloadMolecule3D(viewerCid, viewerSmiles); }, [viewerCid, viewerSmiles]);
  useEffect(() => {
    if (!panelParam || !LEGACY_DETAIL_PANELS[panelParam]) return;
    const params = new URLSearchParams(window.location.search);
    params.set('panel', LEGACY_DETAIL_PANELS[panelParam]);
    window.history.replaceState({ database: true }, '', `${window.location.pathname}?${params}`);
  }, [panelParam]);

  const selectSection = (id: DetailSection) => {
    setActiveSection(id);
    const params = new URLSearchParams(window.location.search);
    params.set('panel', id);
    window.history.replaceState({ database: true }, '', `${window.location.pathname}?${params}`);
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    document.querySelector('.sdb-record-layout')?.scrollIntoView?.({ block: 'start', behavior: reduceMotion ? 'auto' : 'smooth' });
  };

  const moduleItems: Array<{ label: string; count: number; section: DetailSection; warning?: boolean }> = [
    { label: 'Sweetness', count: modules.sweetness, section: 'sweetness' },
    { label: 'Literature', count: modules.literature + modules.food + modules.receptors + modules.regulatory, section: 'literature' },
    { label: 'Conflicts', count: modules.conflicts, section: 'quality', warning: modules.conflicts > 0 },
  ];

  // Literature data hook must be at component top level
  const { data: literatureData, error: literatureError } = useLiteratureData();

  const emptyModule = (title: string, copy: string, icon: typeof Database = CircleHelp) => <EmptyState icon={icon} title={title}>{copy}</EmptyState>;

  const renderSection = () => {
    switch (activeSection) {
      case 'sweetness': {
        const sourceNames = String(provenance?.source_names ?? '').split(';').map((item) => item.trim()).filter(Boolean);
        return <section className="sdb-data-section sdb-record-section"><DetailSectionTitle eyebrow="Sweetness & evidence" title="Reviewed sensory evidence" note="Primary values are shown first; source identifiers remain available as record metadata." />{sqliteDetail?.evidence.measurements.length ? <SweetnessMeasurements records={sqliteDetail.evidence.measurements} /> : emptyModule('No reviewed quantitative sweetness', 'No quantitative sweetness measurement is linked to this compound in the current release.', FlaskConical)}{sqliteDetail?.evidence.tasteAssertions.length ? <TasteAssertions records={sqliteDetail.evidence.tasteAssertions} /> : emptyModule('No reviewed taste assertions', 'No accepted taste assertion is available for this compound.', FlaskConical)}<div className="sdb-section-divider"><span>Evidence lineage</span></div><ol className="sdb-provenance-flow"><li><span>Source collection</span><strong>{provenance?.source_collection ?? 'Not available'}</strong></li><li><span>Evidence grade</span><strong className={`grade-${String(grade ?? '').toLowerCase()}`}>{grade ?? 'Not available'}</strong></li><li><span>Lineage status</span><strong>{provenance?.evidence_lineage_status ?? 'Not available'}</strong></li></ol><dl className="sdb-definition-list sdb-provenance-detail"><div><dt>Evidence tier</dt><dd>{provenance?.evidence_tier ?? 'Not available'}</dd></div><div><dt>Accepted assertions</dt><dd>{sqliteDetail?.evidence.tasteAssertions.length ?? compound.evidence.acceptedAssertions}</dd></div><div><dt>Source names</dt><dd>{sourceNames.join(', ') || 'Not available'}</dd></div></dl></section>;
      }
      case 'chemical-space':
        return <section className="sdb-data-section sdb-record-section"><DetailSectionTitle eyebrow="Chemical space" title="Position within the SweetClass family" note="The selected compound is shown against members of its reviewed level-1 family." /><CompoundProjection compoundId={compound.id} onCompound={onSelect} /></section>;
      case 'literature': {
        if (literatureError) {
          return <section className="sdb-data-section sdb-record-section">
            <DetailSectionTitle eyebrow="Literature" title="Literature and linked records" note="Evidence-based literature links from the SweetSeek corpus and related data modules." />
            <EmptyState icon={FileWarning} title="Literature data could not be loaded">{literatureError}</EmptyState>
          </section>;
        }

        if (!literatureData) {
          return <section className="sdb-data-section sdb-record-section">
            <DetailSectionTitle eyebrow="Literature" title="Literature and linked records" note="Evidence-based literature links from the SweetSeek corpus and related data modules." />
            <EmptyState icon={BookOpen} title="Loading literature registry">Reading the compound-paper evidence index.</EmptyState>
          </section>;
        }

        const compoundLinks = literatureData.links.filter((link) => link.compoundId === compound.id);

        return <section className="sdb-data-section sdb-record-section">
          <DetailSectionTitle eyebrow="Literature" title="Literature and linked records" note="Evidence-based literature links from the SweetSeek corpus and related data modules." />

          {sqliteDetail?.literatureReview?.reviewRequiredCount ? (
            <div className="sdb-inline-notice" role="status">
              Additional candidate literature links are pending review ({sqliteDetail.literatureReview.reviewRequiredCount}).
            </div>
          ) : null}

          <LiteratureEvidenceTable
            links={compoundLinks}
            papers={literatureData.papers}
            compoundName={compound.name}
          />
        </section>;
      }
      case 'structure':
        return <section className="sdb-data-section sdb-record-section"><DetailSectionTitle eyebrow="Structure & similarity" title="Chemical representation" note="The reviewed parent structure is primary; external structures remain linked comparisons." /><div className="sdb-structure-workbench"><div><div className="sdb-segmented" role="group" aria-label="Structure view"><button type="button" className={structureMode === '2d' ? 'active' : ''} onClick={() => setStructureMode('2d')}>2D</button><button type="button" className={structureMode === '3d' ? 'active' : ''} disabled={!viewerCid || !viewerSmiles} onClick={() => setStructureMode('3d')}><Cuboid /> 3D</button></div><div className="sdb-structure-workbench-view">{structureMode === '2d' ? <MoleculeImage compound={compound} /> : viewerCid && viewerSmiles ? <Molecule3DViewer key={compound.id} cid={viewerCid} name={compound.name} smiles={viewerSmiles} /> : null}</div></div><div className="sdb-copy-list"><CopyValue label="Isomeric SMILES" value={compound.isomericSmiles} /><CopyValue label="Canonical SMILES" value={compound.canonicalSmiles} /><CopyValue label="InChIKey" value={compound.inchiKey} /><CopyValue label="Stable ID" value={compound.id} /></div></div><RecordTable title="Aliases and source records" records={sqliteDetail?.aliases ?? []} /><RecordTable title="External identifiers" records={externalIds} /><div className="sdb-section-divider"><span>ECFP4 structural neighbors</span></div>{neighbors.length ? <div className="sdb-similar-grid">{neighbors.map((item) => <button key={item.compound.id} onClick={() => onSelect(item.compound.id)}><MoleculeImage compound={item.compound} small /><span><strong>{item.compound.name}</strong><small>{item.compound.formula ?? 'Formula not available'}</small></span><b>{Math.round(item.similarity * 100)}%</b></button>)}</div> : emptyModule('Similar compounds are not available', 'A valid structure fingerprint is required to calculate molecular neighbors.', Atom)}</section>;
      case 'quality':
        return <section className="sdb-data-section sdb-record-section"><DetailSectionTitle eyebrow="QC & review" title="Structure and release quality" note="Legacy R1–R4 readiness is shown here only and is not equivalent to E1–E3 provenance." /><div className="sdb-quality-summary"><div><span>Structure</span><strong>{sqliteDetail?.quality?.structure_verified || 'Unknown'}</strong></div><div><span>Stereochemistry</span><strong>{sqliteDetail?.quality?.stereochemistry_verified || 'Unknown'}</strong></div><div><span>Chemical form</span><strong>{sqliteDetail?.quality?.form_verified || 'Unknown'}</strong></div><div className="legacy"><span>Legacy readiness</span><strong>{tierCode(compound.evidence.releaseTier)}</strong></div></div>{(compound.review.required || compound.pubchem?.matchStatus === 'matched-with-discrepancy') && <div className="sdb-review-callout"><AlertTriangle /><div><strong>Manual scientific review flag</strong><p>{compound.review.note ?? 'The external structure or identifier comparison differs from the reviewed SweetMeta record.'}</p></div></div>}<RecordTable title="Quality-control fields" records={sqliteDetail?.quality ? [sqliteDetail.quality] : []} />{sqliteDetail?.evidence.conflicts.length ? <RecordTable title="Unresolved conflicts" records={sqliteDetail.evidence.conflicts} /> : emptyModule('No linked data conflicts', 'No conflict record is attached to this compound in the current release.', ShieldCheck)}{sqliteDetail?.stereoReview && <RecordTable title="Huan stereochemistry review" records={[sqliteDetail.stereoReview]} />}</section>;
      default: {
        const reviewed = sqliteDetail?.physicochemical;
        const comparisons = [
          ['Molecular weight', reviewed?.molecular_weight ?? compound.molecularWeight, compound.pubchem?.molecularWeight, 'Da', 2],
          ['cLogP / XLogP', reviewed?.clogp, compound.pubchem?.xlogp, '', 2],
          ['TPSA', reviewed?.tpsa, compound.pubchem?.tpsa, 'A²', 2],
          ['Rotatable bonds', reviewed?.rotatable_bonds, compound.pubchem?.rotatableBondCount, '', 0],
          ['H-bond acceptors', reviewed?.hba, compound.pubchem?.hBondAcceptorCount, '', 0],
          ['H-bond donors', reviewed?.hbd, compound.pubchem?.hBondDonorCount, '', 0],
        ] as const;

        return <section className="sdb-data-section sdb-record-section">
          <DetailSectionTitle eyebrow="Overview" title="Identity, classification, and properties" note="The fields most often needed to identify and compare this compound are kept together." />
          {detailError && <div className="sdb-inline-notice" role="status">SQLite detail unavailable; showing the bundled release snapshot. {detailError}</div>}

          <dl className="sdb-basic-grid">
            <div><dt>Preferred name</dt><dd>{compound.name}</dd></div>
            {(sqliteDetail?.identity?.displayId ?? compound.displayId) && (
              <div><dt>Display ID</dt><dd>{sqliteDetail?.identity?.displayId ?? compound.displayId}</dd></div>
            )}
            {compound.formula && (
              <div><dt>Molecular formula</dt><dd>{compound.formula}</dd></div>
            )}
            {compound.molecularWeight !== null && (
              <div><dt>Molecular weight</dt><dd>{formatNumber(compound.molecularWeight)} Da</dd></div>
            )}
            {compound.formalCharge !== null && compound.formalCharge !== 0 && (
              <div><dt>Formal charge</dt><dd>{formatNumber(compound.formalCharge, 0)}</dd></div>
            )}
            {compound.heavyAtomCount !== null && (
              <div><dt>Heavy atoms</dt><dd>{formatNumber(compound.heavyAtomCount, 0)}</dd></div>
            )}
          </dl>

          <div className="sdb-overview-sweetclass">
            <span>SweetClass</span>
            <div>
              <strong>{classification?.level1 ?? compound.sweetClassLevel1 ?? 'Not available'}</strong>
              <i>→</i>
              <strong>{classification?.level2 ?? compound.sweetClassLevel2 ?? 'Not available'}</strong>
            </div>
            {compound.chemicalClass && <small>External classification: {compound.chemicalClass}</small>}
          </div>

          <div className="sdb-section-divider"><span>Physicochemical properties</span></div>

          {compound.pubchem ? (
            <>
              <div className="sdb-property-comparison">
                <table>
                  <thead>
                    <tr>
                      <th>Property</th>
                      <th>SweetMeta reviewed</th>
                      <th>PubChem</th>
                      <th>Difference</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparisons.map(([label, primary, external, unit, digits]) => {
                      const left = primary === null || primary === undefined ? null : Number(primary);
                      const right = external === null || external === undefined ? null : Number(external);
                      return (
                        <tr key={label}>
                          <th>{label}</th>
                          <td>{left === null ? '—' : `${formatNumber(left, digits)}${unit ? ` ${unit}` : ''}`}</td>
                          <td>{right === null ? '—' : `${formatNumber(right, digits)}${unit ? ` ${unit}` : ''}`}</td>
                          <td>{left === null || right === null ? '—' : formatNumber(left - right, digits)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <>
              <dl className="sdb-property-grid">
                {reviewed?.molecular_weight !== null && reviewed?.molecular_weight !== undefined && (
                  <div><dt>Molecular weight</dt><dd>{formatNumber(reviewed.molecular_weight, 2)} Da</dd></div>
                )}
                {reviewed?.clogp !== null && reviewed?.clogp !== undefined && (
                  <div><dt>cLogP</dt><dd>{formatNumber(reviewed.clogp, 2)}</dd></div>
                )}
                {reviewed?.tpsa !== null && reviewed?.tpsa !== undefined && (
                  <div><dt>TPSA</dt><dd>{formatNumber(reviewed.tpsa, 2)} A²</dd></div>
                )}
                {reviewed?.rotatable_bonds !== null && reviewed?.rotatable_bonds !== undefined && (
                  <div><dt>Rotatable bonds</dt><dd>{formatNumber(reviewed.rotatable_bonds, 0)}</dd></div>
                )}
                {reviewed?.hba !== null && reviewed?.hba !== undefined && (
                  <div><dt>H-bond acceptors</dt><dd>{formatNumber(reviewed.hba, 0)}</dd></div>
                )}
                {reviewed?.hbd !== null && reviewed?.hbd !== undefined && (
                  <div><dt>H-bond donors</dt><dd>{formatNumber(reviewed.hbd, 0)}</dd></div>
                )}
              </dl>
              <p className="sdb-inline-notice">
                PubChem cross-validation unavailable for this compound.
              </p>
            </>
          )}

          <dl className="sdb-property-grid sdb-property-secondary">
            {reviewed?.bertz_complexity !== null && reviewed?.bertz_complexity !== undefined && (
              <div><dt>Bertz complexity</dt><dd>{formatNumber(reviewed.bertz_complexity)}</dd></div>
            )}
            {reviewed?.fraction_csp3 !== null && reviewed?.fraction_csp3 !== undefined && (
              <div><dt>Fraction Csp3</dt><dd>{formatNumber(reviewed.fraction_csp3)}</dd></div>
            )}
            {(reviewed?.heavy_atom_count ?? compound.heavyAtomCount) !== null && (
              <div><dt>Heavy atoms</dt><dd>{formatNumber(reviewed?.heavy_atom_count ?? compound.heavyAtomCount, 0)}</dd></div>
            )}
          </dl>

          <div className="sdb-section-divider"><span>Identifiers and aliases</span></div>
          <div className="sdb-copy-list sdb-basic-identifiers">
            <CopyValue label="Stable ID" value={compound.id} />
            <CopyValue label="InChIKey" value={compound.inchiKey} />
          </div>
          {aliases.length > 0 && (
            <div className="sdb-alias-list">
              <span>Aliases</span>
              <div>
                {aliases.map((alias) => (
                  <button type="button" key={alias} title={`Copy ${alias}`} onClick={() => void navigator.clipboard?.writeText(alias)}>
                    {alias}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="sdb-external-links">
            {externalIds.map((item, index) => {
              const href = externalIdUrl(item.namespace, item.external_id);
              const content = <><span>{item.namespace}</span><strong>{item.external_id}</strong><small>{item.source_id}</small></>;
              return href ? (
                <a key={`${item.namespace}-${item.external_id}-${index}`} href={href} target="_blank" rel="noreferrer">
                  {content}<ExternalLink />
                </a>
              ) : (
                <div key={`${item.namespace}-${item.external_id}-${index}`}>{content}</div>
              );
            })}
          </div>
        </section>;
      }
    }
  };

  return <div className="sdb-page sdb-detail sdb-detail-redesign">
    <button className="sdb-back" onClick={onBack}><ArrowLeft size={17} /> Back to compounds</button>
    <article className="sdb-detail-hero">
      <div className="sdb-detail-identity">
        <div className="sdb-detail-badges">{grade && <span className={`sdb-evidence-badge grade-${grade.toLowerCase()}`}>{grade} provenance</span>}<ReviewBadge compound={compound} />{compound.pubchem?.matchStatus === 'verified' ? <span className="sdb-pubchem-ok"><ShieldCheck size={13} /> PubChem verified</span> : compound.pubchem ? <span className="sdb-discrepancy"><AlertTriangle size={13} /> PubChem discrepancy</span> : null}</div>
        <h1>{compound.name}</h1><p className="sdb-mono">{compound.id}</p>
        {aliases.length > 0 && <p className="sdb-hero-aliases">Also known as {aliases.slice(0, 3).join(' · ')}{aliases.length > 3 ? ` +${aliases.length - 3}` : ''}</p>}
        <div className="sdb-class-tags"><span>{classification?.level1 ?? compound.sweetClassLevel1 ?? 'SweetClass unavailable'}</span><span>{classification?.level2 ?? compound.sweetClassLevel2 ?? 'Subclass unavailable'}</span></div>
        <dl className="sdb-hero-facts">
          {compound.formula && (
            <div><dt>Formula</dt><dd>{compound.formula}</dd></div>
          )}
          {compound.molecularWeight !== null && (
            <div><dt>Molecular weight</dt><dd>{formatNumber(compound.molecularWeight)} Da</dd></div>
          )}
          {casNumbers.length > 0 && (
            <div><dt>CAS</dt><dd>{casNumbers.join(', ')}</dd></div>
          )}
          {pubchemId && (
            <div>
              <dt>PubChem CID</dt>
              <dd>
                <a href={externalIdUrl('PubChemCID', pubchemId) ?? undefined} target="_blank" rel="noreferrer">
                  {pubchemId} <ExternalLink />
                </a>
              </dd>
            </div>
          )}
          {chemblId && (
            <div>
              <dt>ChEMBL ID</dt>
              <dd>
                <a href={externalIdUrl('ChEMBL', chemblId) ?? undefined} target="_blank" rel="noreferrer">
                  {chemblId} <ExternalLink />
                </a>
              </dd>
            </div>
          )}
        </dl>
        {(provenance?.source_collection ?? compound.sourceCollection) && (
          <p className="sdb-hero-source">
            <span>Source collection</span>
            {provenance?.source_collection ?? compound.sourceCollection}
          </p>
        )}
      </div>
      <figure className="sdb-hero-structure"><figcaption>Reviewed 2D structure</figcaption><div><MoleculeImage compound={compound} /></div></figure>
      <div className="sdb-module-strip" role="group" aria-label="Linked data modules">{moduleItems.filter(item => item.count > 0).map((item) => <button type="button" key={item.label} className={`available ${item.warning ? 'warning' : ''}`} onClick={() => selectSection(item.section)}><span>{item.label}</span><strong>{item.count.toLocaleString()}</strong></button>)}</div>
    </article>
    <div className="sdb-record-layout">
      <nav className="sdb-record-nav" aria-label="Compound record sections">
        {DETAIL_SECTIONS.map(({ id, label, icon: Icon, group }, index) => { const showGroup = index === 0 || DETAIL_SECTIONS[index - 1].group !== group; return <div className="sdb-record-nav-item" key={id}>{showGroup && <span className="sdb-record-nav-title">{group}</span>}<button type="button" className={activeSection === id ? 'active' : ''} aria-current={activeSection === id ? 'page' : undefined} onClick={() => selectSection(id)}><Icon /> <span>{label}</span></button></div>; })}
      </nav>
      <div className="sdb-record-content" id={`record-panel-${activeSection}`} aria-live="polite">{renderSection()}</div>
    </div>
  </div>;
};

const mergeSqliteCompound = (base: DatabaseCompound, detail: SweetMetaCompoundDetail): DatabaseCompound => {
  const source = detail.compound as Record<string, unknown>;
  return {
    ...base,
    displayId: source.display_id ? String(source.display_id) : base.displayId,
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
  const [detailState, setDetailState] = useState<{ id: string; data: SweetMetaCompoundDetail | null; error: string | null }>({ id: '', data: null, error: null });
  const sqliteDetail = detailState.id === compoundId ? detailState.data : null;
  const detailError = detailState.id === compoundId ? detailState.error : null;
  useEffect(() => {
    if (!compoundId) return;
    let active = true;
    fetchSweetMetaCompound(compoundId).then((data) => { if (active) setDetailState({ id: compoundId, data, error: null }); }).catch((error: unknown) => { if (active) setDetailState({ id: compoundId, data: null, error: error instanceof Error ? error.message : 'SQLite detail request failed' }); });
    return () => { active = false; };
  }, [compoundId]);
  useEffect(() => { const onPop = () => { const next = initialState(); setRouteState(next); setSection(next.section); setCompoundId(next.compoundId); setQuery(next.query); setTier(next.tier); setMenuOpen(false); }; window.addEventListener('popstate', onPop); return () => window.removeEventListener('popstate', onPop); }, []);
  const resetScroll = () => { const main = document.querySelector<HTMLElement>('.sdb-main'); if (main) main.scrollTop = 0; };
  const navigate = (next: DatabaseSection) => { setSection(next); setCompoundId(null); setQuery(''); setTier('all'); setMenuOpen(false); updateUrl(next, null); setRouteState(initialState()); resetScroll(); };
  const search = (nextQuery: string) => { setSection('compounds'); setCompoundId(null); setQuery(nextQuery); setTier('all'); setMenuOpen(false); updateUrl('compounds', null, { query: nextQuery, tier: 'all' }); setRouteState(initialState()); resetScroll(); };
  const select = (id: string) => { setSection('compounds'); setCompoundId(id); updateUrl('compounds', id, { query, tier }); resetScroll(); };
  const back = () => { setCompoundId(null); updateUrl('compounds', null, { query, tier }); };
  const openStatisticsResult = (values: Record<string, string | number | null | undefined>) => {
    const params = new URLSearchParams({ section: 'compounds' });
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
      <nav className={menuOpen ? 'open' : ''} aria-label="SweetMeta navigation">{SECTIONS.map(({ id, label }) => <button key={id} className={section === id && !compound ? 'active' : ''} onClick={() => navigate(id)}>{label}</button>)}</nav>
      <div className="sdb-header-actions"><button className="sdb-return" onClick={leaveDatabase}><ArrowLeft /> SweetSeek</button><button className="sdb-menu" onClick={() => setMenuOpen((value) => !value)} aria-label={menuOpen ? 'Close database menu' : 'Open database menu'}>{menuOpen ? <X /> : <Menu />}</button></div>
    </header>
    <div className="sdb-mobile-context"><span>{activeLabel}</span><small>{DATABASE_METADATA.totalRecords.toLocaleString()} records</small></div>
    <main className="sdb-main overflow-auto">{compound ? <Detail key={compound.id} compound={sqliteDetail ? mergeSqliteCompound(compound, sqliteDetail) : compound} sqliteDetail={sqliteDetail} detailError={detailError} onBack={back} onSelect={select} /> : section === 'overview' ? <Overview onSelect={select} onSearch={search} onStatistics={() => navigate('statistics')} /> : section === 'compounds' ? <CompoundIndex key={window.location.search} onSelect={select} initialQuery={query} initialTier={tier} initialDrilldown={{ domain: routeState.domain, foodGroup: routeState.foodGroup, sweetnessMinLog10: routeState.sweetnessMinLog10, sweetnessMaxLog10: routeState.sweetnessMaxLog10, qualityMetric: routeState.qualityMetric, qualityState: routeState.qualityState, sweetClassL1: routeState.sweetClassL1, sweetClassL2: routeState.sweetClassL2, evidenceGrade: routeState.evidenceGrade, sourceCollection: routeState.sourceCollection, mwMin: routeState.mwMin, mwMax: routeState.mwMax, clogpMin: routeState.clogpMin, clogpMax: routeState.clogpMax, tpsaMin: routeState.tpsaMin, tpsaMax: routeState.tpsaMax }} /> : section === 'literature' ? <Literature key={window.location.search} onSelect={select} initialYearFrom={routeState.literatureYearFrom} initialYearTo={routeState.literatureYearTo} initialCompoundFamily={routeState.compoundFamily} /> : section === 'statistics' ? <StatisticsDashboard onCompounds={openStatisticsResult} onCompound={select} /> : <Downloads />}</main>
  </div>;
};

export default DatabaseInterface;
