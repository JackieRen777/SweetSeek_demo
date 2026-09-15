// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import DatabaseInterface from './DatabaseInterface';

beforeEach(() => window.history.replaceState({}, '', '/database'));
afterEach(() => cleanup());

describe('Database portal workflows', () => {
  it('opens the portal homepage and browses the real release', () => {
    render(<DatabaseInterface />);
    expect(screen.getByRole('heading', { name: 'SweetDatabase' })).toBeTruthy();
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

  it('passes the homepage query and evidence tier into Browse', () => {
    render(<DatabaseInterface />);
    fireEvent.change(screen.getByRole('textbox', { name: 'Search SweetDatabase' }), { target: { value: 'Thiophenesaccharin' } });
    fireEvent.change(screen.getByRole('combobox', { name: 'Homepage evidence tier' }), { target: { value: 'R2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Search database' }));
    expect(screen.getByRole('heading', { name: 'Browse the current release' })).toBeTruthy();
    expect(screen.getByRole('textbox', { name: 'Search compounds' })).toHaveProperty('value', 'Thiophenesaccharin');
    expect(screen.getByRole('combobox', { name: 'Evidence tier' })).toHaveProperty('value', 'R2');
    expect(screen.getByText('1', { selector: '.sdb-result-meta strong' })).toBeTruthy();
    expect(window.location.search).toContain('q=Thiophenesaccharin');
    expect(window.location.search).toContain('tier=R2');
  });

  it('publishes the data guide from product navigation', () => {
    render(<DatabaseInterface />);
    fireEvent.click(screen.getByRole('button', { name: 'Data Guide' }));
    expect(screen.getByRole('heading', { name: 'How to read SweetDatabase' })).toBeTruthy();
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
