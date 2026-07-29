import { describe, expect, it, vi } from 'vitest';
import { citationMarkdown, citationOrder, citedReferences, doiUrl, openExternalUrl } from './citationUtils';
import type { EncapsulationReference } from './types';

const reference = (id: string): EncapsulationReference => ({
  ref_id: id,
  title: id,
  authors: [],
  journal: '',
  year: '',
  volume: '',
  issue: '',
  pages: '',
  doi: '',
  filename: `${id}.pdf`,
  citation: `${id}[J].`,
  primary_chunk: null,
  chunks: [],
});

const refs = [reference('ref_1'), reference('ref_2'), reference('ref_3')];

describe('encapsulation citation mapping', () => {
  it('numbers references by first appearance and keeps repeated numbers stable', () => {
    const answer = 'First [ref_2], then [ref_1], repeated [ref_2].';
    expect(citationOrder(answer, refs)).toEqual(['ref_2', 'ref_1']);
    expect(citationMarkdown(answer, refs)).toContain('[1](#citation-ref_2)');
    expect(citationMarkdown(answer, refs)).toContain('[2](#citation-ref_1)');
  });

  it('splits grouped citations and ignores uncited references', () => {
    const answer = 'Evidence [ref_3, ref_1].';
    expect(citationMarkdown(answer, refs)).toContain('[1](#citation-ref_3)[2](#citation-ref_1)');
    expect(citedReferences(answer, refs).map((item) => item.reference.ref_id)).toEqual(['ref_3', 'ref_1']);
  });

  it('leaves partial and invalid citation tokens untouched', () => {
    const answer = 'Streaming [ref_1 and invalid [ref_99].';
    expect(citationMarkdown(answer, refs)).toBe(answer);
  });

  it('builds a canonical DOI URL and does not fall back to a local PDF', () => {
    const withDoi = { ...reference('ref_4'), doi: 'https://doi.org/10.1000/example.' };
    expect(doiUrl(withDoi)).toBe('https://doi.org/10.1000/example');
    expect(doiUrl({ ...reference('ref_5'), doi: '10.1016/j.supﬂu.2019.03.011' }))
      .toBe('https://doi.org/10.1016/j.supflu.2019.03.011');
    expect(doiUrl(reference('ref_5'))).toBeNull();
  });

  it('keeps the current page unchanged when the browser blocks a new tab', () => {
    const blockedOpen = vi.fn(() => null);
    expect(openExternalUrl('https://doi.org/10.1000/example', blockedOpen)).toBe('blocked');
    expect(blockedOpen).toHaveBeenCalledWith('https://doi.org/10.1000/example', '_blank');
  });
});
