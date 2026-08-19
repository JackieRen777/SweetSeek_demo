import React from 'react';
import { ExternalLink } from 'lucide-react';
import type { EncapsulationReference } from '../types';
import { doiUrl, openExternalUrl } from '../citationUtils';

interface CitationLinkProps {
  number: React.ReactNode;
  reference: EncapsulationReference;
}

const CitationLink: React.FC<CitationLinkProps> = ({ number, reference }) => {
  const chunk = reference.primary_chunk;
  const publisherUrl = doiUrl(reference);
  const openPublisherPage = (event: React.MouseEvent<HTMLAnchorElement>) => {
    if (!publisherUrl) return;
    event.preventDefault();
    openExternalUrl(publisherUrl);
  };

  return (
    <span className="relative inline-block align-super text-[0.72em] leading-none group mx-0.5">
      {publisherUrl ? (
        <a
          href={publisherUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={openPublisherPage}
          className="rounded-sm font-semibold text-blue-600 hover:text-blue-800 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-300"
          aria-label={`Open reference ${String(number)} on publisher site`}
        >
          [{number}]
        </a>
      ) : (
        <span className="font-semibold text-slate-500" aria-label={`Reference ${String(number)} has no DOI`}>
          [{number}]
        </span>
      )}
      <span className="pointer-events-none invisible opacity-0 group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100 transition-opacity absolute z-50 left-1/2 -translate-x-1/2 bottom-full mb-2 w-[min(360px,calc(100vw-32px))] rounded-md border border-slate-200 bg-white p-3 text-left normal-case tracking-normal shadow-xl">
        <span className="block text-xs font-semibold leading-5 text-slate-800">{reference.citation}</span>
        <span className="mt-2 block border-t border-slate-100 pt-2 text-[11px] font-medium leading-4 text-slate-500">
          Matched evidence{chunk?.page ? ` · Page ${chunk.page}` : ''}
        </span>
        <span className="mt-1 block max-h-28 overflow-hidden text-xs font-normal leading-5 text-slate-600">
          {chunk?.text || 'No matched text block is available for this reference.'}
        </span>
        <span className={`mt-2 flex items-center gap-1 text-[11px] font-medium ${publisherUrl ? 'text-blue-600' : 'text-slate-400'}`}>
          {publisherUrl ? <>View publisher page <ExternalLink size={11} /></> : 'DOI unavailable'}
        </span>
      </span>
    </span>
  );
};

export default CitationLink;
