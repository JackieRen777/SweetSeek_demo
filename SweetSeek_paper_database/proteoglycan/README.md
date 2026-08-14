# Proteoglycan knowledge base

Place food protein-polysaccharide PDF papers in `papers/`, then stop the
SweetSeek Gunicorn process and run:

```bash
python scripts/maintenance/update_proteoglycan_index.py
```

The directory lives at `SweetSeek_paper_database/proteoglycan`. The command builds the first index when none exists and adds only new PDFs on
later runs. Generated metadata and index files are intentionally ignored by Git.
