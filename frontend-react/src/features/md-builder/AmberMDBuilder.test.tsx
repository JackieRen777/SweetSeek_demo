// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AmberMDBuilder from './AmberMDBuilder';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('AmberMDBuilder', () => {
  it('renders the four-step setup and editable protocol controls', () => {
    render(<AmberMDBuilder />);
    expect(screen.getByLabelText('AMBER MD Builder')).toBeTruthy();
    expect(screen.queryByText('Build a reviewable, downloadable simulation workflow.')).toBeNull();
    expect(screen.getByRole('button', { name: 'Single protein' })).toBeTruthy();
    expect(screen.getByLabelText('Production (ns)')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Generate project' })).toBeTruthy();
  });

  it('applies extracted preferences without overwriting manually edited fields', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true, parameters: { temperature_k: 280, simulation_time_ns: 100, salt_molar: 0.15 }, missing_info: ['structure'], needs_clarification: true }),
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<AmberMDBuilder />);
    fireEvent.change(screen.getByLabelText('Temperature (K)'), { target: { value: '315' } });
    fireEvent.change(screen.getByPlaceholderText(/Run a 100 ns simulation/), { target: { value: 'Run 100 ns at 280 K' } });
    fireEvent.click(screen.getByRole('button', { name: 'Apply to parameters' }));
    await waitFor(() => {
      expect((screen.getByLabelText('Temperature (K)') as HTMLInputElement).value).toBe('315');
      expect((screen.getByLabelText('Production (ns)') as HTMLInputElement).value).toBe('100');
      expect((screen.getByLabelText('Salt') as HTMLSelectElement).value).toBe('0.15');
    });
    expect(screen.getByText(/2 preferences applied: production time, salt concentration/)).toBeTruthy();
    const request = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(request.locked_fields).toContain('temperature_k');
  });
});
