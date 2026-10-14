import { useState, useMemo } from 'react';
import { ExternalLink, ArrowUpDown, Search, Download, Tag } from 'lucide-react';
import type { LiteratureData, CompoundPaperLink } from '../literature';
import { RELATIONSHIP_LABELS } from '../literature';

interface LiteratureTableProps {
  links: CompoundPaperLink[];
  papers: LiteratureData['papers'];
  compoundName: string;
}

type SortField = 'title' | 'journal' | 'year' | 'pmid' | 'doi';

const LiteratureTable = ({ links, papers, compoundName }: LiteratureTableProps) => {
  const [sortField, setSortField] = useState<SortField>('year');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [showRelationships, setShowRelationships] = useState(false);
  const pageSize = 10;

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection(field === 'year' ? 'desc' : 'asc');
    }
    setPage(1);
  };

  const sortedLinks = useMemo(() => {
    // First filter by search query
    let filtered = links;
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = links.filter((link) => {
        const paper = papers[link.paperId];
        if (!paper) return false;
        return (
          paper.title.toLowerCase().includes(query) ||
          (paper.journal || '').toLowerCase().includes(query) ||
          (paper.pmid || '').toLowerCase().includes(query) ||
          (paper.doi || '').toLowerCase().includes(query)
        );
      });
    }

    // Then sort
    return [...filtered].sort((a, b) => {
      const paperA = papers[a.paperId];
      const paperB = papers[b.paperId];

      if (!paperA || !paperB) return 0;

      let comparison = 0;

      switch (sortField) {
        case 'title':
          comparison = paperA.title.localeCompare(paperB.title);
          break;
        case 'journal':
          comparison = (paperA.journal || '').localeCompare(paperB.journal || '');
          break;
        case 'year':
          comparison = (paperA.year || 0) - (paperB.year || 0);
          break;
        case 'pmid':
          comparison = (paperA.pmid || '').localeCompare(paperB.pmid || '');
          break;
        case 'doi':
          comparison = (paperA.doi || '').localeCompare(paperB.doi || '');
          break;
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [links, papers, sortField, sortDirection, searchQuery]);

  const pageCount = Math.max(1, Math.ceil(sortedLinks.length / pageSize));
  const visibleLinks = sortedLinks.slice((page - 1) * pageSize, page * pageSize);

  const handleExport = () => {
    const csvRows = [
      ['Title', 'Journal', 'Year', 'PMID', 'DOI', 'Relationship'].join(','),
      ...sortedLinks.map((link) => {
        const paper = papers[link.paperId];
        if (!paper) return '';
        return [
          `"${paper.title.replace(/"/g, '""')}"`,
          `"${(paper.journal || '').replace(/"/g, '""')}"`,
          paper.year || '',
          paper.pmid || '',
          paper.doi || '',
          `"${RELATIONSHIP_LABELS[link.relationshipType] || ''}"`
        ].join(',');
      })
    ];
    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${compoundName}_literature.csv`);
    link.click();
    URL.revokeObjectURL(url);
  };

  const SortButton = ({ field, label }: { field: SortField; label: string }) => (
    <button
      type="button"
      className={`sdb-sort-btn ${sortField === field ? 'active' : ''}`}
      onClick={() => handleSort(field)}
      aria-sort={sortField === field ? (sortDirection === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      <span>{label}</span>
      <ArrowUpDown size={13} />
    </button>
  );

  if (links.length === 0) {
    return (
      <div className="sdb-literature-empty">
        <p>No literature records are currently linked to {compoundName}.</p>
        <small>Literature links are curated from the SweetSeek corpus and require evidence-based validation.</small>
      </div>
    );
  }

  return (
    <div className="sdb-literature-table-section">
      <div className="sdb-literature-header">
        <h3>Literature linked to this compound</h3>
        <p>{links.length} literature {links.length === 1 ? 'record' : 'records'} linked to {compoundName}.</p>
      </div>

      <div className="sdb-literature-controls">
        <div className="sdb-search-box">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search by title, journal, PMID, or DOI..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setPage(1);
            }}
          />
          {searchQuery && (
            <button
              className="sdb-search-clear"
              onClick={() => setSearchQuery('')}
              title="Clear search"
            >
              ×
            </button>
          )}
        </div>
        <div className="sdb-literature-actions">
          <button
            className="sdb-toggle-relationships"
            onClick={() => setShowRelationships(!showRelationships)}
            title={showRelationships ? 'Hide relationship types' : 'Show relationship types'}
          >
            <Tag size={14} />
            {showRelationships ? 'Hide' : 'Show'} relationships
          </button>
          <button
            className="sdb-export-btn"
            onClick={handleExport}
            title="Export as CSV"
          >
            <Download size={14} />
            Export CSV
          </button>
        </div>
      </div>

      {sortedLinks.length === 0 && searchQuery ? (
        <div className="sdb-literature-empty">
          <p>No literature found matching "{searchQuery}"</p>
          <small>Try different keywords or clear the search to see all records.</small>
        </div>
      ) : (
        <>
          <div className="sdb-table-wrap sdb-literature-evidence-table-wrap">
            <table className="sdb-table sdb-literature-evidence-table">
              <thead>
                <tr>
                  <th><SortButton field="title" label="Article Title" /></th>
                  <th><SortButton field="journal" label="Journal" /></th>
                  <th><SortButton field="year" label="Year" /></th>
                  <th><SortButton field="pmid" label="PubMed ID" /></th>
                  <th><SortButton field="doi" label="DOI" /></th>
                </tr>
              </thead>
              <tbody>
                {visibleLinks.map((link) => {
                  const paper = papers[link.paperId];
                  if (!paper) return null;

                  return (
                    <tr key={link.linkId}>
                      <td className="sdb-lit-title-cell">
                        <strong>{paper.title}</strong>
                        {showRelationships && link.relationshipType && (
                          <span className="sdb-relationship-tag">
                            <Tag size={12} />
                            {RELATIONSHIP_LABELS[link.relationshipType] || link.relationshipType}
                          </span>
                        )}
                        {link.evidenceExcerpt && (
                          <small className="sdb-lit-excerpt">{link.evidenceExcerpt}</small>
                        )}
                      </td>
                      <td>{paper.journal || <span className="sdb-muted">—</span>}</td>
                      <td>{paper.year || <span className="sdb-muted">—</span>}</td>
                      <td>
                        {paper.pmid ? (
                          <a
                            href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/`}
                            target="_blank"
                            rel="noreferrer"
                            className="sdb-external-link"
                          >
                            {paper.pmid} <ExternalLink size={12} />
                          </a>
                        ) : (
                          <span className="sdb-muted">—</span>
                        )}
                      </td>
                      <td>
                        {paper.doi ? (
                          <a
                            href={`https://doi.org/${paper.doi}`}
                            target="_blank"
                            rel="noreferrer"
                            className="sdb-external-link"
                          >
                            <ExternalLink size={12} /> View
                          </a>
                        ) : (
                          <span className="sdb-muted">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {pageCount > 1 && (
            <div className="sdb-pagination">
              <button
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </button>
              <span>
                Page {page} of {pageCount}
                {searchQuery && ` (${sortedLinks.length} results)`}
              </span>
              <button
                disabled={page >= pageCount}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default LiteratureTable;
