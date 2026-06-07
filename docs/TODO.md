# TODO — backlog

Items here are **not scheduled** for the current slice of work. Pick them up when the vertical slice (Phases 5–8) is running end-to-end.

---

## Domain — compress and optimize (future)

**Status:** idea / deferred (domain core paused; lives in `src/domain/` as layer 1)

After the backup/restore pipeline works, revisit the domain package and ask: *can we say the same rules with less surface area?*

Possible directions (not decisions yet):

- [ ] **Generic entry points with `@overload`** — collapse `ensure_*` / `mark_*` per entity into `ensure(entity, status=…)` / `mark(entity, status=…)` if explicit names no longer pay for themselves.
- [ ] **Scenario-first API** — expose only `prepare_*` / workflow functions outward; keep `ensure_*` / `require_*` internal (not in `__all__`).
- [ ] **Remove entity `.create()` from models** — inline creation in `actions.py` if factories add no extra rules.
- [ ] **Merge `guards.py` + `scenarios.py`** — one module for preconditions if the split feels artificial.
- [ ] **Repository loading** — single `DomainLoader` vs per-repo `require()` / `list_domain_*` (trade-off: ergonomics vs Protocol size).
- [ ] **Error model** — fewer `code` variants, or typed `reason` enum instead of string duplication (`archive_volume_not_found` + `reason=`).
- [ ] **Audit dead exports** — `ensure_*` still public while use cases call `prepare_*`; decide what stays in the public contract.

**Gate:** do this **after** Phases 5–8 smoke tests pass. Optimizing domain before the pipeline runs risks polishing unused API.

**References:** `src/domain/`, [ONION_ARCHITECTURE.md](ONION_ARCHITECTURE.md) §1, discussion in agent session (repo `require()`, `scenarios.py`).

---

## Documentation sync (low priority)

- [ ] **Rewrite [`STEP_BY_STEP_IMPLEMENTATION_GUIDE.md`](../STEP_BY_STEP_IMPLEMENTATION_GUIDE.md)** — file is stale vs current codebase (`src/domain/` as top-level layer, repo `require()`, `scenarios.py`, use case classes exist, worker tasks still stubs). Either rewrite from scratch using [ONION_LAYER_IMPLEMENTATION.md](ONION_LAYER_IMPLEMENTATION.md) + [NEXT_SESSION.md](NEXT_SESSION.md) as source of truth, or replace with a shorter “current state + next steps” doc and archive the old guide.
- [ ] Update `ONION_ARCHITECTURE.md` — `guards.py` / `transitions.py` wording vs current `actions.py` + `scenarios.py`.
- [ ] Appendix C in `ONION_LAYER_IMPLEMENTATION.md` — check off completed doc items.
- [ ] `IMPLEMENTATION_GUIDE.md` — paths and status blocks (keep in sync after STEP guide rewrite).

---

## Observation / CI (Phase 9)

- [ ] `lint-imports` or equivalent in CI.
- [ ] Session logs + health probes (optional).

See [NEXT_SESSION.md](NEXT_SESSION.md) for the intentional “ship it ugly first” plan.
