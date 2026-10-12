# Company Research Rewrite: Master Plan

**Audience for this top section: the human orchestrator.** Everything above the first
FILE marker is ignored by the splitter. Everything below it is split into sub-files that
are fed to sub-agents.

## Goal

Replace the "disambiguate company" step with a **profile collection** step. For one
company name, the tool queries DuckDuckGo (via the `ddgs` package) for profiles from many
web sources (official site, Wikipedia, LinkedIn, Crunchbase, GitHub, news, careers pages,
and so on) and collates everything into **one markdown report** that an AI agent can read.
It is built test-first (red / green / refactor) and has a verbose / debug logging layer.

## How to split this file

Each sub-file begins with a marker line of the form `<!-- FILE: NN-name.md -->`
(an HTML comment, alone on its line). Split with:

```bash
mkdir -p plan
awk '/^<!-- FILE: [^ ]+ -->$/ { if (out) close(out); out = "plan/" $3; next } out { print > out }' COMPANY_RESEARCH_PLAN.md
ls plan/
```

## How to run a task

Every task needs the shared context, so always prepend `00-context.md`:

```bash
cat plan/00-context.md plan/01-baseline-and-test-infra.md | pi --print
```

Run the tasks in this order. Review each agent's "TASK REPORT" before starting the next
task. The "Can run in parallel with" column is only safe if each agent works in its own
checkout or branch, because the tasks touch disjoint files but share the test suite.

| Task | File | Depends on | Can run in parallel with |
|------|------|-----------|--------------------------|
| 01 | `01-baseline-and-test-infra.md` | none | none |
| 02 | `02-logging.md` | 01 | 03 |
| 03 | `03-textutil-and-models.md` | 01 | 02 |
| 04 | `04-sources.md` | 03 | 05, 06 |
| 05 | `05-search-client.md` | 02, 03 | 04, 06 |
| 06 | `06-extractors.md` | 03 | 04, 05 |
| 07 | `07-collector.md` | 04, 05, 06 | 08 |
| 08 | `08-report.md` | 03 | 07 |
| 09 | `09-cli.md` | 02, 07, 08 | none |
| 10 | `10-cleanup-docs-verification.md` | 09 | none |

Convenience loop (sequential, pauses for your review between tasks):

```bash
mkdir -p logs
for f in plan/0[1-9]-*.md plan/10-*.md; do
  echo "=== $f ==="
  cat plan/00-context.md "$f" | pi --print | tee "logs/$(basename "$f" .md).report.txt"
  read -p "Review the report above. Press Enter to continue, Ctrl-C to stop. "
done
```

## Decisions baked into this plan (change them here before splitting if you disagree)

1. **Disambiguation is removed** from the main flow. Its design notes are saved in
   `docs/FUTURE_DISAMBIGUATION.md` (Task 10) so it can come back later.
2. **The old `test_company_research.py` is retired.** Most of its tests asserted only that a
   key exists or that `True` is true. The new suite lives in `tests/`.
3. **Per-source failure never aborts a run.** Failures are recorded in the report so the
   reading agent knows about data gaps.
4. **stdout carries only the report path.** All logs go to stderr, so the tool is pipe-friendly.
5. **Regex fact extraction is explicitly "heuristic".** The raw evidence (URL and snippet) is
   the primary payload, and extracted facts always point back to their evidence.

<!-- FILE: 00-context.md -->
# SHARED CONTEXT (read fully before doing anything)

You are a junior developer working on a small Python project. You will be given ONE task
file after this context. Do only that task. Follow the process rules below exactly.

## 1. Project goal

`company_research.py` takes a company name, searches DuckDuckGo (package `ddgs`) for
profile information from many web sources, and writes ONE markdown report. The report
is meant to be read by an AI agent, so it must be predictable, complete, and honest about
gaps. The old "disambiguate company" step is being removed. It is NOT part of this work.

## 2. Environment facts (verified on the owner's machine)

- Run Python as `python3` (3.14). Standard library only, plus `ddgs`. Test runner is `unittest`.
- Import with `from ddgs import DDGS` and `from ddgs.exceptions import DDGSException`.
- Use `with factory() as ddgs:` where `factory` is `DDGS` or a fake. Call `ddgs.text(query, max_results=N)`.
- `ddgs.text()` returns a list of dicts with keys `title`, `href`, `body`.
- When a query has zero results, the real library RAISES `DDGSException("No results found.")`.
  It does not return `[]`. Our code must treat that specific case as an empty result, not a failure.
- All commands run from the project root (the directory containing `company_research.py`).

## 3. Target layout (files are created by different tasks)

```
company_research.py          # thin shim: calls researchlib.cli.main  (Task 09)
requirements.txt             # (Task 01)
README.md                    # (Task 10)
docs/FUTURE_DISAMBIGUATION.md  # (Task 10)
researchlib/
  __init__.py                # (Task 01)
  logging_setup.py           # (Task 02)
  textutil.py                # (Task 03)
  models.py                  # (Task 03)
  sources.py                 # (Task 04)
  search_client.py           # (Task 05)
  extractors.py              # (Task 06)
  collector.py               # (Task 07)
  report.py                  # (Task 08)
  cli.py                     # (Task 09)
tests/
  __init__.py                # (Task 01)
  base.py  fakes.py  fixtures.py            # (Task 01)
  test_base.py  test_fakes.py               # (Task 01)
  test_logging_setup.py                     # (Task 02)
  test_textutil.py  test_models.py          # (Task 03)
  test_sources.py                           # (Task 04)
  test_search_client.py                     # (Task 05)
  test_extractors.py                        # (Task 06)
  test_collector.py                         # (Task 07)
  test_report.py  golden/acme_freight_report.md   # (Task 08)
  test_cli.py                               # (Task 09)
  test_live_smoke.py                        # (Task 10)
```

## 4. Module contract (public signatures; build to exactly these)

Later tasks rely on these. Do not rename or change them. If something seems wrong, say so
in your report instead of changing it.

```python
# researchlib/logging_setup.py
LOGGER_NAME = "researchlib"
def verbosity_to_level(verbosity: int) -> int
def configure_logging(verbosity: int = 0, log_file: str | Path | None = None) -> logging.Logger
def reset_logging() -> None

# researchlib/textutil.py
def truncate(text: str, limit: int = 200) -> str
def collapse_whitespace(text: str) -> str
def slugify(text: str) -> str
def md_escape(text: str) -> str

# researchlib/models.py
class SourceStatus(str, Enum):  OK="ok"; EMPTY="empty"; ERROR="error"; SKIPPED="skipped"
class FactCategory(str, Enum):  FOUNDED="founded"; LEADER="leader"; FUNDING_ROUND="funding_round"; FUNDING_AMOUNT="funding_amount"; TECH="tech"
@dataclass(frozen=True) class SearchHit:   title: str; url: str; snippet: str
    @classmethod def from_ddgs(cls, raw: Mapping[str, Any]) -> "SearchHit"
@dataclass(frozen=True) class SourceSpec:
    key: str; label: str; query_template: str
    allowed_domains: tuple[str, ...] = ()
    requires_website: bool = False
    use_location: bool = False
    max_results: int = 10
@dataclass(frozen=True) class Fact:  category: FactCategory; value: str; evidence_url: str; evidence_snippet: str
@dataclass(frozen=True) class SourceProfile:
    spec_key: str; label: str; status: SourceStatus; query: str
    hits: tuple[SearchHit, ...] = (); detail: str = ""
@dataclass(frozen=True) class ResearchResult:
    company_name: str; location: str | None; website_domain: str | None
    generated_at: datetime; profiles: tuple[SourceProfile, ...]; facts: tuple[Fact, ...]
    # properties / methods:
    #   total_hits -> int          (sum of len(hits) over all profiles)
    #   all_hits -> tuple[SearchHit, ...]   (hits of profiles with status OK, in profile order)
    #   count_status(status: SourceStatus) -> int
    #   has_hits -> bool
    #   all_failed -> bool   (at least one profile ERROR, and none OK or EMPTY)

# researchlib/sources.py
OFFICIAL_WEBSITE_KEY = "official_website"
AGGREGATOR_DOMAINS: frozenset[str]
DEFAULT_SOURCES: tuple[SourceSpec, ...]
def extract_domain(url: str) -> str
def domain_matches(url: str, allowed_domains: Sequence[str]) -> bool
def normalize_url(url: str) -> str
def filter_hits_by_domain(hits: Sequence[SearchHit], allowed_domains: Sequence[str]) -> list[SearchHit]
def dedupe_hits(hits: Sequence[SearchHit]) -> list[SearchHit]
def build_query(spec: SourceSpec, company_name: str, location: str | None = None,
                website_domain: str | None = None) -> str
def pick_official_website(hits: Sequence[SearchHit], company_name: str) -> str | None

# researchlib/search_client.py
class SearchError(Exception):   # has attribute .query
def is_no_results_error(exc: BaseException) -> bool
class SearchClient:
    def __init__(self, ddgs_factory=DDGS, *, delay_seconds: float = 1.0,
                 max_attempts: int = 2, sleep_fn=time.sleep)
    def search(self, query: str, max_results: int = 10) -> list[SearchHit]

# researchlib/extractors.py
def extract_founding_years(hits, *, current_year: int | None = None) -> list[Fact]
def extract_leaders(hits, *, company_name: str | None = None) -> list[Fact]
def extract_funding(hits) -> list[Fact]
def extract_tech_keywords(hits) -> list[Fact]
def dedupe_facts(facts) -> list[Fact]
def extract_all(hits, *, company_name: str | None = None, current_year: int | None = None) -> list[Fact]

# researchlib/collector.py
class ProfileCollector:
    def __init__(self, client: SearchClient, sources: Sequence[SourceSpec] = DEFAULT_SOURCES,
                 *, now_fn: Callable[[], datetime] = <UTC now>)
    def collect(self, company_name: str, location: str | None = None,
                website_override: str | None = None) -> ResearchResult

# researchlib/report.py
def report_filename(company_name: str) -> str
def render_markdown(result: ResearchResult) -> str
def write_report(result: ResearchResult, output_dir: str | Path) -> Path

# researchlib/cli.py
def build_arg_parser() -> argparse.ArgumentParser
def main(argv: Sequence[str] | None = None, *, client: SearchClient | None = None,
         now_fn: Callable[[], datetime] | None = None) -> int
```

## 5. Process rules (mandatory)

Work in **red / green / refactor** order. Do not skip or reorder the phases.

1. **RED.** Write the tests for this task FIRST. Do not create or edit production code yet
   (except an empty stub file so imports resolve, if needed). Run the tests. Confirm they
   fail **for the right reason** (missing function, wrong value). They must NOT fail from
   typos, syntax errors, or bad imports in the test file itself. Save the failing output
   summary for your report.
2. **GREEN.** Write the **minimum** production code that makes the tests pass. Resist
   adding features that no test requires. Run the full suite until it passes.
3. **REFACTOR.** With tests green, improve names, remove duplication, add docstrings and
   type hints. Re-run the full suite after every change. Behavior must not change.

If the project is inside a git repository, commit after each phase:
`test(<module>): <summary>`, then `feat(<module>): <summary>`, then `refactor(<module>): <summary>`.
If it is not a git repository, skip commits.

Other rules:

- Touch ONLY the files your task lists. Do not edit tests from earlier tasks. If you believe
  an earlier test is wrong, do not "fix" it silently. Describe the problem in your report.
- If the task is ambiguous, pick the simplest reading and record it under "Decisions" in the
  report. Do not stop to ask questions, and do not invent extra features.
- Never make a real network call in tests. Never write files into the current working
  directory in tests (use `tempfile.TemporaryDirectory`).
- Do not add dependencies other than `ddgs` (Task 10 may add `coverage` as a dev-only tool).
- Do not weaken a test to make it pass. Fix the code. The only exception is a test that is
  genuinely wrong, and then you must explain it in the report.

## 6. Test quality standards (mandatory)

- Layout: Arrange / Act / Assert, with a blank line between the sections.
- One behavior per test. Name tests `test_<unit>_<condition>_<expected result>`.
  (Names listed in tasks are suggestions. The behaviors are mandatory.)
- Assert **specific values** (exact strings, lists, counts, status enums). Banned:
  `assertTrue(True)`, asserting only that a key exists, asserting only `len(x) > 0`
  where the exact content is knowable, and testing Python's own standard library.
- Table-driven cases use `with self.subTest(case=...)`.
- Test failure paths and edge cases (empty input, None, malformed data, boundaries),
  not just the happy path.
- Tests must be deterministic and fast: inject clocks (`now_fn`), sleep (`sleep_fn`),
  and the search factory. Do not rely on wall-clock time, randomness, or ordering of sets.
- All test classes that touch our code inherit `tests.base.NoNetworkTestCase` (created in Task 01).
- At the ddgs boundary use `tests.fakes.FakeDDGSFactory`, not `MagicMock`. Use `MagicMock`
  only where a fake would be disproportionate, and say why in a comment.
- After GREEN, do a **mutation spot check**: temporarily break one line of the new
  production code (flip a comparison, drop a call, change a constant). Confirm at least one
  test fails, then revert the change exactly. Record the result in the report.

Commands:

```bash
python3 -m unittest discover -s tests -t . -v          # whole suite
python3 -m unittest tests.test_sources -v               # one module
python3 -W error -m unittest discover -s tests -t .     # also fails on warnings (run this at the end)
```

## 7. Logging standards (apply to all production code)

- Every module in `researchlib/` starts with `logger = logging.getLogger(__name__)`.
  Because modules live in the `researchlib` package, their loggers are automatically
  children of `researchlib`. Never use `print` for diagnostics. Only `cli.py` may print,
  and only the report path to stdout.
- Use lazy formatting: `logger.debug("query=%r results=%d", query, n)`. Never use f-strings
  in logging calls.
- Levels:
  - **DEBUG:** every query string; raw hit counts; each hit dropped and why; throttle sleeps;
    retry attempts; extractor matches (pattern and value); fact de-duplication; section sizes.
    Snippets are logged only through `textutil.truncate(...)`.
  - **INFO:** run start (company, location, options); each source start and finish (key,
    status, hit count, elapsed ms); website domain chosen; report written (path, bytes); run summary.
  - **WARNING:** a source failed, was skipped, or came back empty; retry after an error; no
    official website found.
  - **ERROR:** every source failed; the report could not be written.
- When catching an exception to convert or record it, log it with `logger.debug(..., exc_info=True)`
  so the traceback is available at DEBUG without flooding normal output.
- Tests assert logging with `self.assertLogs("researchlib", level=...)`. Assert level and a
  stable substring such as the query or source key, not the full message.

## 8. Code standards

- Type hints on all public functions. A docstring on every public function and class
  (one-line summary, then Args/Returns/Raises if non-obvious).
- No bare `except:`. Catch the narrowest exception that makes sense.
- No module-level mutable state, no global singletons. Pure functions where possible.
- Constants are UPPER_CASE at module top. Immutable dataclasses (`frozen=True`) for data.
- Keep functions short (aim for under 40 lines). Extract helpers with names that describe intent.

## 9. Final output format (required)

When you finish, print exactly this structure as your final message:

```
TASK REPORT: <task number and title>
FILES CREATED/CHANGED:
  - path (new|modified)
RED:   <command run> -> <N failures/errors, and the reason in one line>
GREEN: <command run> -> <"Ran N tests ... OK" line>
REFACTOR: <bullet list of what you changed, or "none">
MUTATION CHECK: <what you broke> -> <which test failed> -> reverted
FULL SUITE: <"Ran N tests ... OK" from python3 -W error -m unittest discover -s tests -t .>
DECISIONS / ASSUMPTIONS: <bullets, or "none">
OPEN ISSUES / THINGS THE OWNER SHOULD REVIEW: <bullets, or "none">
```

If you cannot complete the task, say exactly which step failed, paste the relevant error
output, and stop. Do not fabricate a passing result.

<!-- FILE: 01-baseline-and-test-infra.md -->
# TASK 01: Baseline and test infrastructure

**Read the shared context above first.** This task builds the scaffolding and the shared
test tools. It contains no business logic. Tests here test the *test tools* themselves.

## Files

Create: `requirements.txt`, `.gitignore`, `researchlib/__init__.py` (empty),
`tests/__init__.py` (empty), `tests/base.py`, `tests/fakes.py`, `tests/fixtures.py`,
`tests/test_base.py`, `tests/test_fakes.py`.
Delete: `test_company_research.py` in the project root (replaced by the new suite).
Do NOT touch `company_research.py` (a later task replaces it).

## Step 0: Safety baseline

1. If in a git repo: `git tag pre-profile-rewrite` (ignore the error if the tag exists).
2. Run `python3 --version` and `pip show ddgs`. Write `requirements.txt` containing one line
   pinned to the installed version, e.g. `ddgs==X.Y.Z`.
3. Run `python3 -c "import ddgs.exceptions as e; print([n for n in dir(e) if not n.startswith('_')])"`
   and include the output in your report.
4. `.gitignore` must contain: `__pycache__/`, `*.pyc`, `search_results/`, `logs/`, `.coverage`, `htmlcov/`.

## Step 1: RED. Write these files and tests first

### `tests/base.py`: `NoNetworkTestCase`

A `unittest.TestCase` subclass whose `setUp` patches `socket.socket.connect` so that any
connection attempt raises `AssertionError("Network access attempted in a unit test")`.
Use `patch.object(...)` started in `setUp` and stopped with `self.addCleanup(patcher.stop)`.
Subclasses that define their own `setUp` must call `super().setUp()`. Document this in the docstring.

### `tests/fakes.py`: `FakeDDGSFactory`

A callable that stands in for the `DDGS` class. The code under test does
`with factory() as ddgs: ddgs.text(query, max_results=N)`, so a **new session object is created per call**
but **state is shared on the factory**.

Required API:

```python
factory = FakeDDGSFactory()
factory.add_response(substring: str, hits: list[dict])   # if substring in query -> return hits (ddgs dict format)
factory.add_error(substring: str, exc: BaseException)    # if substring in query -> raise exc
factory.add_no_results(substring: str)                   # shorthand: raises DDGSException("No results found.")
factory.set_default(hits: list[dict] | None)             # for unmatched queries; None (initial) means unmatched -> AssertionError
factory.queries        -> list[str]                      # every query received, in order
factory.calls          -> list[tuple[str, int]]          # (query, max_results) in order
factory.sessions_opened -> int                           # times __enter__ ran
factory.sessions_closed -> int                           # times __exit__ ran (even when text() raised)
```

Rules: rules are checked in the order they were added and the **first match wins**.
`text(query, max_results=10, **kwargs)` returns a **new list** of copies, truncated to `max_results`.
An unmatched query with no default raises `AssertionError(f"Unscripted query: {query!r}")`
(this makes test mistakes loud). `__exit__` returns `False` (never swallows exceptions).

### `tests/fixtures.py`

- `make_hit(title="T", url="https://example.com", snippet="S") -> dict` returning ddgs format
  (`title`, `href`, `body`).
- A fictional company dataset (never real companies): constant `ACME_NAME = "Acme Freight"` and
  helper functions that return realistic ddgs-format hit lists, for example `acme_official_hits()`,
  `acme_wikipedia_hits()`, `acme_linkedin_hits()`, `acme_crunchbase_hits()`, `acme_github_hits()`,
  `acme_news_hits()`, `acme_leadership_hits()`, `acme_careers_hits()`, `acme_funding_hits()`,
  `acme_founding_hits()`. Official site domain: `acmefreight.com`. Snippets should embed
  extractable facts: "founded in 2015", "Jane Doe, CEO", "raised $10 million in Series A",
  "Python, React and Kubernetes". Add a function `acme_factory() -> FakeDDGSFactory`
  pre-scripted with responses keyed on distinctive query substrings (`"official website"`,
  `site:wikipedia.org`, `site:linkedin.com`, `site:crunchbase.com`, `site:github.com`,
  `site:acmefreight.com leadership`, `site:acmefreight.com careers`, `site:acmefreight.com about`,
  `funding round`, `founded history`, `announces`, `site:glassdoor.com`). Later tasks reuse this.
  Make `acme_factory()` complete enough that every default source query gets a response.
  (Task 04 finalizes the exact query templates. Task 07 will adjust substrings here if a rule
  needs it, and may edit only this one function.)

### `tests/test_base.py`

- `test_socket_connect_is_blocked`: inside a `NoNetworkTestCase` subclass, `socket.socket().connect(("example.com", 80))`
  raises `AssertionError` whose message mentions "Network access".
- `test_patch_is_removed_after_test`: after a test finishes, `socket.socket.connect` is the original
  (verify with a second test case run via `unittest.TestResult`, or by comparing to a saved original in module scope).

### `tests/test_fakes.py` (inherits `NoNetworkTestCase`)

- first-match-wins ordering; substring matching; returns copies (mutating the result does not alter the script);
  truncation to `max_results`; unmatched query with no default raises `AssertionError` mentioning the query;
  `set_default` is used for unmatched queries; `add_no_results` raises `DDGSException` whose message starts with
  "No results found"; `add_error` raises the given exception; `queries` and `calls` record in order;
  `sessions_opened == sessions_closed` after a normal call AND after a call that raises (proves `__exit__` runs);
  `__exit__` does not suppress exceptions; `make_hit` produces the three ddgs keys.

Run `python3 -m unittest discover -s tests -t . -v`. Expect failures (the tools do not exist yet).

## Step 2: GREEN

Implement `tests/base.py`, `tests/fakes.py`, `tests/fixtures.py` minimally to pass.

## Step 3: REFACTOR

Make sure the fake has docstrings that show a usage example, and that fixtures are plain data with no logic.

## Done when

- `python3 -m unittest discover -s tests -t . -v` is green, finishes in well under 1 second, and the old root test file is gone.
- Report includes the `ddgs.exceptions` names and the pinned version.

<!-- FILE: 02-logging.md -->
# TASK 02: Logging layer

**Read the shared context above first.** Depends on Task 01.

## Files

Create: `researchlib/logging_setup.py`, `tests/test_logging_setup.py`.

## Behavior spec

```python
LOGGER_NAME = "researchlib"
def verbosity_to_level(verbosity: int) -> int
def configure_logging(verbosity: int = 0, log_file=None) -> logging.Logger
def reset_logging() -> None
```

- `verbosity_to_level`: `<= -1` -> `logging.ERROR`; `0` -> `WARNING`; `1` -> `INFO`; `>= 2` -> `DEBUG`.
- `configure_logging` configures **only** the logger named `researchlib` (never the root logger):
  - logger level is `DEBUG`; `propagate = False`.
  - a console `StreamHandler` writing to **`sys.stderr` as it is at call time** (so tests can patch `sys.stderr`),
    at the level from `verbosity_to_level`.
  - if `log_file` is given, a `FileHandler` (UTF-8) at level `DEBUG` **regardless of verbosity**.
    Create parent directories if missing.
  - format: `%(asctime)s %(levelname)-8s %(name)s: %(message)s`.
  - **Idempotent:** calling it again replaces the handlers it previously added. It never stacks duplicates.
  - returns the `researchlib` logger.
- `reset_logging`: removes and closes every handler that `configure_logging` added, restores
  `propagate = True` and level `NOTSET`. Safe to call when nothing is configured.

## Step 1: RED. Tests (`NoNetworkTestCase`; each test calls `reset_logging` via `addCleanup`)

1. `verbosity_to_level` table with `subTest`: -3, -1, 0, 1, 2, 3, 10.
2. `configure_logging(0)` -> a DEBUG message is NOT in captured stderr; a WARNING message IS.
3. `configure_logging(1)` -> INFO appears, DEBUG does not. `configure_logging(2)` -> DEBUG appears.
4. Output line contains the level name and the logger name (e.g. `researchlib.search_client`).
5. Calling `configure_logging` three times leaves exactly **one** console handler (inspect `logger.handlers`).
6. With `log_file` in a temp dir and `verbosity=0`: DEBUG message is in the file, NOT in stderr.
7. `log_file` in a not-yet-existing nested directory is created.
8. The root logger's handlers and level are unchanged by `configure_logging`.
9. `reset_logging` leaves zero handlers, closes the file (writing afterwards does not append to the file), and is safe to call twice.
10. Messages from a child logger (`logging.getLogger("researchlib.anything")`) are captured.

To capture stderr use `unittest.mock.patch("sys.stderr", new_callable=io.StringIO)` **before** calling
`configure_logging`. On Windows file handles must be closed before the temp dir is removed. Call `reset_logging` first.

## Step 2: GREEN, Step 3: REFACTOR

Implement minimally, then tidy (name the format string as a constant; keep a module-level
`_OWNED_HANDLERS` marker approach that does not use mutable global lists. Prefer tagging
handlers with an attribute such as `handler._researchlib_owned = True`).

## Done when

All new tests plus the full suite are green, and `python3 -W error -m unittest ...` shows no ResourceWarning
about unclosed files.

<!-- FILE: 03-textutil-and-models.md -->
# TASK 03: Text utilities and data models

**Read the shared context above first.** Depends on Task 01.

## Files

Create: `researchlib/textutil.py`, `researchlib/models.py`, `tests/test_textutil.py`, `tests/test_models.py`.

## Part A: `textutil.py` (pure functions)

- `truncate(text, limit=200)`: if `len(text) <= limit` return unchanged; otherwise return a string of
  **exactly `limit` characters** ending in `...`. If `limit < 4`, return `text[:limit]` without ellipsis.
- `collapse_whitespace(text)`: replace every run of whitespace (spaces, tabs, newlines) with a single space; strip ends.
- `slugify(text)`: lowercase; replace every run of non-alphanumeric characters with a single `_`; strip leading and
  trailing `_`; if the result is empty return `"company"`. Unicode letters are kept (`"Café"` -> `"café"`).
- `md_escape(text)`: collapse whitespace (newlines become spaces), then backslash-escape these characters:
  `\`, `|`, `[`, `]`, `*`, `_`, `` ` ``, `<`, `>`. Order matters: escape backslash first.

### RED tests for textutil (table-driven with `subTest`)

- `truncate`: shorter than limit, exactly the limit, one over the limit, limit of 3, empty string, default limit.
- `collapse_whitespace`: `"a  b"`, `"a\n\tb"`, leading/trailing whitespace, only whitespace -> `""`.
- `slugify`: `"Good Ship, Inc."` -> `good_ship_inc`; `"  --  "` -> `company`; `""` -> `company`; `"A/B Testing"` -> `a_b_testing`; `"Café Ünï"` -> `café_ünï`; `"x"` -> `x`.
- `md_escape`: pipe, brackets, backtick, newline, a literal backslash (`"a\\b"` -> `"a\\\\b"` i.e. doubled), plain text unchanged, combined case `"[x]|y\nz"`.

## Part B: `models.py`

Implement exactly the dataclasses and enums in the module contract (shared context section 4).

- `SearchHit.from_ddgs(raw)`: reads `title`, `href`, `body`. Missing keys or `None` -> `""`. Strips surrounding whitespace.
  Does not collapse inner whitespace (the report layer does that).
- `ResearchResult` helpers: `total_hits`, `all_hits`, `count_status`, `has_hits`, `all_failed` per the contract.
  `has_hits` is `True` when `total_hits > 0`.

### RED tests for models

- `from_ddgs`: full dict; missing each key; `None` values; whitespace stripping; extra keys ignored.
- Frozen: assigning to a field raises `dataclasses.FrozenInstanceError` (check one of each dataclass).
- Enum values are the exact strings in the contract, and `SourceStatus.OK == "ok"` is true (str-based enum).
- `ResearchResult` with profiles in these configurations: all OK; mix of OK/EMPTY/ERROR/SKIPPED; all ERROR; all SKIPPED;
  no profiles at all. Assert `total_hits`, `all_hits` (order, and that only OK profiles contribute),
  `count_status` for each status, `has_hits`, and `all_failed`.
  Specifically: `all_failed` is `False` for no profiles, `False` for all SKIPPED, `False` for ERROR+EMPTY, `True` for ERROR+SKIPPED,
  `True` for all ERROR.
- A small helper function in the test module builds profiles to keep tests readable.

## Steps 2 and 3

GREEN, then REFACTOR (docstrings; keep dataclasses free of logic beyond the listed properties).

<!-- FILE: 04-sources.md -->
# TASK 04: Source definitions and hit-processing helpers

**Read the shared context above first.** Depends on Task 03 (models).

## Files

Create: `researchlib/sources.py`, `tests/test_sources.py`.
You may also edit **`tests/fixtures.py::acme_factory` only** to align its substrings with the final query templates.

## Behavior spec

### `DEFAULT_SOURCES` (a tuple of `SourceSpec`, in exactly this order)

| # | key | label | query_template | allowed_domains | requires_website | use_location |
|---|-----|-------|----------------|-----------------|------------------|--------------|
| 1 | `official_website` | Official Website | `"{name}" official website` | `()` | no | **yes** |
| 2 | `wikipedia` | Wikipedia | `site:wikipedia.org "{name}" company` | `("wikipedia.org",)` | no | no |
| 3 | `linkedin` | LinkedIn | `site:linkedin.com/company "{name}"` | `("linkedin.com",)` | no | no |
| 4 | `crunchbase` | Crunchbase | `site:crunchbase.com/organization "{name}"` | `("crunchbase.com",)` | no | no |
| 5 | `github` | GitHub | `site:github.com "{name}"` | `("github.com",)` | no | no |
| 6 | `glassdoor` | Glassdoor | `site:glassdoor.com "{name}" overview` | `("glassdoor.com",)` | no | no |
| 7 | `news` | News and Announcements | `"{name}" announces OR launches OR partnership` | `()` | no | no |
| 8 | `founding_search` | Founding and History | `"{name}" founded history` | `()` | no | no |
| 9 | `funding_search` | Funding | `"{name}" funding round raised Series seed` | `()` | no | no |
| 10 | `website_about` | Website: About | `site:{domain} about OR company OR team` | `()` | **yes** | no |
| 11 | `website_leadership` | Website: Leadership | `site:{domain} leadership OR team OR executives` | `()` | **yes** | no |
| 12 | `website_careers` | Website: Careers and Engineering | `site:{domain} careers OR jobs engineering` | `()` | **yes** | no |

`max_results` is 10 for all. For specs with `requires_website=True`, hits are later filtered to the discovered
website domain (the collector does that). `allowed_domains` stays empty for them.
If live testing later shows a template works poorly, only the template strings change.
Tests must therefore not hardcode the full template text. Test structure instead (see below).

### `AGGREGATOR_DOMAINS` (frozenset of lowercase domains)

`linkedin.com, crunchbase.com, wikipedia.org, facebook.com, twitter.com, x.com, instagram.com, youtube.com,
glassdoor.com, indeed.com, bloomberg.com, zoominfo.com, pitchbook.com, github.com, reddit.com, yelp.com,
medium.com, techcrunch.com`

### Functions

- `extract_domain(url)`: lowercase host, remove a leading `www.`, remove any port. Accept a bare domain with no scheme
  (`"acmefreight.com"` or `"acmefreight.com/about"` -> `"acmefreight.com"`; implement by prefixing `//` when `"://"` is not in the string).
  Return `""` for empty or unparseable input. Never raise.
- `domain_matches(url, allowed_domains)`: empty `allowed_domains` -> `True`. Otherwise `True` if the URL's domain equals an allowed
  domain or ends with `"." + allowed`. (`"en.wikipedia.org"` matches `"wikipedia.org"`. `"notwikipedia.org"` does NOT.)
- `normalize_url(url)`: lowercase scheme and host; drop the fragment; drop `utm_*` query parameters (keep other params and their order);
  strip a trailing `/` from the path unless the path is just `/`; leave everything else untouched.
- `filter_hits_by_domain(hits, allowed_domains)`: keep hits where `domain_matches` is true, preserving order.
  Log each dropped hit at DEBUG (url and the allowed list).
- `dedupe_hits(hits)`: keep the first hit for each `normalize_url(hit.url)`; preserve order. Drop hits whose url is empty
  (log at DEBUG). Log each duplicate dropped at DEBUG.
- `build_query(spec, company_name, location=None, website_domain=None)`:
  1. `ValueError` if `company_name` is blank after stripping.
  2. `ValueError` if the template contains `{domain}` and `website_domain` is falsy.
  3. Format the template with `name=company_name.strip()` and `domain=website_domain`.
  4. If `spec.use_location` and `location` (stripped) is non-empty, append `" " + location.strip()`.
  Double quotes inside `company_name` are removed so the query's quoting stays balanced.
- `pick_official_website(hits, company_name)`: among hits whose domain is not in `AGGREGATOR_DOMAINS` (compare using
  `domain_matches(url, AGGREGATOR_DOMAINS)` semantics, so subdomains of aggregators are also excluded):
  prefer the first whose domain, with dots and hyphens removed, contains the *normalized company name*
  (lowercase, alphanumerics only, with trailing corporate suffixes `inc`, `llc`, `ltd`, `corp`, `co`, `company` removed);
  otherwise the first non-aggregator hit; otherwise `None`. Returns the domain from `extract_domain`.
  Log the decision and the reason at DEBUG.

## Step 1: RED. Tests (`NoNetworkTestCase`, table-driven)

**`DEFAULT_SOURCES` structure tests**
- keys are unique; first key is `OFFICIAL_WEBSITE_KEY` and it does not require the website;
- every template's placeholders (use `string.Formatter().parse`) are a subset of `{name, domain, location}`
  and every template includes `{name}` or `{domain}`;
- `requires_website` is true exactly when the template contains `{domain}`;
- `allowed_domains` entries are lowercase, contain no `/` or `:`; all `max_results >= 1`;
- there are exactly 12 sources, and all six `requires_website=False` profile sources (`wikipedia`, `linkedin`, `crunchbase`, `github`, `glassdoor`) have non-empty `allowed_domains`.

**`extract_domain`**: `https://www.Acme.com/a?b=1`, `http://acme.com:8080/x`, `acme.com`, `acme.com/about`, `""`, `"   "`, `"https://"`, `"not a url"` -> `""` or a sane value (document what you choose in a test), `https://en.wikipedia.org/wiki/X`.

**`domain_matches`**: exact; subdomain; look-alike suffix (`notwikipedia.org`); multiple allowed; empty allowed -> True; empty url with non-empty allowed -> False.

**`normalize_url`**: case; fragment; trailing slash; root path stays `/`; `utm_source` removed while `id=5` kept; two URLs differing only by `utm_*` normalize equal.

**`filter_hits_by_domain`**: keeps matching in order, drops others, empty allowed keeps everything, returns a new list, and logs DEBUG for drops (`assertLogs`).

**`dedupe_hits`**: duplicates with trailing slash / fragment / utm; first wins; order preserved; empty url dropped; empty input.

**`build_query`**: placeholder substitution with custom `SourceSpec`s; location appended only when `use_location` is true AND location given; location ignored when `use_location` is false; whitespace-only location ignored; `{domain}` without a domain raises `ValueError`; blank name raises `ValueError`; quotes stripped from name; name is stripped; also one test that builds a query from **every** `DEFAULT_SOURCES` entry (with a name and domain supplied) and asserts no `{` or `}` remains.

**`pick_official_website`**: official + aggregators mixed -> official; name-in-domain beats earlier non-aggregator; `"Acme Freight, Inc."` matches `acmefreight.com`; `www.` stripped; only aggregators -> `None`; subdomain of aggregator excluded (`uk.linkedin.com`); empty list -> `None`; no name match -> first non-aggregator; logs a DEBUG message.

## Steps 2 and 3

GREEN, then REFACTOR. Then update `acme_factory()` substrings in `tests/fixtures.py` if they no longer match the final templates
(verify by building every default query and asserting the factory has a rule for it. Add this as a test in `test_sources.py`).

<!-- FILE: 05-search-client.md -->
# TASK 05: Search client (throttle, retry, error translation)

**Read the shared context above first.** Depends on Tasks 02 and 03.

## Files

Create: `researchlib/search_client.py`, `tests/test_search_client.py`.

## Behavior spec

```python
class SearchError(Exception):   # constructor SearchError(message, query=None); attribute .query
def is_no_results_error(exc: BaseException) -> bool
class SearchClient:
    def __init__(self, ddgs_factory=DDGS, *, delay_seconds=1.0, max_attempts=2, sleep_fn=time.sleep)
    def search(self, query, max_results=10) -> list[SearchHit]
```

- `is_no_results_error(exc)`: `True` only if `exc` is a `DDGSException` whose message, stripped and lowercased,
  starts with `"no results found"`. This isolates the library quirk in one tested place.
- `__init__` validates: `delay_seconds >= 0` and `max_attempts >= 1`, else `ValueError`.
- `search`:
  1. Validate: blank/whitespace `query` -> `ValueError`; `max_results < 1` -> `ValueError`.
  2. **Throttle:** before every search except the very first one made by this client, call `sleep_fn(delay_seconds)`.
     Skip the sleep call entirely if `delay_seconds == 0`.
  3. Attempt loop (up to `max_attempts`): `with self._ddgs_factory() as ddgs: raw = list(ddgs.text(query, max_results=max_results))`.
     The `list(...)` is **inside** the `with` block so the results are fully read before the client closes.
  4. If a `DDGSException` is raised and `is_no_results_error` is true: return `[]` immediately. No retry.
  5. If another `DDGSException` is raised and attempts remain: log a WARNING (query, attempt number, error), call
     `sleep_fn(delay_seconds * attempt_number)` (skip if delay is 0), and retry.
  6. If attempts are exhausted: `raise SearchError(f"Search failed for {query!r}: {exc}", query=query) from exc`.
  7. Exceptions that are NOT `DDGSException` (for example `ValueError` or `KeyError` from a bug) must propagate **unchanged**.
  8. Normalize each raw dict with `SearchHit.from_ddgs`; drop hits with an empty `url` (DEBUG log). Return `list[SearchHit]`.
  9. Logging: DEBUG on query start (query, max_results), DEBUG on completion (raw count, kept count, elapsed ms),
     DEBUG with `exc_info=True` for each caught exception. WARNING on retry. No INFO or ERROR in this module
     (the collector decides what is user-visible).

## Step 1: RED. Tests (`NoNetworkTestCase`; use `FakeDDGSFactory`; `sleep_fn` is a recording stub, never real sleeping)

- `is_no_results_error` table: `DDGSException("No results found.")` True; `"no results found"` lowercase True; leading whitespace True;
  `DDGSException("Rate limited")` False; `ValueError("No results found.")` False; `DDGSException("")` False.
- success: hits normalized into `SearchHit` with the right fields and types, in order.
- passes `max_results` through (check `factory.calls`).
- no results -> `[]`, exactly **one** session opened (no retry), no sleep.
- transient error then success -> returns hits; two sessions opened; sleep called once with `delay_seconds * 1`; WARNING logged.
- persistent error -> `SearchError`; `__cause__` is the original `DDGSException`; `.query` set; message contains the query; session count == `max_attempts`.
- sessions closed: `sessions_opened == sessions_closed` after success, no-results, and failure.
- throttle: first search no sleep; second search sleeps `delay_seconds`; `delay_seconds=0` never calls `sleep_fn`.
- non-DDGS exception (`ValueError("bug")` via `add_error`) propagates unchanged and is NOT retried.
- hits missing `href` are dropped; missing `title`/`body` become `""`.
- validation: blank query, whitespace query, `max_results=0`, `delay_seconds=-1`, `max_attempts=0` -> `ValueError`.
- logging: DEBUG contains the query string (`assertLogs("researchlib.search_client", "DEBUG")`).
- one test that constructs `SearchClient()` with defaults and checks `delay_seconds == 1.0`/`max_attempts == 2`
  via public behavior or documented attributes. Do NOT make a real search.

## Steps 2 and 3

GREEN, then REFACTOR (extract `_run_once`, `_sleep_before_retry`; keep `search` readable).

<!-- FILE: 06-extractors.md -->
# TASK 06: Fact extractors (heuristic, pure functions)

**Read the shared context above first.** Depends on Task 03.

## Files

Create: `researchlib/extractors.py`, `tests/test_extractors.py`.

## Principles

- Extractors are **pure**: input is `Sequence[SearchHit]`, output is `list[Fact]`. No I/O, no network, no clock
  (the current year is injected).
- They search the text `title + " " + snippet` of each hit. Every `Fact` carries `evidence_url=hit.url` and
  `evidence_snippet=truncate(snippet, 200)`.
- They are deliberately **conservative**: prefer a miss to a wrong fact. The report labels all facts as heuristic.
- Log each accepted match at DEBUG (category, value, url) and each rejected candidate at DEBUG (reason).

## Behavior spec

**`extract_founding_years(hits, *, current_year=None)`** (default `datetime.now().year`)
- Regex: `\b(?:founded|established|est\.?)\s*(?:in|:)?\s*(\d{4})\b`, case-insensitive. So "Founded in 2015", "founded 2015", "Est. 2003", "Established: 1998" match.
- Accept only `1800 <= year <= current_year`. Out-of-range candidates are rejected (DEBUG log).
- One `Fact(FOUNDED, "2015", ...)` per distinct match. A snippet with two matches yields two facts.
- Does NOT match "since 2020" or "refounded in 2020" is out of scope. Just make sure "founded" must be a whole word.

**`extract_leaders(hits, *, company_name=None)`**
- Canonical roles: `CEO` (also "Chief Executive Officer"), `CTO`, `COO`, `CFO`, `Founder`, `Co-founder` (also "Cofounder", "Co-Founder"), `President`.
- Name = 2 or 3 consecutive capitalized words (`[A-Z][a-z]+` or `[A-Z][a-z]+-[A-Z][a-z]+` or with a middle initial `[A-Z]\.`).
- Three patterns, tried per hit: (a) `NAME, ROLE`; (b) `ROLE NAME` (role immediately followed by a name); (c) `NAME is|as (the|our|its) ROLE`.
- Value format: `"Jane Doe (CEO)"` (canonical role in parentheses).
- If `company_name` is given, discard candidates whose name equals or contains the company name (case-insensitive) or is contained in it.
- Compound titles like "Co-founder and CEO" yield one fact for the **first** role only. Document this known limitation in the docstring.

**`extract_funding(hits)`**
- Rounds: `Series [A-Z]` (letter is upper-case, followed by a word boundary, so "Series of events" does not match), `Seed`/`Pre-seed` only when followed by "round" or "funding" (normalize to `Seed`, `Pre-Seed`). Category `FUNDING_ROUND`.
- Amounts: a verb from `raised|raises|secured|secures|closed|closes|funding of` followed by `\$\d+(?:\.\d+)?\s?(?:k|K|M|B|thousand|million|billion)\b`. The value is the amount **as written** (`"$10 million"`, `"$2.5M"`). Category `FUNDING_AMOUNT`. Amounts without such a verb are NOT extracted.

**`extract_tech_keywords(hits)`**
- A module constant `TECH_PATTERNS` maps canonical name -> compiled regex. Required canonical names and rules:
  - case-insensitive: `Python`, `JavaScript`, `TypeScript`, `Java` (must not fire inside "JavaScript"), `Ruby`, `Kubernetes` (also `k8s`), `Docker`, `AWS` (also "Amazon Web Services"), `Azure`, `PostgreSQL` (also "Postgres"), `Terraform`, `Kafka`, `Redis`, `Node.js` (also "NodeJS", "node.js"), `Go` **only** as `Golang` or `Go (developer|engineer|backend|programming)`.
  - case-sensitive (ambiguous English words): `React` (also "ReactJS"), `Rust`.
- Category `TECH`, value is the canonical name, one fact per canonical name per hit. Output sorted by canonical name within a hit.
- Remove the old non-technology keywords (`github`, `linkedin`, `engineering`, `developer`).

**`dedupe_facts(facts)`**: unique by `(category, value.lower())`, keep the first (its evidence), stable order.

**`extract_all(hits, *, company_name=None, current_year=None)`**: concatenate founding, leaders, funding (rounds then amounts), tech, then `dedupe_facts`. Empty input -> `[]`.

## Step 1: RED. Tests (`NoNetworkTestCase`; table-driven with `subTest`)

For each extractor, build hits with `SearchHit(...)` directly. Required cases:

- **Founding:** the five positive phrasings above; `current_year=2026` boundary tests (2026 accepted, 2027 rejected, 1800 accepted, 1799 rejected);
  "founded in 1492" rejected; "Confounded in 2015" NOT matched; two years in one snippet -> two facts in order;
  year found in the *title* only; no match -> `[]`; evidence_url/evidence_snippet populated and snippet truncated at 200 chars.
- **Leaders:** each of the three patterns; each canonical role incl. long-form; `Co-founder and CEO` -> first role only;
  "the CEO said" -> none; "CEO of the year" -> none; `company_name="Acme Freight"` excludes "Acme Freight, CEO"; names with a middle initial
  (`Jane Q. Doe, CTO`); hyphenated surname; lowercase names -> none.
- **Funding:** "raised $10 million in Series A" -> ROUND `Series A` and AMOUNT `$10 million`; "$2.5M seed round" -> ROUND `Seed`, no amount;
  "closes $40M" -> amount `$40M`; "$10 million revenue" -> nothing; "Series of events" -> nothing; "Series b" lowercase letter -> nothing;
  "Pre-seed funding" -> `Pre-Seed`.
- **Tech:** the sentence "Our engineers use Python, JavaScript, React, and Node.js" -> exactly those four, sorted; `JavaScript` alone does NOT yield `Java`;
  `go-to-market strategy` and "let's go" yield no `Go`; "Golang" and "Go developer" yield `Go`; `k8s` -> `Kubernetes`; "Amazon Web Services" -> `AWS`;
  "we react quickly" (lowercase) yields no `React`; "Postgres" -> `PostgreSQL`; `Rust` yes, "rusty" no.
- **dedupe_facts:** duplicates differing only by case; first evidence kept; order stable; different categories with same value are both kept.
- **extract_all:** combined fixture hit yields facts in the documented category order; empty input; logging at DEBUG for an accepted match.

## Steps 2 and 3

GREEN, then REFACTOR (compile regexes once at module level; name each pattern; no function over 40 lines).
In the mutation check, change the year boundary `<=` to `<` and confirm a test fails.

<!-- FILE: 07-collector.md -->
# TASK 07: Profile collector (orchestration)

**Read the shared context above first.** Depends on Tasks 04, 05, 06 (and 03).

## Files

Create: `researchlib/collector.py`, `tests/test_collector.py`.
You may edit **`tests/fixtures.py::acme_factory` only** if a rule needs adjusting.

## Behavior spec: `ProfileCollector.collect(company_name, location=None, website_override=None) -> ResearchResult`

1. Raise `ValueError` if `company_name` is blank after stripping. Store the stripped name.
2. If `website_override` is given, `website_domain = extract_domain(website_override)` (accepts a URL or bare domain). Otherwise `None`.
3. Process `self.sources` **in order**. For each spec:
   - **Skip rule:** if `spec.requires_website` and `website_domain` is falsy: record a `SourceProfile(status=SKIPPED, query="", detail="no official website known")`.
     Do **not** call the client. Log WARNING.
   - Otherwise `query = build_query(spec, name, location, website_domain)`; log INFO "source start".
   - `hits = client.search(query, spec.max_results)`. Catch **only** `SearchError`: record `status=ERROR`, `detail=str(exc)`, `hits=()`. Log WARNING, and DEBUG with `exc_info=True`.
   - Post-process: `allowed = (website_domain,) if spec.requires_website else spec.allowed_domains`; then
     `filter_hits_by_domain`, then `dedupe_hits`.
   - Status: `OK` if the processed hits are non-empty; else `EMPTY`. For EMPTY set `detail` to `"0 raw hits"` or
     `"<N> raw hits, 0 after domain filtering"` as appropriate. Log WARNING for EMPTY.
   - INFO "source finish" with key, status, kept-hit count, elapsed ms (measure with `time.perf_counter`; elapsed is not asserted exactly in tests).
   - **Website discovery:** after the `official_website` source (key == `OFFICIAL_WEBSITE_KEY`) completes with hits, and no override was given, set
     `website_domain = pick_official_website(processed_hits, name)`. Log INFO with the domain, or WARNING if `None`.
     If an override was given, still run this source for evidence but do NOT replace the override domain.
4. `facts = extract_all(all OK hits, company_name=name)` (use the `all_hits` of a provisional result, or collect hits directly).
5. Return `ResearchResult(company_name=name, location=location-or-None (stripped, empty -> None), website_domain=..., generated_at=self._now_fn(), profiles=tuple(...), facts=tuple(facts))`.
6. Log an INFO run summary: counts per status, total hits, number of facts, website domain.
7. Non-`SearchError` exceptions propagate (they are bugs).

Default `now_fn` returns `datetime.now(timezone.utc)`.

## Step 1: RED. Tests (`NoNetworkTestCase`; `SearchClient(factory, delay_seconds=0, sleep_fn=recording stub)` over `acme_factory()` or a hand-scripted `FakeDDGSFactory`)

Use `now_fn=lambda: datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)`. Use a **short custom `sources`** list for focused tests, and the full `DEFAULT_SOURCES` only in the end-to-end tests.

- happy path (full defaults on the Acme fixtures): 12 profiles in `DEFAULT_SOURCES` order, all `OK`; `website_domain == "acmefreight.com"`; `generated_at` equals the injected time.
- website discovery feeds later queries: queries for `website_*` sources contain `site:acmefreight.com`, and those queries are issued **after** the official-website query (check order via `factory.queries`).
- no website found (official source returns only aggregator hits): `website_domain is None`; all three `website_*` profiles `SKIPPED` with the exact detail string; the factory never received a `site:` + domain query for them; a WARNING was logged.
- `website_override="https://www.override.io/x"` -> domain `override.io`; queries use `site:override.io`; the override is NOT replaced by the discovered domain even though the official source returns `acmefreight.com`.
- a `SearchError` source (script a persistent `DDGSException`) -> that profile `ERROR` with detail containing the query; other sources still processed; result not `all_failed`.
- every source errors -> `result.all_failed is True`, `has_hits is False`, no exception raised.
- `add_no_results` -> status `EMPTY`, detail `"0 raw hits"`, no ERROR.
- domain filtering: the `linkedin` source returns one linkedin hit and one off-domain hit -> only the linkedin hit remains; if ALL are off-domain -> `EMPTY` with detail `"2 raw hits, 0 after domain filtering"`.
- de-duplication: two hits with URLs differing only by trailing slash -> one hit kept.
- location: with `location="Seattle"` the official-website query contains `Seattle` and the `wikipedia` query does not (use `DEFAULT_SOURCES`); with no location neither does. Whitespace-only location -> `result.location is None`.
- facts: from the Acme fixtures `extract_all` results appear: a `FOUNDED` fact `"2015"`, a `LEADER` fact `"Jane Doe (CEO)"`, a `FUNDING_ROUND` `"Series A"`, a `TECH` fact `"Python"`.
- facts only come from OK profiles (an ERROR profile contributes none).
- blank `company_name` -> `ValueError`. Company name is stripped in the result.
- a non-`SearchError` exception from the client (`ValueError` raised by a stub client) propagates.
- logging: INFO message containing the source key for start and finish; WARNING for skipped; INFO summary mentions the website domain.
- custom `sources` argument is honored (only those queries issued).

## Steps 2 and 3

GREEN, then REFACTOR (extract `_collect_one(spec, ctx)`, `_resolve_allowed_domains`, `_summarize`; keep `collect` under ~40 lines).
Mutation check suggestion: remove the `dedupe_hits` call; confirm the dedupe test fails.

<!-- FILE: 08-report.md -->
# TASK 08: Markdown report renderer and writer

**Read the shared context above first.** Depends on Task 03 (models, textutil). Independent of Task 07.

## Files

Create: `researchlib/report.py`, `tests/test_report.py`, `tests/golden/acme_freight_report.md`.

## Report format (exact; the reading agent relies on stable structure)

Rules:
- Strings in front matter are double-quoted, with `\` and `"` escaped. `None` renders as `null`. Counts are bare integers.
- `generated_at` is `result.generated_at.isoformat()` and is quoted.
- Section order is fixed. Source sections follow `result.profiles` order. Facts are listed in `result.facts` order, grouped by category.
- All free text (titles, snippets, details, queries in the table) goes through `md_escape`. The inline-code `Query:` line is NOT escaped but any backtick in it is replaced with `'`.
- The document ends with exactly one trailing newline.

```
---
company: "Acme Freight"
location: "Seattle"
website_domain: "acmefreight.com"
generated_at: "2026-01-15T10:30:00+00:00"
tool: "company_research.py"
sources_attempted: 12
sources_ok: 9
sources_empty: 1
sources_error: 1
sources_skipped: 1
total_hits: 31
---

# Company Research: Acme Freight

## How to read this document

This report was assembled automatically from web search results (DuckDuckGo). Each "Source" section contains raw search hits (title, URL, snippet) and is the primary evidence. The "Extracted facts" section was produced by simple pattern matching and may be wrong or incomplete, so check each fact against its linked source. A source with status `error`, `empty`, or `skipped` means data is missing; it is not evidence that the information does not exist.

## Extracted facts (heuristic)

### Founded
- 2015 (source: https://example.com/a)

### Leadership
- Jane Doe (CEO) (source: https://example.com/b)

### Funding
- Series A (source: https://example.com/c)
- $10 million (source: https://example.com/c)

### Technology mentions
- Python (source: https://example.com/d)

## Source: Official Website (official_website)

- Status: ok
- Query: `"Acme Freight" official website Seattle`
- Hits: 2

### 1. Acme Freight | Home
- URL: https://acmefreight.com
- Snippet: Acme Freight moves goods.

### 2. Title two
- URL: https://acmefreight.com/about
- Snippet: (no snippet)

## Source: Wikipedia (wikipedia)

- Status: error
- Query: `site:wikipedia.org "Acme Freight" company`
- Detail: Search failed for ...

## Collection log

| Source | Status | Hits | Detail |
|--------|--------|------|--------|
| official_website | ok | 2 | |
| wikipedia | error | 0 | Search failed for ... |
```

Details:
- `sources_error` counts `ERROR` profiles; `sources_attempted` is the total number of profiles (including skipped).
- An empty facts category prints `_None found._` as its only line. The categories **Founded, Leadership, Funding,
  Technology mentions** always appear, in that order. Funding contains rounds then amounts, in `result.facts` order.
- Fact line format: `- {md_escape(value)} (source: {evidence_url})`.
- Source section header: `## Source: {md_escape(label)} ({spec_key})`.
- For `OK` profiles list each hit as `### {n}. {md_escape(title) or "(untitled)"}` then `- URL: {url}` then
  `- Snippet: {md_escape(snippet) or "(no snippet)"}`, with a blank line between hits. Numbering starts at 1.
- For non-OK profiles, omit the hit list. Show `Status`, `Query` (omit the line when the query is empty, e.g. skipped), and `Detail` (omit when empty).
- The "Hits" line appears for OK profiles only.
- The collection log has one row per profile. The `Hits` column is `len(hits)`. The `Detail` cell is `md_escape(detail)`.
- Title with no `company_name` content is not possible (the collector validates), so you need not handle a blank company.

## Functions

- `report_filename(company_name)` -> `f"{slugify(company_name)}_research.md"`.
- `render_markdown(result)` -> the string above. Pure and deterministic.
- `write_report(result, output_dir)` -> creates `output_dir` (parents included), writes UTF-8 with `\n` newlines, **overwrites** an existing file,
  returns the `Path`. Logs INFO (path, bytes written) and DEBUG (character count per top-level section).
  Raises whatever the OS raises; logs ERROR with `exc_info=True` first, then re-raises.

## Step 1: RED. Tests (`NoNetworkTestCase`; build `ResearchResult` objects with a helper in the test module)

**Hand-write the golden file `tests/golden/acme_freight_report.md` first, from the format above, without running any code.**
Use a result with: location `Seattle`, one OK profile with 2 hits (one with an empty snippet), one ERROR profile, one EMPTY profile
(detail `2 raw hits, 0 after domain filtering`), one SKIPPED profile (detail `no official website known`), and one fact in each
category (use two funding facts: a round and an amount). Fixed `generated_at = 2026-01-15T10:30:00+00:00`.

Tests:
- `test_render_matches_golden_file`: `render_markdown(result) == golden file contents`. On failure, show a unified diff in the message (`difflib.unified_diff`).
- front matter: each key/value for a second, simpler result (location `None` -> `null`; quote and backslash in company name `He said "hi" \ ok` are escaped).
- counts: `sources_*` and `total_hits` correct for mixed statuses.
- empty facts: all four categories present with `_None found._`, in order.
- per-status rendering: OK shows Hits and entries; ERROR shows Detail and no hits; SKIPPED has no Query line; EMPTY shows Detail.
- escaping: title containing `|`, `[x]`, `*bold*`, newline; snippet with newlines is a single line; backticks in query replaced by `'`.
- empty title -> `(untitled)`; empty snippet -> `(no snippet)`.
- determinism: rendering twice gives identical strings; the output ends with exactly one `\n` (not two).
- table: one row per profile in order; a `|` in a detail is escaped so the row has exactly 5 unescaped pipes. Verify by splitting on unescaped pipes with a regex.
- heading structure: `[l for l in text.splitlines() if l.startswith("## ")]` equals the expected list in order.
- `report_filename`: `"Good Ship, Inc."` -> `good_ship_inc_research.md`; empty-ish name -> `company_research.md`.
- `write_report` (temp dir): creates nested missing directories; returns a `Path` ending in the expected filename; file content equals `render_markdown`;
  non-ASCII company name `Café Ünïcode` round-trips as UTF-8; second write overwrites; no `\r` in the file; INFO log contains the path.
- `write_report` failure: `output_dir` that is an existing **file** -> raises `OSError` (or a subclass) and an ERROR is logged.

## Steps 2 and 3

GREEN, then REFACTOR (one helper per section: `_render_front_matter`, `_render_facts`, `_render_source_section`, `_render_collection_log`).
Review the golden file diff by eye one last time. The golden file is the spec. Do not regenerate it from code.

<!-- FILE: 09-cli.md -->
# TASK 09: Command-line interface and entry-point shim

**Read the shared context above first.** Depends on Tasks 02, 07, 08.

## Files

Create: `researchlib/cli.py`, `tests/test_cli.py`.
Replace the contents of `company_research.py` with a thin shim (below). The old implementation is intentionally removed.

## Shim (`company_research.py`)

```python
#!/usr/bin/env python3
"""Entry point. All logic lives in researchlib.cli."""
import sys
from researchlib.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

## Behavior spec

`build_arg_parser()` arguments:

| Argument | Details |
|----------|---------|
| `company_name` (positional) | required |
| `--location`, `-l` | optional string |
| `--website` | optional URL or domain; passed as `website_override` |
| `--output-dir`, `-o` | default `search_results` |
| `--delay` | float, default `1.0`, must be `>= 0` (argparse `type` validator; error -> exit 2) |
| `-v` / `--verbose` | count; `-v` = INFO, `-vv` = DEBUG |
| `-q` / `--quiet` | `store_true`; ERROR only. Mutually exclusive with `-v` |
| `--log-file` | optional path; receives DEBUG logs regardless of `-v` |

`main(argv=None, *, client=None, now_fn=None) -> int`:

1. Parse args (`argv=None` -> `sys.argv[1:]`).
2. `verbosity = -1 if quiet else args.verbose`; call `configure_logging(verbosity, args.log_file)`.
   Wrap the rest of the function in `try/finally: reset_logging()` so handlers never leak between runs or tests.
3. INFO log: run start with the parsed options.
4. `client = client or SearchClient(delay_seconds=args.delay)`; `collector = ProfileCollector(client, now_fn=now_fn) if now_fn else ProfileCollector(client)`.
5. `result = collector.collect(args.company_name, args.location, args.website)`.
6. `path = write_report(result, args.output_dir)` (always write, even when there is no data, so the reader sees the gaps).
7. Print **only** `str(path)` followed by a newline to **stdout**. Nothing else is ever printed to stdout.
8. Return an exit code:
   - `3` if `result.all_failed` (log ERROR "all sources failed"),
   - `1` if not `result.has_hits` (log WARNING),
   - `0` otherwise.
9. A blank company name (`""`, `"  "`) -> `parser.error(...)` -> exit code 2.
10. `KeyboardInterrupt` -> log WARNING, return `130`.
11. Do not catch other exceptions (let them show a traceback), but make sure logging is reset.

## Step 1: RED. Tests (`NoNetworkTestCase`)

Helper in the test module: `run_main(argv, factory)` that builds `SearchClient(factory, delay_seconds=0, sleep_fn=lambda s: None)`,
patches `sys.stdout`/`sys.stderr` with `StringIO`, calls `main(argv, client=..., now_fn=fixed)`, and returns `(code, stdout, stderr)`.
Always pass `-o <tempdir>`.

- parser defaults: output dir `search_results`, delay `1.0`, verbose `0`, location/website/log-file `None`.
- parser flags: `-l`, `--website`, `-o`, `--delay 0.5`, `-vv` -> `verbose == 2`, `-q`.
- parser errors (assert `SystemExit` with code 2): no company; `--delay -1`; `--delay abc`; `-q -v` together.
- happy path with `acme_factory()`: exit code 0; stdout is exactly `"<tempdir>/acme_freight_research.md\n"`; the file exists and starts with `---\ncompany: "Acme Freight"`.
- default verbosity prints **nothing** to stderr on a fully successful run.
- `-v` shows INFO lines (source start/finish) on stderr; stdout unchanged.
- `-vv` shows DEBUG lines including at least one query string; `--log-file` (in a temp dir) gets DEBUG lines even without `-v`.
- `-q` suppresses WARNINGs (use a run that would warn, e.g. an EMPTY source) but ERROR still shows when all sources fail.
- exit code 1: every query `add_no_results` -> report still written, content shows `empty` statuses, stdout is still the path.
- exit code 3: every query raises `DDGSException("boom")` -> report still written with `error` statuses; ERROR logged.
- blank name `""` -> exit code 2.
- `--location Seattle` appears in the official-website query (`factory.queries`) and in the report front matter.
- `--website acmefreight.com` produces `site:acmefreight.com` queries even if the official search returns nothing useful.
- logging is reset after `main` returns, including when it raises (patch the collector to raise `RuntimeError`, `assertRaises`, then check `logging.getLogger("researchlib").handlers == []`).
- `KeyboardInterrupt` raised by the stub client -> return code 130.
- shim: `import company_research` and assert `company_research.main is researchlib.cli.main`.
- one subprocess test: `[sys.executable, "company_research.py", "--help"]` exits 0 and stdout contains `company_name`. (This is the only subprocess test. It makes no network call.)

## Steps 2 and 3

GREEN, then REFACTOR (small helpers: `_exit_code_for(result)`, `_parse_delay`). Confirm that a plain `grep -n "print(" researchlib/` finds
only the single stdout print in `cli.py`; include that grep output in your report.

<!-- FILE: 10-cleanup-docs-verification.md -->
# TASK 10: Cleanup, documentation, live smoke test, and final verification

**Read the shared context above first.** Depends on all earlier tasks. This task adds docs and an opt-in live test,
and verifies the whole system. Production logic changes are allowed only to fix defects you find. Each defect needs a
failing test first (red/green/refactor applies).

## Files

Create: `README.md`, `docs/FUTURE_DISAMBIGUATION.md`, `tests/test_live_smoke.py`.

## Part A: Live smoke test (opt-in, never run by default)

`tests/test_live_smoke.py`:
- Inherits plain `unittest.TestCase` (NOT `NoNetworkTestCase`).
- Decorated with `@unittest.skipUnless(os.environ.get("RUN_LIVE_TESTS") == "1", "set RUN_LIVE_TESTS=1 to run live network tests")`.
- One test: run `main(["Anthropic", "-o", <tempdir>, "--delay", "1.5", "--log-file", <tempdir>/run.log])` with a real client.
  Assert only **structure**, because live results vary: exit code in `{0}`; the report file exists; it contains the headings
  `## How to read this document`, `## Extracted facts (heuristic)`, `## Collection log`; the log file is non-empty;
  at least 3 sources have status `ok` in the front matter count (`sources_ok: N` with N >= 3).
- A comment at the top explains that this test is inherently flaky (rate limits, search engine changes) and is not part of CI.

Verify that the default run SKIPS it: `python3 -m unittest discover -s tests -t . -v` shows `skipped`.

## Part B: Documentation

`README.md` must contain these sections (concise, accurate, copy-pasteable commands):
1. What it does (3 sentences).
2. Install: `pip install -r requirements.txt`.
3. Usage with examples: basic, `--location`, `--website`, `-vv --log-file logs/run.log`.
4. Exit codes table: 0, 1, 2, 3, 130, with meaning.
5. Output: stdout is the report path only; logs go to stderr; where the report is written.
6. Report format overview (front matter keys, section order, the meaning of statuses `ok/empty/error/skipped`).
7. How to add a new source: add a `SourceSpec` to `DEFAULT_SOURCES`, add a test in `tests/test_sources.py`, and extend `acme_factory`.
8. Logging guide: which level shows what (copy the table from the shared standards, condensed).
9. Testing: commands for the whole suite, one module, `-W error`, coverage, and the live test.
10. Troubleshooting: empty results (rate limiting; try `--delay 3`; try `-vv` and read the queries), "all sources failed" (network or the library changed; check `pip show ddgs`).

`docs/FUTURE_DISAMBIGUATION.md`: record why disambiguation was deferred and how it should come back. Content to include:
the problems of the old function (single query; results not grouped by company; weak `'inc' in title` filter; location used only to discard;
`main()` silently picked result `[0]`); the proposed design (gather several queries -> group hits by registrable domain -> score candidates
by name-in-domain, name-in-title, location match, number of independent hits, "founded/headquartered" mentions -> decide `unique | ambiguous | not_found`
with named margin constants); and the integration point (run before `ProfileCollector.collect`, feeding `website_override`). State that
it must be built test-first with pure functions for grouping, scoring, and deciding.

## Part C: Verification checklist (run and record each result in your report)

1. **Clean offline run:** disable network if possible (or rely on `NoNetworkTestCase`). Run
   `python3 -W error -m unittest discover -s tests -t . -v`. All pass; live test skipped; no warnings (watch for `ResourceWarning`).
2. **Determinism:** run the full suite 3 times in a row. Identical counts. Record the total run time (it should be under ~5 seconds).
3. **Test isolation:** run each test module alone (`python3 -m unittest tests.test_sources`, and so on). Every module passes standalone
   (this catches hidden inter-test dependencies). Also run with tests in reverse order if you can:
   `python3 -m unittest discover -s tests -t . --reverse`? (Not all Python versions support it; skip with a note if unsupported.)
4. **No stray files:** after the run, `git status` (or `ls`) shows no files created in the project root by tests (no `test_output/`, no `search_results/`).
5. **Coverage:** `pip install coverage` (dev only, do NOT add to requirements.txt), then
   `python3 -m coverage run --source=researchlib -m unittest discover -s tests -t . && python3 -m coverage report -m`.
   Target is at least 90% line coverage for `researchlib`. For any uncovered lines, either add a test (red/green) or list them in the report with a reason.
6. **Mutation spot checks:** perform these five, one at a time, run the suite, confirm a failure, and revert each exactly:
   (a) in `extractors.py` flip the year upper bound `<=` to `<`; (b) in `collector.py` remove the `dedupe_hits` call;
   (c) in `search_client.py` move the `list(...)` call outside the `with` block (use `str_replace`, confirm the fake detects the unclosed-session ordering or
   explain why the existing tests cannot catch it, then add a test if they cannot); (d) in `cli.py` change the all-failed exit code `3` to `2`;
   (e) in `report.py` drop `md_escape` from the snippet. If any mutation survives (no test fails), write the missing test (red/green) and re-run.
7. **Logging review:** run the tool's pipeline once via the cli test helper at `-vv` and paste ~20 representative log lines into the report. Confirm each
   level is used as the standards say (DEBUG queries and drops; INFO source start/finish and summary; WARNING skipped/empty). Fix mismatches.
8. **Grep checks (paste the output):**
   `grep -rn "print(" researchlib/` (only `cli.py` stdout print), `grep -rn "except:" researchlib/` (none), `grep -rn "logger\.\(debug\|info\|warning\|error\)(f\"" researchlib/` (none).
9. **Live check (optional; only if a network is available):**
   `RUN_LIVE_TESTS=1 python3 -m unittest tests.test_live_smoke -v`, then
   `python3 company_research.py "Anthropic" -vv --log-file logs/manual.log -o search_results` and paste the first 60 lines of the produced report.
   If a source is `empty` or `error`, report which and what the DEBUG log said. Do NOT change query templates without the owner's approval; propose changes in your report.

## Done when

All checklist items are recorded in the TASK REPORT, the suite is green and deterministic, README and the future-work doc exist, and no mutation survives.
