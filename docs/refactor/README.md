# Рефакторинг `use_cases` — документация по PR (UC-1 … UC-8)

Подробное описание каждого этапа рефакторинга слоя `use_cases` (июнь 2026).  
Канон архитектуры: [PROJECT.md](../PROJECT.md). План работ: `.cursor/plans/use_cases_full_refactor_*.plan.md`.

## Порядок и зависимости

```
UC-1 → UC-2 → UC-3 → UC-4 → UC-5 → UC-6 → UC-7 → UC-8
                  ↑
            backup smoke обязателен
```

**Не смешивать:** restore extract (UC-7) шёл после layout (UC-6); Client API provider — отдельный трек.

## Файлы по этапам

| PR | Файл | Суть |
|----|------|------|
| UC-1 | [UC-01-ch1-session-progress.md](UC-01-ch1-session-progress.md) | CH-1b: автоключ в UC; `GetSessionProgressUseCase` |
| UC-2 | [UC-02-public-api.md](UC-02-public-api.md) | `use_cases/public/`: BackupApi, WorkerApi, commands, results |
| UC-3 | [UC-03-wire-adapters.md](UC-03-wire-adapters.md) | Удаление facade; bootstrap → public API |
| UC-4 | [UC-04-failure-reporting.md](UC-04-failure-reporting.md) | Report*Failure в WorkerApi + Celery |
| UC-5 | [UC-05-restore-refs.md](UC-05-restore-refs.md) | `restore_ref_for_volume` для Client API |
| UC-6 | [UC-06-shared-layout.md](UC-06-shared-layout.md) | Move-only: `use_cases/shared/` |
| UC-7 | [UC-07-restore-e2e.md](UC-07-restore-e2e.md) | Download + 7z extract → `dest_path` |
| UC-8 | [UC-08-import-linter.md](UC-08-import-linter.md) | `types.py` internal; `.importlinter`; CI |

## Gate каждого PR

```bash
.venv/bin/pytest -m "not integration" -v
.venv/bin/ruff check src tests
.venv/bin/mypy src
.venv/bin/lint-imports   # с UC-8
```

**Smoke (Roman, руками):** Start Session → Add File → Start Backup → Refresh Progress; с UC-7 — Restore Session.

## Критерий «слой закрыт»

- Adapters → только `use_cases.public`
- Нет `BackupFacade`
- Restore: файл в выбранном `dest_path`
- `import-linter` green + unit-тесты green
