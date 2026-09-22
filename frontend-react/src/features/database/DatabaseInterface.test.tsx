// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
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

beforeEach(() => {
  window.history.replaceState({}, '', '/database');
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => literatureFixture })));
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

  it('keeps molecule assets outside the database route directory', () => {
    render(<DatabaseInterface />);
    const moleculeNames = ['Sucralose', 'Aspartame', 'Stevioside', 'Thiophenesaccharin'];
    const sources = moleculeNames.map((name) =>
      screen.getByRole('img', { name: `${name} structure` }).getAttribute('src'),
    );
    expect(sources.every((source) => source?.startsWith('/database-assets/'))).toBe(true);
  });

  it('shows the complete ECFP4 UMAP map and molecular hover details', () => {
    render(<DatabaseInterface />);
    expect(screen.getByRole('heading', { name: 'ECFP4 Molecular Similarity Landscape' })).toBeTruthy();
    expect(screen.getByRole('button', { name: '2D' }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('button', { name: '3D' }).getAttribute('aria-pressed')).toBe('false');
    expect(screen.getByRole('img', { name: 'ECFP4 UMAP structural similarity map' })).toBeTruthy();
    expect(screen.getByText('1,296 molecules mapped')).toBeTruthy();
    expect(screen.queryByRole('group', { name: 'Color by' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Evidence tiers' })).toBeNull();
    expect(screen.getByText('C1')).toBeTruthy();
    expect(screen.getByText('572 molecules')).toBeTruthy();

    const point = document.querySelector('.sdb-dot');
    expect(point).toBeTruthy();
    if (!point) throw new Error('Expected at least one chemical-space point');
    fireEvent.mouseEnter(point);
    expect(screen.getByText('Molecular formula')).toBeTruthy();
    expect(screen.getByText('Molecular weight')).toBeTruthy();
    expect(screen.getByText('Structural cluster')).toBeTruthy();
    expect(screen.getByText('Evidence tier')).toBeTruthy();
    fireEvent.mouseLeave(point);
    expect(screen.queryByText('Molecular formula')).toBeNull();
  });

  it('passes the homepage query into Browse without exposing unsupported filters', () => {
    render(<DatabaseInterface />);
    expect(screen.queryByRole('combobox', { name: 'Entity type' })).toBeNull();
    expect(screen.queryByRole('combobox', { name: 'Homepage evidence tier' })).toBeNull();
    fireEvent.change(screen.getByRole('textbox', { name: 'Search SweetMeta' }), { target: { value: 'Thiophenesaccharin' } });
    fireEvent.click(screen.getByRole('button', { name: 'Search database' }));
    expect(screen.getByRole('heading', { name: 'Browse the current release' })).toBeTruthy();
    expect(screen.getByRole('textbox', { name: 'Search compounds' })).toHaveProperty('value', 'Thiophenesaccharin');
    expect(screen.getByRole('combobox', { name: 'Evidence tier' })).toHaveProperty('value', 'all');
    expect(screen.getByText('1', { selector: '.sdb-result-meta strong' })).toBeTruthy();
    expect(window.location.search).toContain('q=Thiophenesaccharin');
    expect(window.location.search).not.toContain('tier=');
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

  it('searches the 1,296-record release and opens a compound detail', () => {
    window.history.replaceState({}, '', '/database?section=compounds');
    render(<DatabaseInterface />);
    fireEvent.change(screen.getByRole('textbox', { name: 'Search compounds' }), { target: { value: 'Beryllium chloride' } });
    expect(screen.getByText('1', { selector: '.sdb-result-meta strong' })).toBeTruthy();
    fireEvent.click(screen.getByText('Beryllium chloride'));
    expect(screen.getByRole('heading', { name: 'Beryllium chloride' })).toBeTruthy();
    expect(screen.getByText(/external identifier match exposed a source-field discrepancy/i)).toBeTruthy();
    expect(screen.getByRole('group', { name: 'Structure view' })).toBeTruthy();
    expect(screen.getByRole('navigation', { name: 'Compound record sections' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Overview' }).getAttribute('aria-current')).toBe('page');
    expect(screen.getByRole('heading', { name: 'Evidence and identity status' })).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'ECFP4 structural neighbors' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Similar Compounds' }));
    expect(screen.getByRole('button', { name: 'Similar Compounds' }).getAttribute('aria-current')).toBe('page');
    expect(screen.getByRole('heading', { name: 'ECFP4 structural neighbors' })).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'Evidence and identity status' })).toBeNull();
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

  it('shows core literature on a compound detail without changing R1-R4', async () => {
    window.history.replaceState({}, '', '/database?section=compounds&compound=CMP_CZMRCDWAGMRECN-RDBDAFJKSA-N');
    render(<DatabaseInterface />);
    fireEvent.click(screen.getByRole('button', { name: 'Literature & Evidence' }));
    expect((await screen.findByRole('tab', { name: /Core evidence/ })).getAttribute('aria-selected')).toBe('true');
    expect(await screen.findByText('Sucrose and aspartame sensory response')).toBeTruthy();
    fireEvent.click(screen.getByRole('tab', { name: /Background mentions/ }));
    expect(screen.getByText('Background-only mentions are held in the manual review queue and are not published as formal evidence.')).toBeTruthy();
  });

  it('keeps every public download action disabled', () => {
    window.history.replaceState({}, '', '/database?section=downloads');
    render(<DatabaseInterface />);
    const restricted = screen.getAllByRole('button', { name: /Restricted/i });
    expect(restricted).toHaveLength(3);
    expect(restricted.every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
  });

  it('loads SQLite statistics and drills into the public release', async () => {
    const statisticsFixture = {
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
    expect(screen.getByText('An evidence landscape of sweet compounds, tracing molecular collection, curation, validation, and cross-domain data coverage.')).toBeTruthy();
    expect(screen.getByText('Candidate and needs-review literature links are excluded.', { exact: false })).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'R1 · 189' }));
    expect(await screen.findByRole('heading', { name: 'Browse the current release' })).toBeTruthy();
    expect(new URLSearchParams(window.location.search).get('tier')).toBe('R1');
  });
});
