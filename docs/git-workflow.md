# Git Workflow — MGL842 TP2

This document describes the Git workflow adopted for this project as part of the
MGL842 quality process improvement initiative (TP2).
It extends the original Rich contribution process documented in `CONTRIBUTING.md`.

---

## Branch Strategy

We use a **trunk-based development** approach with short-lived feature branches:

```
master          ← protected; all changes go through Pull Requests
  └── feature/<issue-id>-<short-description>   ← new feature or improvement
  └── fix/<issue-id>-<short-description>        ← bug fix
  └── refactor/<issue-id>-<short-description>   ← code quality refactoring
  └── ci/<description>                          ← CI/CD pipeline changes
```

### Branch naming examples

| Type | Example |
|------|---------|
| Refactoring | `refactor/1-console-blob-extraction` |
| Bug fix | `fix/42-progress-render-overflow` |
| CI improvement | `ci/add-pip-audit-security-scan` |
| Documentation | `docs/update-contributing-guide` |

---

## Protected Branch Rules (`master`)

The `master` branch has the following protections enabled:

| Rule | Setting |
|------|---------|
| Require pull request before merging | ✅ enabled |
| Required approving reviews | 1 |
| Dismiss stale reviews on new push | ✅ enabled |
| Require status checks to pass | ✅ CI must pass |
| Prevent force pushes | ✅ enabled |
| Prevent branch deletion | ✅ enabled |

---

## Pull Request Process

### 1. Create a branch from `master`

```bash
git checkout master
git pull origin master
git checkout -b refactor/1-console-blob-extraction
```

### 2. Develop and commit

Commit messages follow the **Conventional Commits** convention:

```
<type>(<scope>): <short summary>

[optional body]

Refs: #<issue-id>
```

**Types:** `feat`, `fix`, `refactor`, `ci`, `docs`, `test`, `chore`

Examples:
```
refactor(console): extract StyleManager from Console class

Reduces console.py from 1706 LOC toward the SIG <500 LOC target.
Moves style resolution logic to rich/style_manager.py.

Refs: #1
```

```
ci(security): add pip-audit dependency vulnerability scan

Adds a security job to pythonpackage.yml that runs pip-audit
on every pull request. Addresses TP1 recommendation R5.

Refs: #4
```

### 3. Local checks before pushing

Run all three checks locally (same as CI):

```bash
make test          # pytest + coverage
make typecheck     # mypy --strict
make format-check  # black --check
```

### 4. Open a Pull Request

- Target branch: `master`
- Fill in the PR template (classification, checklist, link to issue)
- CI will run automatically; fix any failures before requesting review

### 5. Code Review

- Reviewer checks functionality, code quality, and test coverage
- Reviewer uses the checklist in [CODE_REVIEW_CHECKLIST.md](code-review-checklist.md)
- Approval required before merge; stale approvals are dismissed on new pushes

### 6. Merge

- Use **squash and merge** to keep `master` history linear
- Delete the feature branch after merge

---

## Issue Tracking

All work items are tracked as GitHub Issues with the following labels:

| Label | Usage |
|-------|-------|
| `bug` | Incorrect behaviour |
| `tech-debt` | Technical debt identified by static analysis (TP1) |
| `refactoring` | Code restructuring without behaviour change |
| `code-quality` | Duplication, complexity, or size issues |
| `security` | Dependency vulnerability or CI security gap |
| `ci-cd` | Pipeline configuration and improvements |
| `observability` | Logging, metrics, distributed tracing |
| `testing` | Test coverage improvements |
| `enhancement` | New feature or improvement |
| `documentation` | Documentation updates |

### Current open issues (from TP1 analysis)

| # | Title | Priority |
|---|-------|----------|
| [#1](https://github.com/michelzzw/rich/issues/1) | Refactor console.py — Blob antipattern | High |
| [#2](https://github.com/michelzzw/rich/issues/2) | Decompose `_traverse()` — CC=58 | High |
| [#3](https://github.com/michelzzw/rich/issues/3) | Reduce duplication in progress.py | Medium |
| [#4](https://github.com/michelzzw/rich/issues/4) | Add pip-audit security scan to CI | Low |

---

## Remotes

| Remote | URL | Purpose |
|--------|-----|---------|
| `origin` | `https://github.com/michelzzw/rich` | Your fork — push here |
| `upstream` | `https://github.com/Textualize/rich` | Original project — fetch updates |

Sync with upstream:
```bash
git fetch upstream
git checkout master
git merge upstream/master
git push origin master
```
