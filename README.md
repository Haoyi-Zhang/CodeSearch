# Continuation certificates for federated code search

This repository is a bounded, offline-reproducible prototype for exact **standing** top-k queries over asynchronously indexed code shards. It preserves the adverse one-shot result: fetching a stale prefix plus a change suffix for every cold query is safe but uses 2.15× the source bytes of exact delta overlay. The positive mechanism instead keeps validated query-specific state at the coordinator and advances it over a shared, query-independent event feed.

A continuation token stores a bounded candidate buffer and a conservative rank-key lower bound for every omitted live result. Complete replacement events remove dirty rows, add final positive assignments, and update the tail without consulting an index. Only a shard whose tail can still cross the global top-k threshold is repaired. An independently implemented stateful checker validates bindings, event continuity, score arithmetic, token transitions, repairs, merge order, and status. Local prefix completeness remains a trusted crash-model obligation; retained-history replay checks every supplied receipt but is not a Byzantine proof.

## Primary generated-churn result

The primary campaign contains nine cases × two prespecified seeds × 63 ticks × four active queries = 4,536 observations per policy. It uses 16 standing queries, `k=L=5`, six logical loopback endpoints in one process, and deterministic churn over 2,071 initially indexed function bodies.

| Policy | Exact | Justified complete | False complete | Unsound rows | Source bytes/query | Messages/query | Max logical state |
|---|---:|---:|---:|---:|---:|---:|---:|
| Continuation | 4,340 | 4,248 | 0 | 0 | 353.842 | 1.861 | 60,078 B |
| Stateless exact overlay | 4,340 | 4,248 | 0 | 0 | 2,157.174 | 6.071 | 0 B |
| Cut-aware result cache | 4,340 | 4,248 | 0 | 0 | 2,076.886 | 5.852 | 18,237 B |
| Full coordinator mirror | 4,340 | 4,248 | 0 | 0 | 729.109 | 1.443 | 1,735,030 B |
| Unsafe stale | 2,626 | 4,536 claimed | 1,910 | 2,075 | 0 | 0 | 17,517 B |

Continuation reduces source bytes by 83.60% versus overlay, 82.96% versus cut-cache, and 51.47% versus the mirror. It executes 48 actual blocker repairs. The mirror sends fewer messages but retains 28.88× more logical state; cut-cache retains less state but sends 5.87× more source bytes. All safe policies expose the same failure-closed boundary: 4,248 responses are justified complete, 92 more match the oracle only in hindsight, and 196 are otherwise partial or rank-underdetermined.

## Held-out published-history and process validation

A separate validation starts from the exact retained cachetools v7.1.4 module and applies all six published commits through the observed v7.1.8 head interval that change or add a Python function body in that module. Seven function assignments become six ordered replacement events, with a frozen digest after every projected stage. This is a function-level trace, not complete Git snapshots.

The campaign runs all 64 disjoint corpus query seeds plus four deterministic change-targeted plans after each commit: 408 observations per policy. The six source replicas are six distinct OS child processes on one host. One is terminated after commit three; a fresh process with a new PID starts from the base, replays the history, and converges with all five peers and the independent oracle. A both-owner outage probe returns partial and refuses overlay completeness, then heals to the exact complete answer.

| Policy | Exact / complete | False complete | Unsound rows | Source bytes/query | Messages/query | Max logical state |
|---|---:|---:|---:|---:|---:|---:|
| Continuation | 408 | 0 | 0 | 400.069 | 1.029 | 145,912 B |
| Exact overlay | 408 | 0 | 0 | 2,193.613 | 6.000 | 0 B |
| Cut-aware cache | 408 | 0 | 0 | 1,014.544 | 2.667 | 75,176 B |
| Unsafe stale | 386 | 22 | 21 | 0 | 0 | — |

Continuation uses 81.76% fewer source bytes than overlay and 60.57% fewer than cut-cache. Independent analysis reconstructs 1,991 delivered source receipts and all policy/checker transitions. Only ten query/commit observations change the oracle, so the unsafe control and four frozen targeted plans are material to the validation. The trace remains deterministic, single-module, single-host, and not a user query log.

## Retained cold-query negative result

The earlier one-shot campaign contains 1,008 observations per policy. Prefix repair and exact overlay both return 969 oracle-equal and 936 justified-complete responses with zero false completeness or unsound rows, but prefix repair uses 4,673.661 versus 2,173.183 source bytes/query. A first invocation should therefore use overlay; continuation is a standing-query reuse mechanism, not a universal certificate advantage.

## Reproduction

Requirements: Linux/POSIX, Python 3.10+ with assertions enabled, loopback TCP, `/usr/bin/time`, and `prlimit`; no third-party Python package, network download, GPU, account, or external service is required. Included upstream source files are parsed as text and never imported or executed. Use a disposable extraction because results are regenerated.

Primary continuation packet:

```sh
python run_continuation_suite.py
```

The clean four-stage run executes 43 unit tests, 220,997 finite instances, 26 trace jobs (18 primary plus eight development traces), and independent replay. Stages are sequential; only the trace batch uses at most two independent workers. Each child has a 3 GiB address-space limit and the suite has a 170-second deadline. The exact host-specific time, CPU, and RSS record is retained in `results/continuation-clean-reproduction.json`; semantic and wire outcomes are checked against the frozen contract.

Held-out history/process packet:

```sh
python run_real_history_suite.py
```

The clean three-stage run checks four directed history tests, the six-process campaign, and independent replay under a 90-second deadline and 4 GiB child address-space bound. Its exact host-specific resource record is `results/real-history-clean-reproduction.json`.

Retained one-shot packet:

```sh
python run_suite.py
```

The retained run executes 36 commands under a 180-second deadline, with at most three trace workers. Its exact host-specific resource record is `results/clean-reproduction.json`.


Complete sequential gate:

```sh
python run_all_validation.py
```

This runs the three suites above, regenerates the resource ledger with `refresh_resource_ledger.py`, and then executes `validate_release.py`. The validator checks 26 material claim/evidence rows, all frozen result invariants and negative controls, the retained input and Git-history contracts, package hygiene, and the 67-record reference ledgers without network access. In the full project, `python validate_release.py --paper-dir ../paper --project-root ..` also requires exact agreement among every manuscript citation, BibTeX record, rendered bibliography item, audit row, and verification row.

Useful focused commands:

```sh
python -m unittest discover -s tests -v
python finite_continuation.py
python continuation_campaign.py --case rank-churn --seed 2 --active 4 --capacity 5
python analyze_continuation.py
python real_history_campaign.py
python analyze_real_history.py
python finite.py
python reproduce.py --case index-lag --seed 2
python analyze.py
```

## Repository map

- `src/continuation.py`: token invariant, advancement, merge, blocker diagnosis, and `k+d` repair bound.
- `src/continuation_coordinator.py`: shared feed, token sessions, selective repairs, and compaction.
- `src/continuation_checker.py`: independent stateful checker with no coordinator/producer import.
- `src/service.py`: primary six-logical-endpoint loopback service.
- `src/process_service.py`: one source replica per OS process, termination, restart, and loopback RPC.
- `src/real_history.py`: pinned function-level commit projection and deterministic validation queries.
- `continuation_campaign.py`, `continuation_batch.py`, `analyze_continuation.py`: generated-churn campaign, bounded driver, and independent replay.
- `real_history_campaign.py`, `analyze_real_history.py`, `run_real_history_suite.py`: held-out published-history/process validation.
- `finite_continuation.py`: 220,997 finite transition, repair, and merge checks.
- `proofs/model.md`: assumptions, lemmas, theorems, counterexamples, and limits.
- `inputs/git-history/cachetools-function-history.json`: pinned commit metadata, exact function operations, and stage digests.
- `docs/real-history-provenance.md`: selection rule, provenance, query scope, and non-claims.
- `results/`: raw compressed traces, independent analyses, frozen summaries, and clean reproduction logs.
- `docs/`: claim/evidence, literature, 67-entry reference audit and record-verification ledgers, resource, provenance, and trust ledgers.
- `refresh_resource_ledger.py`: regenerates the resource record directly from the three clean-run JSON reports and retained logs.
- `validate_release.py`: offline closure check for evidence paths, exact result invariants, references, inputs, history, generated manuscript values (when the paper is present), and package hygiene.
- `run_all_validation.py`: sequential release gate for all public suites, ledger regeneration, and final validation.
- `inputs/`: 107 retained public-source files and upstream notices.

## Scope and exclusions

The primary corpus contains 2,135 extracted Python function bodies from eight licensed source distributions; 2,071 seed the indexes and 64 disjoint bodies seed queries. Its updates and activation schedule are generated. The held-out validation uses six published function-changing commits, but only as a verified function-level projection over one module; it is not a repository-wide history or observed query stream.

Ranking is maximum overlap with one or two frozen AST-label alternatives. It is not semantic search, FaCoY, TF-IDF, BM25, Lucene, or learned retrieval. The primary harness shares a process; the held-out harness uses separate processes but still one host and loopback. Neither supplies disk durability, multi-host failure isolation, WAN/TLS/backpressure, or production throughput. The vector cut is writer-declared rather than transactional, causally closed, or necessarily wall-clock latest. Writer order, ownership installation, and truthful local prefix receipts are trusted. Source-RPC bytes exclude source-body acquisition, client result delivery, production framing, and process-control dissemination consistently across compared policies.

No minimal communication, instance optimality, universal workload win, production latency, deployment availability, malicious-source authentication, or external peer acceptance is claimed. No paper submission, public repository, email, account action, or external compute execution was performed.

<!-- FINAL-REVIEWER-HARDENING -->
## Final reviewer-hardening status

The final release reports source-facing and end-to-end application bytes separately. It treats continuation certificates, exact overlay, cut-aware caching, and full mirroring as a Pareto comparison rather than claiming universal dominance. The confirmatory experiment remains frozen; a wider-seed run is separately labeled post-hoc. Cold initialization, recurrence amortization, baseline contracts, query-schedule fairness, assumptions, negative controls, provenance, reference closure, deterministic PDF rebuilding, and exact-package reproduction are executable release gates.

See `artifact/FINAL-DELIVERY-REPORT.md` and `artifact/FINAL-REVIEWER-MATRIX.md`. Current local evidence-gate status: **INCOMPLETE**. Bibliography: **67 unique entries**. PDF: **17 pages**.
