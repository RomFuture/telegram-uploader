# AI agent skills (planned)

How we wire **Cursor Agent Skills** into this repo: project rules the agent reads before coding, reviewing, or writing docs.

Status: **partial** — [stop-slop](https://github.com/hardikpandya/stop-slop) is a git submodule under `docs/stop-slop/`. Project-owned skills under `.cursor/skills/` are not set up yet.

---

## What skills are

A skill is a folder with `SKILL.md` (YAML frontmatter + instructions). Cursor loads skills when the task matches the skill `description`.

| Location | Path | Who sees it |
|----------|------|-------------|
| Personal | `~/.cursor/skills/<name>/` | You, all projects |
| Project | `.cursor/skills/<name>/` | Anyone who clones the repo |
| Reference only (not auto-loaded) | `docs/<vendor>/` via submodule | Humans + agent if you @-mention or copy rules |

Do **not** write into `~/.cursor/skills-cursor/` — that is Cursor’s built-in set.

---

## What to implement

### 1. Project skills directory

Create `.cursor/skills/` and add skills that encode **this repo’s** workflows:

| Skill (idea) | Trigger | Contents |
|--------------|---------|----------|
| `onion-layers` | Touching imports across `domain` / `use_cases` / `infrastructure` / `application` | Link [ONION_ARCHITECTURE.md](ONION_ARCHITECTURE.md), layer boundary test, “GUI never imports infrastructure” |
| `gate-and-smoke` | Closing backlog items | Link [ONION_LAYER_IMPLEMENTATION.md](ONION_LAYER_IMPLEMENTATION.md), `./scripts/run.sh`, manual smoke checklist |
| `telegram-uploader-dev` | Run / debug / compose | `.env`, ports 5433, worker log commands |
| `stop-slop` (optional wrapper) | Editing README, docs, user-facing prose | Point at `docs/stop-slop/SKILL.md` or vendor rules inline |

**Gate:** agent follows onion + gate docs without you pasting them each session; at least one project skill has a clear `description` and you verified it fires in Cursor.

### 2. Vendor skills: copy vs submodule

| Approach | Pros | Cons |
|----------|------|------|
| **Submodule** (e.g. `docs/stop-slop`) | Upstream updates via `git submodule update`; license stays visible | Clone needs `--recurse-submodules`; path is reference, not auto skill unless wired |
| **Vendor copy** (delete `.git`, commit files) | Simple clone; no submodule UX | You merge upstream by hand |
| **Personal install** | No repo noise | Teammates don’t get the same rules |

**Current choice:** `docs/stop-slop` = **submodule** → `https://github.com/hardikpandya/stop-slop.git`.

To use stop-slop when editing prose, @-mention `docs/stop-slop/SKILL.md` or add a thin `.cursor/skills/stop-slop/SKILL.md` that says “read and apply `docs/stop-slop/SKILL.md`”.

### 3. Clone / CI notes

After submodule is configured:

```bash
git clone --recurse-submodules git@github.com:RomFuture/telegram-uploader.git
# or, if already cloned:
git submodule update --init --recursive
```

CI does not need skills to run tests; optional check: fail if submodule pointer is missing (`git submodule status`).

---

## SKILL.md minimum

```markdown
---
name: skill-id
description: When to use this skill — one line, specific triggers
---

# Title

Instructions the agent must follow.
```

See Cursor’s skill authoring guide in your personal `create-skill` skill, or [stop-slop/SKILL.md](stop-slop/SKILL.md) for a small example.

---

## Suggested order of work

1. Fix submodule: `docs/stop-slop` (see below if `already exists in the index`).
2. Add `.cursor/skills/onion-layers/SKILL.md` (highest value for this codebase).
3. Add `.cursor/skills/gate-and-smoke/SKILL.md`.
4. Optional: wrapper skill for stop-slop prose rules.
5. Document clone flags in [README.md](../README.md) once submodule is on `main`.

---

## Submodule troubleshooting

**Error:** `fatal: 'docs/stop-slop' already exists in the index`

You ran `git add` on a folder that already had its own `.git`. Git staged a **gitlink** (pointer), not files. `git submodule add` refuses because the path is taken.

**Fix:**

```bash
git rm --cached docs/stop-slop          # drop bad index entry; keep files on disk
rm -rf docs/stop-slop                   # remove nested clone
git submodule add https://github.com/hardikpandya/stop-slop.git docs/stop-slop
git add .gitmodules docs/stop-slop
```

Result: `.gitmodules` + submodule commit SHA. Clones must use `--recurse-submodules` or `submodule update --init`.

---

## Out of scope (for now)

- Publishing skills to a public registry
- Skills that run shell commands without human review
- Duplicating full [INTERNAL_SPEC.md](INTERNAL_SPEC.md) inside every skill (link instead)

---

*Tracked in [BACKLOG.md](BACKLOG.md) · overview in [PROJECT.md](PROJECT.md)*
