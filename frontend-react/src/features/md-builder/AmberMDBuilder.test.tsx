// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AmberMDBuilder from './AmberMDBuilder';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('AmberMDBuilder', () => {
  it('starts at MD setup when docking is disabled', () => {
    const { container } = render(<AmberMDBuilder />);
    expect(screen.getByLabelText('AMBER MD Builder')).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'Docking' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Run docking' })).toBeNull();
    expect(screen.getByRole('button', { name: '1 MD Setup' })).toBeTruthy();
    expect(screen.queryByText('Describe your simulation')).toBeNull();
    expect(screen.getByRole('button', { name: 'Single protein' })).toBeTruthy();
    expect(screen.getByLabelText('Production (ns)')).toBeTruthy();
    expect(container.querySelector('.mdp-files-panel')?.contains(screen.getByLabelText('Production (ns)'))).toBe(true);
    expect(screen.getByRole('button', { name: 'Generate project' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'MD Expert' })).toBeTruthy();
    expect(screen.getByLabelText('3D structure viewer')).toBeTruthy();
    expect(screen.getByText('Upload a PDB, MOL2, or SDF to view the structure')).toBeTruthy();
  });

  it('applies setup conditions from expert chat without overwriting manually edited fields', async () => {
    render(<AmberMDBuilder />);
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true, answer: 'The requested setup is ready.', intent: 'setup', confidence: 'high', auto_apply: true,
        parameter_updates: { temperature_k: 280, simulation_time_ns: 100, salt_molar: 0.15 }, diagnostic_checks: [],
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    fireEvent.change(screen.getByLabelText('Temperature (K)'), { target: { value: '315' } });
    fireEvent.change(screen.getByLabelText('Ask MD Expert'), { target: { value: 'Set up 100 ns at 280 K with 0.15 M NaCl' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send to MD Expert' }));
    await waitFor(() => {
      expect((screen.getByLabelText('Temperature (K)') as HTMLInputElement).value).toBe('315');
      expect((screen.getByLabelText('Production (ns)') as HTMLInputElement).value).toBe('100');
      expect((screen.getByLabelText('Salt') as HTMLSelectElement).value).toBe('0.15');
    });
    expect(screen.getByText(/2 parameters updated: production time, salt concentration/)).toBeTruthy();
    expect(screen.getByText('The requested setup is ready.')).toBeTruthy();
    const request = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(request.locked_fields).toContain('temperature_k');
  });

  it('requires confirmation before applying troubleshooting suggestions', async () => {
    render(<AmberMDBuilder />);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true, answer: 'Check periodic imaging first.', intent: 'troubleshooting', confidence: 'medium', auto_apply: false,
        parameter_updates: { timestep_fs: 1 }, diagnostic_checks: ['Run cpptraj autoimage.'],
      }),
    }));
    fireEvent.change(screen.getByLabelText('Ask MD Expert'), { target: { value: 'My ligand left the binding site' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send to MD Expert' }));
    expect(await screen.findByText('Run cpptraj autoimage.')).toBeTruthy();
    expect((screen.getByLabelText('Timestep (fs)') as HTMLInputElement).value).toBe('2');
    fireEvent.click(screen.getByRole('button', { name: 'Apply changes' }));
    expect((screen.getByLabelText('Timestep (fs)') as HTMLInputElement).value).toBe('1');
  });
});
