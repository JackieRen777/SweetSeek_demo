# SweetSeek paper database

This directory contains the source literature for each independent RAG domain.
PDF files and generated metadata are local runtime data and are not committed to
Git. Vector indexes remain in their existing `faiss_db` or `storage_*`
directories outside this database.

Set `PAPER_DATABASE_ROOT` to this directory locally. Production deployments use
`/data/sweetseek/SweetSeek_paper_database` so code releases cannot overwrite the
paper collection.
