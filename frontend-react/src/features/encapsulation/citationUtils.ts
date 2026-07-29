import type { EncapsulationReference } from './types';

type OpenedWindow = { opener: unknown };
type OpenWindow = (url: string, target: string) => OpenedWindow | null;

const CITATION_GROUP = /\[((?:ref_\d+)(?:\s*,\s*ref_\d+)*)\]/g;

export function citationOrder(content: string, references: EncapsulationReference[]): string[] {
  const valid = new Set(references.map((reference) => reference.ref_id));
  const order: string[] = [];
  for (const match of content.matchAll(CITATION_GROUP)) {
    for (const id of match[1].split(',').map((value) => value.trim())) {
      if (valid.has(id) && !order.includes(id)) order.push(id);
    }
  }
  return order;
}

export function citationMarkdown(content: string, references: EncapsulationReference[]): string {
  const order = citationOrder(content, references);
  const numbers = new Map(order.map((id, index) => [id, index + 1]));
  return content.replace(CITATION_GROUP, (original, group: string) => {
    const links = group
      .split(',')
      .map((value) => value.trim())
      .filter((id) => numbers.has(id))
      .map((id) => `[${numbers.get(id)}](#citation-${id})`);
    return links.length ? links.join('') : original;
  });
}

export function citedReferences(
  content: string,
  references: EncapsulationReference[],
): Array<{ number: number; reference: EncapsulationReference }> {
  const byId = new Map(references.map((reference) => [reference.ref_id, reference]));
  return citationOrder(content, references).flatMap((id, index) => {
    const reference = byId.get(id);
    return reference ? [{ number: index + 1, reference }] : [];
  });
}

export function doiUrl(reference: EncapsulationReference): string | null {
  const doi = reference.doi
    .normalize('NFKC')
    .trim()
    .replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '')
    .replace(/^doi\s*:\s*/i, '')
    .replace(/[.,;\s]+$/, '');
  return doi ? encodeURI(`https://doi.org/${doi}`) : null;
}

export function openExternalUrl(
  url: string,
  openWindow: OpenWindow = (targetUrl, target) => window.open(targetUrl, target),
): 'new-tab' | 'blocked' {
  const opened = openWindow(url, '_blank');
  if (opened) {
    opened.opener = null;
    return 'new-tab';
  }
  return 'blocked';
}
