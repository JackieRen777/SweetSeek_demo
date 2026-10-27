# Website usage counters

The self-hosted counter uses SQLite and requires no external analytics account.
It starts counting when the updated frontend and backend are running together;
it does not reconstruct historical traffic.

## Counting rules

- A full page load or refresh records one visit. Navigating between SweetSeek
  features does not record another visit. This is page loads, not unique people.
- Sending a nonempty question records one submission, including Enter-to-send,
  in sweetness, dual-protein, encapsulation and proteoglycan Q&A.
- Blank submissions, filling a suggested question, stopping an answer, answer
  stream chunks and automatic knowledge-base retries do not add submissions.
- A question is counted when submitted, even if the answer fails or is stopped.
- Every event has a random ID. Delivery retries reuse that ID and are counted once.
- Only the ID, event kind, knowledge domain and server-assigned date are stored.
  No question text, answer text, IP address, account or persistent visitor ID is
  stored by this counter. Existing application/access logs are separate.
- Daily counts use Asia/Shanghai. Automated browsers may count as visits; this
  lightweight counter is an operational estimate, not an audited traffic service.
- Delivery is retried once and never delays Q&A. If the backend stays unavailable
  or the browser blocks delivery, the event can be lost.

## Viewing statistics

Statistics are currently hidden from the website at the owner's request. Page
loads and question submissions continue to be recorded. Query the summary when
the owner asks for the counts; public display can be restored later on request.
The unused `UsageCounter` component is retained for that future change.
`GET /api/usage/summary` returns cumulative and daily counts plus per-domain Q&A
counts. Only aggregate counters are public. `POST /api/usage/events` accepts a
small JSON object containing `id` (UUID), `event` and `domain`.

## Persistence

Local development defaults to `runtime/usage.sqlite3`, excluded from Git. Set
`USAGE_ANALYTICS_DB_PATH` to override the path. Local and production data are
separate. The Git deploy script provisions a writable shared directory and sets
`USAGE_ANALYTICS_DB_PATH=$BASE/shared/analytics/usage.sqlite3`, so deployments and
backend restarts preserve the counts. For other deployment methods, set an
equivalent persistent path outside the release directory and allow the backend
user to write its parent directory. Back up this database with other runtime data.

Frontend-only deployment does not enable the API; restart/deploy the backend too.
No additional Python or Node dependencies are needed.
