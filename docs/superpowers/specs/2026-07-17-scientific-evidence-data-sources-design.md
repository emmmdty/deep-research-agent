# Scientific Evidence Data Sources Design

Date: 2026-07-17

Status: approved direction, source design awaiting user review

## 1. Decision

The first product domain is a living research-evidence radar for AI agents,
tool use, and agent evaluation. The product is not a generic paper search or
literature-summary service. It must answer questions about research progress,
experimental comparability, replication, contradiction, and changes since a
previous report.

The data strategy is:

1. use documented scholarly APIs, repositories, and bulk feeds instead of
   crawling search-result pages;
2. maintain a small versioned local corpus for the selected domain;
3. separate publication evidence from metadata, citation, review, and artifact
   enrichment;
4. preserve identifiers, versions, licenses, hashes, and retrieval timestamps;
5. freeze an exact corpus manifest before agents produce a report;
6. let deterministic code own acquisition, deduplication, and versioning while
   agents own screening, evidence extraction, comparison, criticism, and
   synthesis.

This design assumes that the project may later be publicly hosted or used
commercially. Source terms are therefore interpreted conservatively.

## 2. Product Questions the Corpus Must Support

The source system must provide enough evidence to answer questions such as:

- What important agent-evaluation papers appeared in the last 30, 90, or 180
  days?
- Which papers introduce new tasks, datasets, benchmarks, metrics, or agent
  architectures?
- Which reported improvements remain valid when the model, benchmark, tool
  budget, sampling budget, and evaluation protocol are held constant?
- Which claims have been independently replicated, contradicted, or weakened by
  later work?
- Which preprints were later accepted, revised, withdrawn, corrected, or
  retracted?
- Which papers provide usable code, datasets, model weights, and reproducible
  environments?
- What changed since a user's previous report?
- Which evidence supports each important report claim, and where is that
  evidence located in the source document?

Metadata aggregators alone cannot support these answers. Important claims must
ultimately point to a paper, review, official artifact, or other primary source.

## 3. Source Roles

Every connector has exactly one primary role. A source may enrich other fields,
but it must not silently replace a stronger source.

| Role | Purpose | Examples |
| --- | --- | --- |
| Primary publication | Accepted paper or preprint used as claim evidence | ACL Anthology, PMLR, JMLR, TMLR, arXiv |
| Review and decision | Submission state, review, rebuttal, decision | OpenReview |
| Bibliographic identity | DOI, venue, author, title, publication relations | Crossref, DBLP, DataCite |
| Scholarly graph | Citation edges, topics, related works, OA locations | OpenAlex |
| Open-access resolver | Locate a legal accessible copy | OpenAlex OA locations, Unpaywall |
| Research artifact | Code, models, datasets, releases, archived software | GitHub, Hugging Face, Zenodo, Software Heritage, OpenML |
| User corpus | Papers and libraries supplied by a user | PDF, BibTeX, RIS, Zotero export |

## 4. Source Inventory

### 4.1 Primary Sources for the Initial Domain

| Source | Coverage and value | Programmatic access | Update model | Full-text policy | Priority |
| --- | --- | --- | --- | --- | --- |
| arXiv | Fastest coverage of new AI/ML/NLP work; explicit paper versions | OAI-PMH for daily metadata harvest, Atom API for targeted search, and documented bulk-data access | Daily incremental harvest by datestamp; preserve every `vN` | Metadata is CC0. Full-text license varies per paper; store or redistribute only according to the record license | MVP-A |
| ACL Anthology | Accepted ACL-family NLP papers with stable ACL IDs | Official Git repository and Python API over authoritative XML/YAML; stable `.bib`, `.xml`, and `.pdf` URLs | Pull official data repository and process changed records | 2016+ materials are CC BY 4.0; older material has different terms, including non-commercial terms | MVP-A |
| PMLR | ICML, AISTATS, COLT, and other ML proceedings; official BibTeX and PDFs | Static paper pages plus official per-volume Git repositories containing BibTeX and PDFs | Poll volume index or pull changed official volume repositories | PMLR publication agreement grants CC BY 4.0 | MVP-B |
| JMLR | Peer-reviewed machine-learning journal papers | Stable volume indexes, paper pages, `.bib`, and PDF links | Poll current volume index and reconcile by paper ID | Accepted papers grant CC BY 4.0 | MVP-B |
| TMLR | Continuously published ML papers, open reviews, and reproducibility/survey certifications | JMLR accepted-paper index plus OpenReview API and PDFs | Poll accepted-paper index and relevant OpenReview invitations | TMLR submissions and publications are CC BY 4.0 | MVP-B |
| OpenReview | ICLR/TMLR and selected conference submissions, reviews, replies, and decisions | `openreview-py` and API v2; older venues may require API v1 | Increment by venue invitation and note modification time | Store public notes and PDFs according to venue visibility and paper license; do not expose non-public notes | MVP-B |
| NeurIPS Proceedings | Accepted NeurIPS papers and the datasets/benchmarks track | Static annual proceedings, paper pages, BibTeX-like metadata, and PDFs; supplement identity from Crossref/DBLP/OpenAlex | Poll annual/current proceedings and reconcile identifiers | Treat as link-only or internal processing unless the individual paper license permits mirroring | MVP-B |
| CVF Open Access | Accepted CVPR, ICCV, and WACV papers | Static conference indexes and accepted-version PDFs | Poll conference indexes after publication | Publicly readable but copyright remains with authors or other holders; default to link-only/internal processing | Phase 2 |
| AAAI Proceedings | Accepted AAAI-family papers | Official OJS pages and PDFs; metadata enrichment through Crossref/DBLP/OpenAlex | Poll proceedings issue metadata | Default to metadata/link-only unless an item license explicitly permits storage | Phase 2 |
| USENIX/NDSS proceedings | Open systems and security papers relevant to agent security | Official proceedings pages and PDFs | Poll selected conference proceedings | Record and enforce item-level license | Domain extension |
| PMC Open Access Subset | JATS full text for biomedical extensions of agent research | PMC OAI-PMH, E-utilities, BioC API, and approved bulk services | OAI-PMH by datestamp | Only the OA subset and item licenses permit full-text reuse; never bulk-fetch PMC webpages | Domain extension |

Official references:

- [arXiv bulk data and preferred OAI-PMH access](https://info.arxiv.org/help/bulk_data.html)
- [arXiv API terms and metadata/full-text license distinction](https://info.arxiv.org/help/api/tou.html)
- [ACL Anthology development, API, data, and licensing](https://aclanthology.org/info/development/)
- [PMLR proceedings specification](https://proceedings.mlr.press/spec.html)
- [PMLR CC BY 4.0 publication agreement](https://proceedings.mlr.press/pmlr-license-agreement.html)
- [JMLR publication and license policy](https://jmlr.org/author-info.html)
- [TMLR copyright and licensing](https://jmlr.org/tmlr/author-guide.html)
- [OpenReview API version guidance](https://docs.openreview.net/getting-started/using-the-api)
- [NeurIPS proceedings index](https://papers.nips.cc/paper/)
- [CVF Open Access policy](https://openaccess.thecvf.com/)
- [AAAI conference proceedings](https://aaai.org/aaai-publications/aaai-conference-proceedings/)
- [PMC OAI-PMH and automated-retrieval rules](https://pmc.ncbi.nlm.nih.gov/tools/oai/)

### 4.2 Metadata, Identity, and Citation Sources

| Source | Use | Access and licensing | Product rule | Priority |
| --- | --- | --- | --- | --- |
| OpenAlex | Citation graph, topics, abstract index, author/institution IDs, OA locations, retraction flags | REST API plus full snapshot; underlying OpenAlex data is CC0, while API quota/pricing can change | Main scholarly graph and discovery index; never use it as the sole evidence for a paper claim | MVP-A |
| Crossref | DOI metadata, publisher/venue identity, dates, relations, corrections, and updates | Free REST API with etiquette requirements; paid metadata services are available when stronger support is required | Canonical DOI resolver and publication reconciliation | MVP-A |
| DBLP | High-quality computer-science bibliography, author and venue disambiguation | Search API and downloadable metadata; metadata is CC0 | CS-specific identity fallback and venue validation | MVP-A |
| DataCite | Dataset, software, supplement, and research-output DOIs with version/relationship metadata | Public REST API without authentication; annual public CC0 data file | Resolve paper-to-dataset/software relationships | Phase 2 |
| Unpaywall | Legal OA locations for DOI-identified works | REST API with a recommended daily limit; current snapshot data is also available through OpenAlex | Use only as OA-location fallback because OpenAlex already incorporates this role | Phase 2 |
| Semantic Scholar | Citation/related-paper enrichment and experimental retrieval baseline | API and datasets are rate-limited; default license is restrictive for commercial product use | Optional research/evaluation connector only; no production dependency without an expanded license | Optional |
| ORCID | Author identity | Public API subject to its terms and rate limits | Add only when author disambiguation is a demonstrated error source | Later |
| ROR | Institution identity | Open registry and data dump | Normalize affiliations only when needed by a user question | Later |

Official references:

- [OpenAlex API and snapshot](https://developers.openalex.org/)
- [OpenAlex authentication and service limits](https://developers.openalex.org/api-reference/authentication)
- [Crossref REST API etiquette](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/)
- [DBLP CC0 metadata policy](https://dblp.org/faq/1474677.html)
- [DataCite public REST API](https://support.datacite.org/docs/api)
- [DataCite public CC0 data files](https://support.datacite.org/docs/datacite-public-data-file)
- [Unpaywall API](https://unpaywall.org/products/api)
- [Semantic Scholar API license](https://api.semanticscholar.org/license/)

### 4.3 Code, Model, Dataset, and Reproducibility Sources

| Source | Use | Stability and constraints | Priority |
| --- | --- | --- | --- |
| GitHub REST API | Repository metadata, licenses, releases, tags, commit SHA, archived state | Use authenticated polling and conditional requests. Third-party repositories cannot rely on webhooks controlled by this product. Repositories may be deleted or made private | MVP-B |
| Hugging Face Hub API | Models, datasets, Spaces, paper links, model/dataset cards, commit SHA | Use authenticated API, rate-limit headers, and webhooks where appropriate. Hub paper ranking is discovery metadata, not evidence | MVP-B |
| Zenodo | Versioned research artifacts, datasets, software, supplements, DOIs, checksums | REST API, OAI-PMH, and monthly metadata dumps; file license is record-specific | Phase 2 |
| Software Heritage | Durable archived source code and persistent SWHIDs | REST API and archive/vault access; use as fallback when an original repository disappears | Phase 2 |
| OpenML | Reproducible datasets, tasks, flows, runs, predictions, and metrics | Public downloads and API; record item licenses and acknowledge that exact reproduction may still depend on the environment | Phase 2 |
| User-supplied artifacts | Private code, PDFs, experiment logs, and internal benchmarks | User-authorized workspace only; never add to a shared corpus by default | MVP-A |

Official references:

- [GitHub REST API best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)
- [Hugging Face Hub API](https://huggingface.co/docs/hub/en/api)
- [Hugging Face paper APIs](https://huggingface.co/docs/huggingface_hub/en/package_reference/hf_api)
- [Zenodo REST, OAI-PMH, and metadata dumps](https://developers.zenodo.org/)
- [Software Heritage archive and API](https://docs.softwareheritage.org/)
- [OpenML reproducible runs](https://docs.openml.org/concepts/runs/)

### 4.4 Sources That Must Not Be Production Dependencies

| Source | Decision | Reason |
| --- | --- | --- |
| Google Scholar pages | Do not crawl | No supported public search API for this use; blocking and layout changes make it unsuitable for a stable connector |
| ResearchGate/Academia.edu | Do not crawl | Account, copyright, and anti-automation constraints; resolve legal copies through OA sources instead |
| Sci-Hub or other unauthorized mirrors | Prohibited | Copyright and provenance failure |
| Publisher HTML/PDF behind ACM, IEEE, Springer, Elsevier, or other paywalls | Metadata/link-only unless licensed or user supplied | Search availability does not grant automated full-text reuse rights |
| General web search | Discovery fallback only | Results are unstable and cannot independently support a critical scientific claim |
| Papers With Code live site/API | Do not depend on it | The original service and URLs have undergone platform transitions; the old public dump can be used only as a dated seed, not a current truth source |
| ar5iv or third-party PDF-to-HTML mirrors | Parser fallback only | Useful derived renderings but not authoritative publication sources |
| Semantic Scholar summaries/TLDRs | Never cite as paper evidence | Derived text is not the authors' evidence and production licensing is restrictive |

## 5. Delivery Stages

### MVP-A: Stable Corpus Backbone

Implement a complete, testable vertical slice with:

1. arXiv OAI-PMH metadata and version tracking;
2. ACL Anthology official data and permitted full text;
3. OpenAlex discovery/citation enrichment;
4. Crossref DOI reconciliation;
5. DBLP computer-science identity reconciliation;
6. user-supplied PDF/BibTeX import;
7. immutable snapshots and a frozen corpus manifest.

This stage can already produce a scoped research-progress report, but it must
label accepted ACL papers separately from arXiv-only preprints.

### MVP-B: Top-Venue and Artifact Evidence

Add:

1. PMLR and JMLR accepted papers;
2. TMLR and OpenReview submissions/reviews/decisions;
3. NeurIPS accepted-paper reconciliation;
4. GitHub and Hugging Face research artifacts;
5. experiment-fact extraction and comparability review.

MVP-B is the minimum product that can credibly call itself an AI-agent research
evidence radar rather than an arXiv summarizer.

### Phase 2: Coverage and Preservation

Add CVF, AAAI, DataCite, Zenodo, Software Heritage, OpenML, Unpaywall fallback,
and selected domain-specific proceedings. Add PMC only if the product explicitly
expands into biomedical evidence.

## 6. Canonical Data Contracts

### 6.1 SourceDescriptor

Every connector must declare:

```text
source_id
source_role
trust_tier
coverage
official_base_uri
access_method
authentication_mode
rate_limit_policy
incremental_cursor_type
canonical_identifiers
metadata_license
fulltext_license_strategy
storage_policy
redistribution_policy
freshness_sla
fallback_sources
health_probe
parser_name
parser_version
```

### 6.2 WorkRecord

One scholarly work can have several source records and document versions:

```text
work_id
title
authors
abstract
external_ids: arxiv, acl, doi, openreview, dblp, openalex, pmid
publication_status: preprint, submitted, accepted, published, withdrawn, retracted
venue
publication_dates
topics
license
locations
citation_edges
artifact_links
```

### 6.3 DocumentVersion

```text
document_version_id
work_id
source_id
source_native_id
version_label
canonical_uri
published_at
source_updated_at
retrieved_at
content_sha256
media_type
license
storage_policy
parser_version
supersedes
```

### 6.4 Research Evidence Records

Agents write typed records rather than unstructured notes:

```text
EvidenceSpan: document_version_id, page/section, offsets, quote, extraction_method
ClaimRecord: claim, claim_type, evidence_spans, support_status, confidence
ExperimentFact: task, dataset, split, model, baseline, metric, value, budget, protocol
ArtifactRecord: type, URI, version/commit, license, archived_URI, availability_status
ReviewRecord: venue, decision, reviewer_claim, author_response, public_visibility
```

## 7. License-Aware Storage Policy

Each downloaded object receives exactly one storage policy:

| Policy | Meaning | Typical sources |
| --- | --- | --- |
| `mirror_allowed` | Store immutable raw file and parsed text; display with attribution under license | ACL 2016+, PMLR, JMLR, TMLR, appropriately licensed arXiv/PMC papers |
| `internal_processing` | Store privately for product processing but do not redistribute the full document | An item whose terms permit access/processing but not republication |
| `derived_only` | Store metadata, hash, parser output allowed by policy, and short evidence excerpts; discard raw file after processing | Restrictive or uncertain open web documents |
| `link_only` | Store metadata and canonical URL only | Paywalled publisher version or unclear-license proceedings item |
| `user_supplied` | Store in the user's private workspace under their authorization | Uploaded PDF or private artifact |

The Web product displays source links, bibliographic attribution, and the
minimum evidence excerpt needed for verification. It does not become a public
PDF mirror.

## 8. Identity, Deduplication, and Version Resolution

Resolution order:

1. exact persistent identifier match: DOI, ACL ID, OpenReview forum ID, or arXiv
   base ID;
2. explicit `isVersionOf`, `versionOf`, publication relation, or official venue
   link;
3. exact normalized title plus compatible author set;
4. fuzzy title/author/date match as a merge candidate;
5. human review for ambiguous candidates.

Low-confidence matches are never merged automatically. The product keeps:

- arXiv `v1`, `v2`, and later versions as separate `DocumentVersion` records;
- the arXiv preprint and accepted conference version under one `WorkRecord` only
  when the relationship is sufficiently supported;
- submission, accepted manuscript, and publisher version labels;
- withdrawn, corrected, and retracted status history;
- a preferred evidence version without deleting older evidence.

## 9. Incremental Update Flow

```text
scheduled source cursors
        -> discover changed identifiers
        -> fetch metadata and permitted content
        -> hash and deduplicate raw objects
        -> parse changed document versions
        -> resolve work identity and publication state
        -> enrich citations, reviews, and artifacts
        -> validate schema and license policy
        -> publish a new corpus snapshot
        -> freeze CorpusManifest for each report
```

Default cadence:

| Cadence | Sources/actions |
| --- | --- |
| Daily | arXiv OAI-PMH, ACL data pull, selected OpenReview venues, targeted OpenAlex refresh |
| Twice weekly | PMLR/JMLR/TMLR indexes, NeurIPS current proceedings, GitHub/Hugging Face artifacts |
| Weekly | Crossref and DBLP reconciliation, artifact availability checks |
| Monthly | Retraction/correction reconciliation, license audit, connector schema review |
| Report preflight | Refresh only relevant stale sources, then freeze a corpus manifest |

Every cursor is advanced only after the fetched batch is validated and stored.
Runs must be idempotent and resume from the last committed cursor.

## 10. Source Health and Failure Handling

Connector status values:

```text
healthy
unchanged
stale
rate_limited
authentication_failed
schema_changed
license_blocked
partial
unavailable
retired
```

Required behavior:

- An unavailable metadata enricher does not erase previously validated data.
- Failure of a primary source marks affected reports as stale or incomplete.
- A report must disclose the corpus cutoff and unavailable sources.
- arXiv API failure falls back to the local OAI mirror, not webpage scraping.
- ACL website failure falls back to the last validated official data-repository
  snapshot.
- OpenAlex failure falls back to Crossref/DBLP for identity, while citation
  coverage is marked stale.
- OpenReview failure preserves the last public state and blocks claims about a
  newer decision.
- A deleted GitHub repository resolves to Software Heritage when an archived
  version exists.
- A paywalled or license-blocked paper can be requested from the user as a
  private upload; the system must not bypass access controls.

## 11. Agent Boundary

Agents do not autonomously crawl arbitrary sites. The orchestrator gives agents
access to versioned records through typed tools.

Recommended research workers:

1. scope and ontology planner;
2. lexical, semantic, and citation-snowball retrieval workers;
3. screening workers that cite inclusion/exclusion evidence;
4. per-paper evidence and experiment extraction workers;
5. experiment comparability critic;
6. replication and contradiction analyst;
7. synthesis writer;
8. citation and coverage auditor.

Parallel workers operate on independent paper cohorts and return the same
schema. A deterministic reducer resolves duplicates and disagreements. Agent
conversation is not used as the system of record.

## 12. Verification and Acceptance Criteria

Before a connector enters the product path, it must pass:

1. an official-access check showing that the selected API/feed is intended for
   programmatic use;
2. a license fixture covering permitted, restricted, missing, and changed
   licenses;
3. an idempotent two-run incremental-sync test;
4. a cursor resume test after a simulated partial failure;
5. a schema-change fixture and explicit failure state;
6. a provenance test from report claim to exact document version and evidence
   span;
7. a deletion test proving that previously frozen report manifests remain
   reproducible;
8. a rate-limit test proving that retry and backoff do not skip records.

Corpus-level acceptance for the first benchmark set:

- at least 90% discovery coverage on a manually curated 50-work AI-agent seed
  set;
- at least 95% precision for automatic same-work merges, with ambiguous cases
  routed to review;
- 100% of stored full-text objects have a recorded license and storage policy;
- 100% of critical report claims resolve to a source version and evidence span;
- report regeneration from a frozen manifest does not contact external sources;
- source outages produce visible freshness warnings rather than fabricated or
  silently stale conclusions.

These are target acceptance thresholds, not current measured results.

## 13. Verification Snapshot

On 2026-07-17, read-only probes from the development environment successfully
reached arXiv OAI-PMH, the arXiv Atom API, ACL `.bib` and PDF endpoints, PMLR,
NeurIPS proceedings, DBLP API, OpenAlex search, Crossref API, DataCite API,
Zenodo API, and Hugging Face API.

The same probe observed an anonymous OpenReview API `403`, a GitHub anonymous
rate-limit failure in a shared environment, and transient connectivity failures
for JMLR/CVF. These observations are not availability guarantees. They justify
authenticated service accounts, official bulk feeds, local snapshots, health
checks, and explicit fallbacks.

## 14. Explicit Non-Goals

- Mirroring every paper on the internet.
- Claiming systematic-review completeness without a declared search protocol.
- Treating citation count as research quality.
- Treating an arXiv preprint as peer reviewed.
- Redistributing papers without a compatible license.
- Using search-engine snippets or model summaries as scientific evidence.
- Building all source connectors before the MVP-A vertical slice is evaluated.
