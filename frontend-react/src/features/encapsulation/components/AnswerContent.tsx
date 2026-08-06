import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { EncapsulationReference } from '../types';
import { citationMarkdown, citedReferences, doiUrl, openExternalUrl } from '../citationUtils';
import CitationLink from './CitationLink';

interface AnswerContentProps {
  content: string;
  references: EncapsulationReference[];
}

const CitationText: React.FC<{ reference: EncapsulationReference }> = ({ reference }) => {
  const { citation, journal } = reference;
  if (!journal) return <>{citation}</>;
  const journalStart = citation.indexOf(journal);
  if (journalStart < 0) return <>{citation}</>;

  return (
    <>
      {citation.slice(0, journalStart)}
      <em>{journal}</em>
      {citation.slice(journalStart + journal.length)}
    </>
  );
};

const openPublisherPage = (event: React.MouseEvent<HTMLAnchorElement>, url: string) => {
  event.preventDefault();
  openExternalUrl(url);
};

const AnswerContent: React.FC<AnswerContentProps> = ({ content, references }) => {
  const byId = new Map(references.map((reference) => [reference.ref_id, reference]));
  const cited = citedReferences(content, references);
  const markdown = citationMarkdown(content, references);

  return (
    <div className="text-[15px] leading-7 text-slate-700">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
          h1: ({ children }) => <h1 className="mt-6 mb-3 text-xl font-semibold text-slate-900">{children}</h1>,
          h2: ({ children }) => <h2 className="mt-6 mb-3 text-lg font-semibold text-slate-900">{children}</h2>,
          h3: ({ children }) => <h3 className="mt-5 mb-2 text-base font-semibold text-slate-900">{children}</h3>,
          ul: ({ children }) => <ul className="mb-4 list-disc pl-6 space-y-1.5">{children}</ul>,
          ol: ({ children }) => <ol className="mb-4 list-decimal pl-6 space-y-1.5">{children}</ol>,
          strong: ({ children }) => <strong className="font-semibold text-slate-900">{children}</strong>,
          a: ({ href, children }) => {
            const match = href?.match(/^#citation-(ref_\d+)$/);
            const reference = match ? byId.get(match[1]) : undefined;
            if (reference) return <CitationLink number={children} reference={reference} />;
            return <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">{children}</a>;
          },
        }}
      >
        {markdown}
      </ReactMarkdown>

      {cited.length > 0 && (
        <section className="mt-8 border-t border-slate-200 pt-5" aria-label="References">
          <h3 className="mb-3 text-sm font-semibold text-slate-900">参考文献</h3>
          <ol className="space-y-2.5">
            {cited.map(({ number, reference }) => {
              const publisherUrl = doiUrl(reference);
              return (
                <li key={reference.ref_id} className="flex gap-2 text-xs leading-5 text-slate-600">
                  <span className="shrink-0 text-slate-400">[{number}]</span>
                  {publisherUrl ? (
                    <a
                      href={publisherUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(event) => openPublisherPage(event, publisherUrl)}
                      className="hover:text-blue-700 hover:underline"
                    >
                      <CitationText reference={reference} />
                    </a>
                  ) : (
                    <span><CitationText reference={reference} /></span>
                  )}
                </li>
              );
            })}
          </ol>
        </section>
      )}
    </div>
  );
};

export default AnswerContent;
