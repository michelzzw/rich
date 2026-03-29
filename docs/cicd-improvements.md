# CI/CD Improvements — MGL842 TP2

This document summarises the CI/CD pipeline improvements made as part of TP2,
their motivation (linked to TP1 findings), and usage instructions.

---

## Context: what existed before

The original Rich project already had a solid CI pipeline (`pythonpackage.yml`):
- Tests on 3 OS × 7 Python versions (21 combinations)
- Black formatting check
- MyPy strict type checking
- pytest + Codecov coverage upload

**We kept this pipeline untouched.** TP2 adds three new things on top of it.

---

## What was added

### 1. Security scanning — `security.yml` (addresses TP1 — R5)

**Why:** TP1 identified that the CI pipeline had no dependency vulnerability scanning.
Dependabot was configured only for version updates, not security alerts.
The ISO 25010 Security dimension and SQO-OSS Security were both rated **Fair/Modéré**.

**What it does:**

| Job | Tool | Trigger |
|-----|------|---------|
| Dependency Audit | `pip-audit` | every PR + push to master |
| Code Complexity | `radon` | every PR + push to master |

**pip-audit job:**
- Exports the full dependency list (direct + transitive) via `poetry export`
- Runs `pip-audit` against it, checking PyPI Advisory Database + OSV
- Uploads a text report as a GitHub Actions artifact
- Non-blocking (`continue-on-error: true`) — findings are reported but don't block PRs
  *(remove `continue-on-error` in production once the baseline is clean)*

**radon job:**
- Reports cyclomatic complexity (CC) for all units in `rich/`
- Flags any unit with **CC > 50** (SIG 4-star threshold: 0% allowed) — linked to issues #1 and #2
- Reports Maintainability Index (MI) and raw LOC metrics
- Results appear directly in the GitHub Actions step summary (visible in the UI)

**Key finding on first run:**
```
pygments 2.19.2  CVE-2026-4539
ReDoS vulnerability in AdlLexer (pygments/lexers/archetype.py)
Fix: upgrade pygments when a patched version is released
```
This confirmed TP1's prediction that the dependency chain was unmonitored.
The scan detected a real CVE on day one of activation.

**radon findings (baseline, before any refactoring):**
- `rich/markdown.py::_traverse()` — CC=58 (tracked in issue #2)
- `rich/console.py::__str__()` — CC=35 (tracked in issue #1)
- Overall: 81% of units have CC ≤ 10 (good), but 3.4% at CC > 50 (SIG violation)

---

### 2. Docker build & deployment — `docker.yml`

**Why:** TP2 requires containerisation (IaC) and automated deployment to a test environment.
Rich is a library, not a service — a minimal FastAPI wrapper (`service/app.py`) was created
to provide a deployable artefact.

**What it does:**

| Event | Action |
|-------|--------|
| Pull Request | Builds image, runs smoke tests (validation only, no push) |
| Push to master | Builds + pushes to `ghcr.io/michelzzw/rich-service:latest` |

**Smoke tests (run inside the container):**
1. `GET /health` → expects `{"status": "ok"}`
2. `POST /render` with Markdown content → expects `html` and `ansi` fields in response

**Image:** `ghcr.io/michelzzw/rich-service:latest`
- Multi-stage build (builder + slim runtime)
- Non-root user (`appuser`) for security
- Docker `HEALTHCHECK` built in

---

### 3. Rich Render Service — `service/app.py`

A minimal FastAPI application exposing Rich's rendering over HTTP.
Used as the deployable unit for Docker/IaC/Observability demonstrations.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| POST | `/render` | Render content using Rich |

**`/render` request body:**
```json
{
  "content": "# Hello\nThis is **markdown**.",
  "format": "markdown",
  "language": "python"
}
```
Supported formats: `markdown`, `syntax` (code highlighting), `text`.

**`/render` response:**
```json
{
  "html": "<pre>...</pre>",
  "ansi": "\u001b[1m...\u001b[0m",
  "format": "markdown",
  "content_length": 42
}
```

---

## How to run locally

### Run the service with Docker Compose
```bash
docker compose up --build
# Service available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Test the endpoints
```bash
# Health check
curl http://localhost:8000/health

# Render markdown
curl -X POST http://localhost:8000/render \
  -H "Content-Type: application/json" \
  -d '{"content": "# Hello\n\nThis is **Rich**.", "format": "markdown"}'
```

### Run pip-audit locally
```bash
pip install pip-audit
poetry export --without-hashes -f requirements.txt -o /tmp/req.txt
pip-audit --requirement /tmp/req.txt --desc
```

### Run radon locally
```bash
pip install radon
radon cc rich/ -s -n B --show-complexity   # CC report
radon mi rich/ -s                           # Maintainability index
```

---

## Link to TP1 recommendations

| TP1 Recommendation | TP2 Action | Status |
|--------------------|------------|--------|
| R5 — Add dependency vulnerability scanning to CI | pip-audit job in `security.yml` | ✅ Done — CVE-2026-4539 found |
| R1 — Refactor `console.py` (Blob) | Tracked in issue #1, planned for next PR | 🔜 Pending |
| R2 — Decompose `_traverse()` | Tracked in issue #2, planned for next PR | 🔜 Pending |
| R3 — Reduce duplication in `progress.py` | Tracked in issue #3, planned for next PR | 🔜 Pending |
| R4 — Targeted test coverage | Monitored via existing Codecov integration | ✅ Monitored |

---

## DORA metrics baseline (before TP2 improvements)

To evaluate the quality process improvement (as required by TP2 evaluation criteria),
we measure the four DORA key metrics before and after the pipeline changes.

| Metric | Before TP2 | After TP2 |
|--------|-----------|-----------|
| Deployment Frequency | Manual / on-demand | Automated on every merge to master |
| Lead Time for Changes | Not measured | CI feedback in ~3 min (security + docker) |
| Change Failure Rate | Not measured | Tracked via failed CI runs |
| MTTR | Not measured | To be measured via observability stack |

*(The "after" values will be updated once the observability stack is in place.)*
