import React, { useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, FileSearch, Minus, Plus, Search, X } from 'lucide-react';
import { GlobalWorkerOptions, getDocument, type PDFDocumentProxy } from 'pdfjs-dist/legacy/build/pdf.mjs';
import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';
import { EventBus, PDFFindController, PDFLinkService, PDFViewer } from 'pdfjs-dist/legacy/web/pdf_viewer.mjs';
import 'pdfjs-dist/legacy/web/pdf_viewer.css';

GlobalWorkerOptions.workerSrc = workerUrl;

const bestSearchExcerpt = (value: string) => {
  const normalized = value.replace(/\s+/g, ' ').replace(/\s+-\s+/g, '').trim();
  const sentence = normalized.split(/(?<=[.!?。！？])\s+/).find((part) => part.length >= 45);
  return (sentence || normalized).slice(0, 180);
};

const PdfViewerPage: React.FC = () => {
  const params = new URLSearchParams(window.location.search);
  const documentId = params.get('document') || '';
  const requestedPage = Math.max(1, Number(params.get('page')) || 1);
  const matchedText = params.get('highlight') || '';
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<HTMLDivElement | null>(null);
  const pdfViewerRef = useRef<PDFViewer | null>(null);
  const eventBusRef = useRef<EventBus | null>(null);
  const [pdf, setPdf] = useState<PDFDocumentProxy | null>(null);
  const [page, setPage] = useState(requestedPage);
  const [scale, setScale] = useState(100);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [evidenceOpen, setEvidenceOpen] = useState(Boolean(matchedText));

  const runFind = (query: string, highlightAll = true) => {
    const eventBus = eventBusRef.current;
    if (!eventBus || !query.trim()) return;
    eventBus.dispatch('find', {
      source: window,
      type: '',
      query,
      phraseSearch: true,
      caseSensitive: false,
      entireWord: false,
      highlightAll,
      findPrevious: false,
      matchDiacritics: false,
    });
  };

  useEffect(() => {
    let disposed = false;
    const container = containerRef.current;
    const viewerElement = viewerRef.current;
    if (!container || !viewerElement || !documentId) {
      setError('文档地址无效');
      setLoading(false);
      return;
    }

    const eventBus = new EventBus();
    const linkService = new PDFLinkService({ eventBus });
    const findController = new PDFFindController({ eventBus, linkService });
    const pdfViewer = new PDFViewer({
      container,
      viewer: viewerElement,
      eventBus,
      linkService,
      findController,
      textLayerMode: 1,
      removePageBorders: false,
    });
    linkService.setViewer(pdfViewer);
    eventBusRef.current = eventBus;
    pdfViewerRef.current = pdfViewer;

    const onPageChanging = ({ pageNumber }: { pageNumber: number }) => setPage(pageNumber);
    const onScaleChanging = ({ scale: nextScale }: { scale: number }) => setScale(Math.round(nextScale * 100));
    eventBus.on('pagechanging', onPageChanging);
    eventBus.on('scalechanging', onScaleChanging);

    const loadingTask = getDocument({ url: `/api/encapsulation/documents/${documentId}/pdf` });
    loadingTask.promise
      .then((loadedPdf) => {
        if (disposed) {
          return;
        }
        setPdf(loadedPdf);
        pdfViewer.setDocument(loadedPdf);
        linkService.setDocument(loadedPdf);
        findController.setDocument(loadedPdf);
        eventBus.on('pagesinit', () => {
          pdfViewer.currentScaleValue = 'page-width';
          pdfViewer.currentPageNumber = Math.min(requestedPage, loadedPdf.numPages);
          setLoading(false);
          const excerpt = bestSearchExcerpt(matchedText);
          if (excerpt) window.setTimeout(() => runFind(excerpt), 350);
        });
      })
      .catch((reason: Error) => {
        if (disposed) return;
        setError(reason.message || 'PDF 加载失败');
        setLoading(false);
      });

    return () => {
      disposed = true;
      eventBus.off('pagechanging', onPageChanging);
      eventBus.off('scalechanging', onScaleChanging);
      void loadingTask.destroy();
      eventBusRef.current = null;
      pdfViewerRef.current = null;
    };
  // The viewer is initialized once from the URL supplied by the citation link.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId]);

  const setCurrentPage = (next: number) => {
    if (!pdfViewerRef.current || !pdf) return;
    pdfViewerRef.current.currentPageNumber = Math.min(Math.max(1, next), pdf.numPages);
  };

  const changeScale = (direction: number) => {
    const viewer = pdfViewerRef.current;
    if (!viewer) return;
    viewer.currentScale = Math.min(3, Math.max(0.5, viewer.currentScale + direction * 0.15));
  };

  return (
    <main className="flex h-screen w-screen flex-col overflow-hidden bg-slate-100 text-slate-800">
      <header className="z-20 flex min-h-14 shrink-0 flex-wrap items-center gap-2 border-b border-slate-200 bg-white px-3 py-2 shadow-sm md:px-5">
        <button onClick={() => window.close()} title="Close" className="flex size-8 items-center justify-center rounded-md hover:bg-slate-100">
          <X size={18} />
        </button>
        <div className="mr-auto flex min-w-0 items-center gap-2 text-sm font-medium">
          <FileSearch size={17} className="shrink-0 text-blue-600" />
          <span className="truncate">Encapsulation PDF</span>
        </div>
        <div className="flex h-8 items-center rounded-md border border-slate-200 bg-white">
          <button onClick={() => setCurrentPage(page - 1)} title="Previous page" className="flex size-8 items-center justify-center hover:bg-slate-50"><ChevronLeft size={16} /></button>
          <input
            value={page}
            onChange={(event) => setPage(Number(event.target.value) || 1)}
            onBlur={() => setCurrentPage(page)}
            onKeyDown={(event) => event.key === 'Enter' && setCurrentPage(page)}
            className="h-full w-10 border-x border-slate-200 text-center text-xs outline-none"
            aria-label="Page number"
          />
          <span className="px-2 text-xs text-slate-400">/ {pdf?.numPages || '-'}</span>
          <button onClick={() => setCurrentPage(page + 1)} title="Next page" className="flex size-8 items-center justify-center hover:bg-slate-50"><ChevronRight size={16} /></button>
        </div>
        <div className="flex h-8 items-center rounded-md border border-slate-200 bg-white">
          <button onClick={() => changeScale(-1)} title="Zoom out" className="flex size-8 items-center justify-center hover:bg-slate-50"><Minus size={15} /></button>
          <button onClick={() => { if (pdfViewerRef.current) pdfViewerRef.current.currentScaleValue = 'page-width'; }} title="Fit width" className="w-12 text-xs text-slate-600 hover:text-blue-600">{scale}%</button>
          <button onClick={() => changeScale(1)} title="Zoom in" className="flex size-8 items-center justify-center hover:bg-slate-50"><Plus size={15} /></button>
        </div>
        <form className="relative hidden md:block" onSubmit={(event) => { event.preventDefault(); runFind(search, false); }}>
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search in PDF" className="h-8 w-44 rounded-md border border-slate-200 pl-8 pr-2 text-xs outline-none focus:border-blue-300" />
        </form>
      </header>

      <div className="relative flex min-h-0 flex-1">
        <div ref={containerRef} className="absolute inset-0 overflow-auto bg-slate-200">
          <div ref={viewerRef} className="pdfViewer" />
        </div>
        {loading && <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-100 text-sm text-slate-500">Loading PDF...</div>}
        {error && <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-100 px-6 text-center text-sm text-red-600">{error}</div>}
        {matchedText && (
          <aside className={`absolute bottom-4 right-4 z-20 w-[min(420px,calc(100%-32px))] rounded-md border border-slate-200 bg-white shadow-xl transition ${evidenceOpen ? '' : 'translate-y-[calc(100%-38px)]'}`}>
            <button onClick={() => setEvidenceOpen((value) => !value)} className="flex h-9 w-full items-center px-3 text-left text-xs font-semibold text-slate-700">
              Matched evidence
            </button>
            <p className="max-h-36 overflow-y-auto border-t border-slate-100 px-3 py-2 text-xs leading-5 text-slate-600">{matchedText}</p>
          </aside>
        )}
      </div>
    </main>
  );
};

export default PdfViewerPage;
