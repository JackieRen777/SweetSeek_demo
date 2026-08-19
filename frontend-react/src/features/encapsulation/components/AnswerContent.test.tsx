// @vitest-environment jsdom

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import AnswerContent from './AnswerContent';
import type { EncapsulationReference } from '../types';

const reference: EncapsulationReference = {
  ref_id: 'ref_8',
  title: 'Protein-polysaccharide encapsulation systems',
  authors: ['Smith J', 'Lee K', 'Wang P', 'Garcia M'],
  journal: 'Food Chemistry',
  year: '2024',
  volume: '10',
  issue: '2',
  pages: '20-30',
  doi: '10.1000/example',
  filename: 'paper.pdf',
  citation: 'Smith J, Lee K, Wang P, et al. Protein-polysaccharide encapsulation systems[J]. Food Chemistry, 2024, 10(2): 20-30.',
  primary_chunk: {
    chunk_id: 'chunk-8',
    page: 4,
    text: 'Matched evidence about protein and polysaccharide wall materials.',
    score: 0.8,
    rank: 1,
  },
  chunks: [],
};

describe('AnswerContent', () => {
  it('renders a superscript citation, evidence preview, and clickable bibliography', () => {
    const popup = { opener: window } as unknown as Window;
    const open = vi.spyOn(window, 'open').mockImplementation(() => popup);
    render(<AnswerContent content="Evidence-based answer [ref_8]." references={[reference]} />);

    const inlineLink = screen.getByLabelText('Open reference 1 on publisher site');
    expect(inlineLink.getAttribute('href')).toBe('https://doi.org/10.1000/example');
    expect(inlineLink.getAttribute('target')).toBe('_blank');
    fireEvent.click(inlineLink);
    expect(open).toHaveBeenCalledWith('https://doi.org/10.1000/example', '_blank');
    expect(popup.opener).toBeNull();
    expect(screen.getAllByText(reference.citation).length).toBeGreaterThan(0);
    expect(screen.getByText((_, element) => element?.textContent === 'Matched evidence · Page 4')).toBeTruthy();
    expect(screen.getByText(reference.primary_chunk!.text)).toBeTruthy();
    expect(screen.getByRole('heading', { name: '参考文献' })).toBeTruthy();
    const journal = screen.getByText(reference.journal);
    expect(journal.tagName).toBe('EM');
    expect(journal.closest('a')?.getAttribute('href')).toBe('https://doi.org/10.1000/example');
    fireEvent.click(journal.closest('a')!);
    expect(open).toHaveBeenCalledTimes(2);
    expect(screen.getByText('View publisher page')).toBeTruthy();
    open.mockRestore();
  });
});
