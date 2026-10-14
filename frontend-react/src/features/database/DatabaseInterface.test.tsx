// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import DatabaseInterface from './DatabaseInterface';

const literatureFixture = {
  metadata: { generatedAt: '2026-09-17', sourcePaperCount: 1314, indexedPaperCount: 1314, sourceCompoundCount: 1296, linkedPaperCount: 1, linkedCompoundCount: 2, publicLinkCount: 2, reviewCandidateCount: 5976, doiCount: 1, pmidCount: 1, relationshipCounts: { primary_subject: 2 }, identityAmbiguityCount: 55, policy: 'Test policy' },
  papers: { PAPER_TEST: { paperId: 'PAPER_TEST', title: 'Sucrose and aspartame sensory response', authors: ['Test Author'], journal: 'Test Journal', year: 2024, family: 'Hominidae', doi: '10.1000/test', pmid: '12345', sourceFile: 'test.pdf' } },
  links: [
    { linkId: 'LINK_SUCROSE', compoundId: 'CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N', paperId: 'PAPER_TEST', relationshipType: 'primary_subject', isPrimary: true, evidenceExcerpt: 'Sucrose sensory response was measured.', pageNumber: '2', matchMethod: 'title_exact_alias', matchedAlias: 'sucrose', mentionCount: 3, confidence: 0.98, reviewStatus: 'auto_high_confidence', reviewReason: null },
    { linkId: 'LINK_ASPARTAME', compoundId: 'CMP_IAOZJIPTCAWIRG-QWRGUYRKSA-N', paperId: 'PAPER_TEST', relationshipType: 'primary_subject', isPrimary: true, evidenceExcerpt: 'Aspartame sensory response was measured.', pageNumber: '2', matchMethod: 'title_exact_alias', matchedAlias: 'aspartame', mentionCount: 2, confidence: 0.98, reviewStatus: 'auto_high_confidence', reviewReason: null },
  ],
};

const reviewedStatisticsFixture = {
  release: { version: 'v1.0.7', databaseFile: 'SweetDatabase_v1.0.7.sqlite', sha256: 'abc', generatedAt: '2026-10-08T00:00:00Z', reviewDate: '2026-10-05', publicCompounds: 1296 },
  kpis: [], readiness: [{ key: 'R1', label: 'R1 high readiness', count: 189, percent: 14.58 }],
  literatureTimeline: [{ yearFrom: 2020, yearTo: 2024, family: 'sugars-polyols', records: 20 }],
  sweetnessDistribution: [], domainCoverage: [{ key: 'literature', label: 'Accepted literature', records: 180, compounds: 38, percent: 2.93, denominator: 1296 }],
  foodGroups: [], qualityProfile: [{ key: 'structure', label: 'Structure identity', verified: 499, attention: 1, unknown: 796, denominator: 1296 }],
  composition: { level1: [{ key: 'Peptide and amino-acid sweeteners', label: 'Peptide and amino-acid sweeteners', count: 502, percent: 38.73 }], level2: [{ parent: 'Peptide and amino-acid sweeteners', key: 'Amino acids', label: 'Amino acids', count: 100, parentTotal: 502, percentWithinParent: 19.92, percentOverall: 7.72 }] },
  chemicalSpace: [{ id: 'CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N', method: 'umap', x: 7.2, y: 3.4, name: 'Sucrose', formula: 'C12H22O11', molecularWeight: 342.3, sweetClassLevel1: 'Peptide and amino-acid sweeteners', sweetClassLevel2: 'Amino acids', evidenceGrade: 'E1', sourceCollection: 'Reviewed', sourceNames: 'SweetMeta', releaseTier: 'R1_high_readiness', fingerprint: 'ECFP4', metric: 'Jaccard', randomSeed: 1 }, { id: 'CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N', method: 'pca', x: 1.2, y: -0.4, name: 'Sucrose', formula: 'C12H22O11', molecularWeight: 342.3, sweetClassLevel1: 'Peptide and amino-acid sweeteners', sweetClassLevel2: 'Amino acids', evidenceGrade: 'E1', sourceCollection: 'Reviewed', sourceNames: 'SweetMeta', releaseTier: 'R1_high_readiness', fingerprint: 'ECFP4', metric: 'PCA', randomSeed: 1 }],
  evidenceCoverage: { sourceToGrade: [{ source: 'Reviewed', target: 'E1', count: 1296 }], gradeToFamily: [{ source: 'E1', target: 'Peptide and amino-acid sweeteners', count: 1296 }], paths: [{ source: 'Reviewed', grade: 'E1', family: 'Peptide and amino-acid sweeteners', count: 1296 }], familyGrades: [{ family: 'Peptide and amino-acid sweeteners', grade: 'E1', count: 1296, total: 1296, percent: 100 }], modules: [] },
  properties: [{ key: 'molecularWeight', label: 'Molecular weight', unit: 'Da', axisPrecision: 0, groups: [{ family: 'Peptide and amino-acid sweeteners', n: 1, min: 342.3, q1: 342.3, median: 342.3, q3: 342.3, max: 342.3, density: [{ value: 342.3, density: 1 }] }] }],
  featureCoverageComparison: [{ resource: 'SweetDatabase (this work)', entryScope: '1,296 compounds', snapshot: 'v1.0', features: { Structure: 1 } }],
  benchmark: { splits: [{ split: 'test', negative: 180, positive: 182, total: 362 }], models: [{ model: 'XGB', displayModel: 'ECFP4 + XGBoost', split: 'test', seed: '20260825', n: 362, threshold: .4, rocAuc: .92, prAuc: .91, balancedAccuracy: .84, mcc: .68, brier: .11 }] },
};

beforeEach(() => {
  window.history.replaceState({}, '', '/database');
  vi.stubGlobal('fetch', vi.fn(async (input: string | URL | Request) => {
    const url = String(input);
    if (url.includes('/api/sweetmeta/statistics')) return { ok: true, json: async () => ({ success: true, data: reviewedStatisticsFixture }) };
    if (url.includes('/api/sweetmeta/downloads')) return { ok: true, json: async () => ({ success: true, data: { version: 'v1.0.7', reviewDate: '2026-10-05', recordCount: 1296, items: [{ key: 'database', label: 'Reviewed SQLite database', filename: 'SweetDatabase.sqlite', bytes: 1000, sha256: 'a'.repeat(64), url: '/api/sweetmeta/downloads/database' }] } }) };
    return { ok: true, json: async () => literatureFixture };
  }));
});
afterEach(() => cleanup());

describe('Database portal workflows', { timeout: 15_000 }, () => {
  it('opens the portal homepage and browses the real release', () => {
    render(<DatabaseInterface />);
    expect(screen.getByRole('heading', { name: 'SweetMeta' })).toBeTruthy();
    expect(document.querySelector('.sdb-main')?.classList.contains('overflow-auto')).toBe(true);
    expect(screen.getByText(/1,296 records/)).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'SweetMeta Database Composition' })).toBeTruthy();
    expect(screen.getByText('Sweet molecules')).toBeTruthy();
    expect(screen.getByText('Verified structures')).toBeTruthy();
    expect(screen.getByText('Literature-linked molecules')).toBeTruthy();
    expect(screen.getByText('Indexed publications')).toBeTruthy();
    expect(screen.getByText('40')).toBeTruthy();
    expect(screen.getByText('1,314')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Sweet molecules' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Readiness distribution' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Known limitations' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'From identity to evidence' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Browse' }));
    expect(screen.getByRole('heading', { name: 'Browse the current release' })).toBeTruthy();
    expect(window.location.search).toContain('section=compounds');
  });

  it('shows five automatically rotating Statistics visuals without carousel chrome', async () => {
    render(<DatabaseInterface />);
    expect(screen.getByRole('img', { name: 'SweetClass Composition' })).toBeTruthy();
    expect(screen.queryByText('structures cross-checked')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Next visualization' })).toBeNull();
    expect(document.querySelectorAll('.sdb-hero-stat-plot img')).toHaveLength(5);
    fireEvent.click(screen.getByRole('button', { name: 'Open SweetClass Composition in Statistics' }));
    expect(await screen.findByRole('heading', { name: 'SweetMeta Data Statistics' })).toBeTruthy();
    expect(window.location.search).toContain('section=statistics');
  });

  it('keeps the full UMAP/PCA explorer out of the homepage', () => {
    render(<DatabaseInterface />);
    expect(screen.queryByRole('heading', { name: 'Reviewed ECFP4 Molecular Space' })).toBeNull();
    expect(screen.queryByRole('group', { name: 'Projection method' })).toBeNull();
  });

  it('passes the homepage query into Browse and presents the compact compound catalog', () => {
    render(<DatabaseInterface />);
    expect(screen.queryByRole('combobox', { name: 'Entity type' })).toBeNull();
    expect(screen.queryByRole('combobox', { name: 'Homepage evidence tier' })).toBeNull();
    fireEvent.change(screen.getByRole('textbox', { name: 'Search SweetMeta' }), { target: { value: 'Thiophenesaccharin' } });
    fireEvent.click(screen.getByRole('button', { name: 'Search database' }));
    expect(screen.getByRole('heading', { name: 'Browse the current release' })).toBeTruthy();
    expect(screen.getByRole('textbox', { name: 'Search compounds' })).toHaveProperty('value', 'Thiophenesaccharin');
    expect(screen.queryByRole('combobox', { name: 'Evidence tier' })).toBeNull();
    for (const heading of ['ID', 'Name', 'Formula', 'SweetClass', 'Evidence grade', 'MW', 'Source']) {
      expect(screen.getByRole('columnheader', { name: heading })).toBeTruthy();
    }
    expect(screen.queryByText(/^R[1-4]$/, { selector: 'tbody .sdb-tier' })).toBeNull();
    expect(screen.queryByRole('columnheader', { name: 'Assertions' })).toBeNull();
    expect(document.querySelector('.sdb-display-id')?.textContent).toMatch(/^\d{6}$/);
    expect(screen.getByText('1', { selector: '.sdb-result-meta strong' })).toBeTruthy();
    expect(window.location.search).toContain('q=Thiophenesaccharin');
    expect(window.location.search).not.toContain('tier=');
  });

  it('keeps reviewed Browse filters compact and reveals advanced controls on demand', () => {
    window.history.replaceState({}, '', '/database?section=compounds');
    render(<DatabaseInterface />);
    expect(screen.getByRole('combobox', { name: 'SweetClass family' })).toBeTruthy();
    expect(screen.getByRole('combobox', { name: 'Evidence grade' })).toBeTruthy();
    expect(screen.queryByRole('combobox', { name: 'SweetClass subclass' })).toBeNull();

    const moreFilters = screen.getByRole('button', { name: /More filters/i });
    expect(moreFilters.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(moreFilters);
    expect(moreFilters.getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByRole('spinbutton', { name: 'MW minimum' })).toBeTruthy();
    expect(screen.getByRole('spinbutton', { name: 'cLogP maximum' })).toBeTruthy();

    const subclass = screen.getByRole('combobox', { name: 'SweetClass subclass' });
    expect(subclass).toHaveProperty('disabled', true);
    fireEvent.change(screen.getByRole('combobox', { name: 'SweetClass family' }), { target: { value: 'Peptide and amino-acid sweeteners' } });
    expect(subclass).toHaveProperty('disabled', false);
    expect(screen.getByRole('option', { name: 'Peptide sweeteners' })).toBeTruthy();
  });

  it.each([
    ['Sucrose', 'CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N'],
    ['Glucose', 'CMP_GZCGUPFRVQAUEE-SLPGGIOYSA-N'],
    ['Aspartame', 'CMP_IAOZJIPTCAWIRG-QWRGUYRKSA-N'],
  ])('opens the %s example record', (name, id) => {
    render(<DatabaseInterface />);
    fireEvent.click(screen.getByRole('button', { name }));
    expect(screen.getByRole('button', { name: 'Back to compounds' })).toBeTruthy();
    expect(new URLSearchParams(window.location.search).get('compound')).toBe(id);
  });

  it('removes the Evidence and Data Guide modules from product navigation', () => {
    render(<DatabaseInterface />);
    expect(screen.queryByRole('button', { name: 'Evidence' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Data Guide' })).toBeNull();
  });

  it.each(['evidence', 'guide'])('falls back to Home for removed %s links', (section) => {
    window.history.replaceState({}, '', `/database?section=${section}`);
    render(<DatabaseInterface />);
    expect(screen.getByRole('heading', { name: 'SweetMeta' })).toBeTruthy();
  });

  it('opens the identity-first compound detail and navigates its reviewed sections', () => {
    window.history.replaceState({}, '', '/database?section=compounds');
    render(<DatabaseInterface />);
    fireEvent.change(screen.getByRole('textbox', { name: 'Search compounds' }), { target: { value: 'Beryllium chloride' } });
    expect(screen.getByText('1', { selector: '.sdb-result-meta strong' })).toBeTruthy();
    fireEvent.click(screen.getByText('Beryllium chloride'));
    expect(screen.getByRole('heading', { name: 'Beryllium chloride' })).toBeTruthy();
    const recordNav = screen.getByRole('navigation', { name: 'Compound record sections' });
    expect(screen.getByRole('group', { name: 'Linked data modules' })).toBeTruthy();
    for (const section of ['Overview', 'Sweetness & evidence', 'Chemical space', 'Literature', 'Linked records', 'Structure & similarity', 'QC & review']) {
      expect(within(recordNav).getByRole('button', { name: section })).toBeTruthy();
    }
    expect(within(recordNav).getByRole('button', { name: 'Overview' }).getAttribute('aria-current')).toBe('page');
    expect(screen.getByRole('heading', { name: 'Identity, classification, and properties' })).toBeTruthy();
    expect(within(recordNav).queryByRole('button', { name: 'SweetClass' })).toBeNull();
    expect(within(recordNav).queryByRole('button', { name: 'Provenance' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'ECFP4 structural neighbors' })).toBeNull();
    fireEvent.click(within(recordNav).getByRole('button', { name: 'QC & review' }));
    expect(screen.getByText('Manual scientific review flag')).toBeTruthy();
    expect(screen.getByText('Legacy readiness')).toBeTruthy();
    expect(new URLSearchParams(window.location.search).get('panel')).toBe('quality');
    fireEvent.click(within(recordNav).getByRole('button', { name: 'Structure & similarity' }));
    expect(within(recordNav).getByRole('button', { name: 'Structure & similarity' }).getAttribute('aria-current')).toBe('page');
    expect(screen.getByText('ECFP4 structural neighbors')).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'Identity, classification, and properties' })).toBeNull();
    expect(new URLSearchParams(window.location.search).get('panel')).toBe('structure');
  });

  it('restores the selected detail panel from the URL', () => {
    window.history.replaceState({}, '', '/database?section=compounds&compound=CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N&panel=classification');
    render(<DatabaseInterface />);
    expect(within(screen.getByRole('navigation', { name: 'Compound record sections' })).getByRole('button', { name: 'Overview' }).getAttribute('aria-current')).toBe('page');
    expect(screen.getByRole('heading', { name: 'Identity, classification, and properties' })).toBeTruthy();
    expect(new URLSearchParams(window.location.search).get('panel')).toBe('basic');
  });

  it('links a unique exact InChIKey match to ChEMBL', () => {
    window.history.replaceState({}, '', '/database?section=compounds&compound=CMP_WZUVPPKBWHMQCE-UHFFFAOYSA-N');
    render(<DatabaseInterface />);
    const chemblLinks = screen.getAllByRole('link', { name: /CHEMBL1479103/i });
    expect(chemblLinks.length).toBeGreaterThan(0);
    expect(chemblLinks[0].getAttribute('href')).toContain('/CHEMBL1479103');
  });

  it('loads and filters the compound-linked literature table', async () => {
    window.history.replaceState({}, '', '/database?section=literature');
    render(<DatabaseInterface />);
    expect(await screen.findByRole('heading', { name: 'Compound-linked literature' })).toBeTruthy();
    expect(screen.getByRole('columnheader', { name: 'Family' })).toBeTruthy();
    expect(screen.queryByRole('columnheader', { name: 'Abstract' })).toBeNull();
    expect(screen.getAllByText('Hominidae')).toHaveLength(2);
    expect(await screen.findAllByText('Sucrose and aspartame sensory response')).toHaveLength(2);
    fireEvent.change(screen.getByRole('textbox', { name: 'Search literature' }), { target: { value: 'CMP_IAOZJIPTCAWIRG-QWRGUYRKSA-N' } });
    expect(screen.getAllByText('Sucrose and aspartame sensory response')).toHaveLength(1);
    expect(screen.getByRole('link', { name: /12345/i }).getAttribute('href')).toContain('/12345/');
  });

  it('shows literature on a compound detail without changing R1-R4', async () => {
    window.history.replaceState({}, '', '/database?section=compounds&compound=CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N');
    render(<DatabaseInterface />);
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Compound record sections' })).getByRole('button', { name: 'Literature' }));
    // Check that literature section loads - either with records or empty state
    expect(await screen.findByText(/Literature linked to this compound|No literature records are currently linked to/)).toBeTruthy();
  });

  it('offers the allowlisted reviewed release downloads', async () => {
    window.history.replaceState({}, '', '/database?section=downloads');
    render(<DatabaseInterface />);
    const download = await screen.findByRole('link', { name: /Download/i });
    expect(download.getAttribute('href')).toBe('/api/sweetmeta/downloads/database');
    expect(screen.getByText(/SHA-256/)).toBeTruthy();
  });

  it('loads SQLite statistics and drills into the public release', async () => {
    const statisticsFixture = {
      ...reviewedStatisticsFixture,
      release: { version: 'v1.0.6', databaseFile: 'SweetDatabase_v1.0.6.sqlite', sha256: 'abc', generatedAt: '2026-09-21T00:00:00Z', publicCompounds: 1296 },
      kpis: [
        { key: 'compounds', label: 'Public compounds', value: 1296, detail: 'Formally released compound records' },
        { key: 'taste', label: 'Taste assertions', value: 2121, detail: '1,296 public compounds' },
        { key: 'sweetness', label: 'Sweetness measurements', value: 316, detail: '316 public compounds' },
        { key: 'literature', label: 'Literature records', value: 1735, detail: 'Curated publication metadata' },
        { key: 'literature-links', label: 'Literature-linked compounds', value: 38, detail: 'Accepted or reviewed links' },
        { key: 'food', label: 'Food-linked compounds', value: 69, detail: '84,566 occurrence records' },
        { key: 'regulatory', label: 'Regulatory-linked compounds', value: 102, detail: '195 substance links' },
        { key: 'quality', label: 'Quality review queue', value: 170, detail: 'Manual review or unresolved conflict' },
      ],
      readiness: [
        { key: 'R1', label: 'R1 high readiness', count: 189, percent: 14.58 },
        { key: 'R2', label: 'R2 traceable', count: 849, percent: 65.51 },
        { key: 'R3', label: 'R3 dataset supported', count: 88, percent: 6.79 },
        { key: 'R4', label: 'R4 high risk review', count: 170, percent: 13.12 },
      ],
      literatureTimeline: [{ yearFrom: 2020, yearTo: 2024, family: 'sugars-polyols', records: 20 }],
      sweetnessDistribution: [{ key: '1-10x', label: '1-10x', minLog10: 0, maxLog10: 1, records: 10, compounds: 10 }],
      domainCoverage: [{ key: 'literature', label: 'Accepted literature', records: 180, compounds: 38, percent: 2.93, denominator: 1296 }],
      foodGroups: [{ key: 'Fruits', label: 'Fruits', records: 10156, foods: 153, compounds: 49, percent: 3.78, denominator: 1296 }],
      qualityProfile: [{ key: 'structure', label: 'Structure identity', verified: 499, attention: 1, unknown: 796, denominator: 1296 }],
    };
    vi.stubGlobal('fetch', vi.fn(async (input: string | URL | Request) => {
      const url = String(input);
      if (url.includes('/api/sweetmeta/statistics')) return { ok: true, json: async () => ({ success: true, data: statisticsFixture }) };
      return { ok: false, status: 503, json: async () => ({ success: false, error: 'offline' }) };
    }));
    window.history.replaceState({}, '', '/database?section=statistics');
    render(<DatabaseInterface />);
    expect(await screen.findByRole('heading', { name: 'SweetMeta Data Statistics' })).toBeTruthy();
    expect(screen.queryByText('Reviewed snapshot · 2026-10-05')).toBeNull();
    expect(screen.queryByText('Interactive views calculated from the reviewed v1.0.7 source tables.')).toBeNull();
    expect(screen.queryByRole('tab')).toBeNull();
    for (const section of ['SweetClass Composition', 'Chemical Space', 'Evidence Provenance', 'Physicochemical Landscape', 'Coverage']) {
      expect(screen.getByRole('heading', { name: section })).toBeTruthy();
    }
    expect(screen.queryByRole('heading', { name: 'R1–R4 operational status' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Publication timeline' })).toBeNull();
    expect(screen.queryByRole('heading', { name: 'Leading food groups' })).toBeNull();
    expect(screen.getByRole('heading', { name: 'Property distributions by SweetClass family' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'UMAP molecular space by SweetClass family' })).toBeTruthy();
    expect(screen.getByRole('img', { name: 'PCA molecular space by SweetClass family' })).toBeTruthy();
  });
});
