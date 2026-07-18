# GROBID Deployment Boundary

The Compose profile runs GROBID as a CPU-only parsing service with two visible limits: a 1 GiB JVM heap and two active processors. It is the primary scholarly PDF parser; `DoclingParser` remains the application fallback when GROBID is unavailable or rejects a document.

The API uses the internal URL `http://grobid:8070`. The service is not published to the host. Its `/api/isalive` health probe must pass before the API starts, so parser outages are visible instead of silently changing extraction behavior.

For larger corpora, measure queue time and parser memory on representative PDFs before raising either limit. Do not store private PDFs in the GROBID container; parsed output must return to the tenant-aware corpus service and immutable artifact store.
