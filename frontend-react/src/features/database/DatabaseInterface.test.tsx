// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import DatabaseInterface from './DatabaseInterface';

beforeEach(() => window.history.replaceState({}, '', '/database'));
afterEach(() => cleanup());

describe('Database portal workflows', { timeout: 15_000 }, () => {
  it('opens the portal homepage and browses the real release', () => {
    render(<DatabaseInterface />);
    expect(screen.getByRole('heading', { name: 'SweetMeta' })).toBeTruthy();
    expect(document.querySelector('.sdb-main')?.classList.contains('overflow-auto')).toBe(true);
    expect(screen.getByText('1,296')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /Browse entities/i }));
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
    expect(screen.getByRole('heading', { name: 'ECFP4 structural similarity map' })).toBeTruthy();
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

  it('passes the homepage query and evidence tier into Browse', () => {
    render(<DatabaseInterface />);
    fireEvent.change(screen.getByRole('textbox', { name: 'Search SweetMeta' }), { target: { value: 'Thiophenesaccharin' } });
    fireEvent.change(screen.getByRole('combobox', { name: 'Homepage evidence tier' }), { target: { value: 'R2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Search database' }));
    expect(screen.getByRole('heading', { name: 'Browse the current release' })).toBeTruthy();
    expect(screen.getByRole('textbox', { name: 'Search compounds' })).toHaveProperty('value', 'Thiophenesaccharin');
    expect(screen.getByRole('combobox', { name: 'Evidence tier' })).toHaveProperty('value', 'R2');
    expect(screen.getByText('1', { selector: '.sdb-result-meta strong' })).toBeTruthy();
    expect(window.location.search).toContain('q=Thiophenesaccharin');
    expect(window.location.search).toContain('tier=R2');
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

  it('publishes the data guide from product navigation', () => {
    render(<DatabaseInterface />);
    fireEvent.click(screen.getByRole('button', { name: 'Data Guide' }));
    expect(screen.getByRole('heading', { name: 'How to read SweetMeta' })).toBeTruthy();
    expect(screen.getByText('R1–R4 meaning')).toBeTruthy();
  });

  it('searches the 1,296-record release and opens a compound detail', () => {
    window.history.replaceState({}, '', '/database?section=compounds');
    render(<DatabaseInterface />);
    fireEvent.change(screen.getByRole('textbox', { name: 'Search compounds' }), { target: { value: 'Beryllium chloride' } });
    expect(screen.getByText('1', { selector: '.sdb-result-meta strong' })).toBeTruthy();
    fireEvent.click(screen.getByText('Beryllium chloride'));
    expect(screen.getByRole('heading', { name: 'Beryllium chloride' })).toBeTruthy();
    expect(screen.getByText(/matched, with at least one source-field discrepancy/i)).toBeTruthy();
  });

  it('publishes all evidence tiers', () => {
    window.history.replaceState({}, '', '/database?section=evidence');
    render(<DatabaseInterface />);
    expect(screen.getByText('High readiness')).toBeTruthy();
    expect(screen.getByText('Traceable')).toBeTruthy();
    expect(screen.getByText('Dataset supported')).toBeTruthy();
    expect(screen.getByText('High-risk identity')).toBeTruthy();
  });

  it('keeps every public download action disabled', () => {
    window.history.replaceState({}, '', '/database?section=downloads');
    render(<DatabaseInterface />);
    const restricted = screen.getAllByRole('button', { name: /Restricted/i });
    expect(restricted).toHaveLength(3);
    expect(restricted.every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
  });
});
