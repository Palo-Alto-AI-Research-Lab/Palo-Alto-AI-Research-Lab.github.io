# tools/ — how the generated parts of this site are built

Most of this site is hand-written HTML. Two things are **generated** and must not be
hand-edited, because the generator overwrites them:

- `contributions/index.html` — the public list of every pull request opened from this account
- the footer link block (`<div class="sitenav">`) on every page
- the `<span id="prcount">` counter on the one-pager
- `sitemap.xml` — every page served from this host, including project pages that live in other
  repositories (`/claude-bible/`, `/verbatim-citation-gate/`, `/the-journey/`, `/cofounder/`)

## build_site.py

**What it does.** Asks the GitHub search API for `is:pr author:Palo-Alto-AI-Research-Lab`,
renders the contributions page from the answer, and re-injects the same footer link block into
every page so the navigation can never drift page-to-page.

**Input.** The public GitHub search API. `GITHUB_TOKEN` is optional — it only raises the rate
limit. Without it the anonymous limit (10 searches/minute) is plenty for one run.

**Output.** `contributions/index.html`, the footer block on all pages listed in `PAGES`, and the
counter on `index.html`. Nothing else is touched.

**How to run.**

    python tools/build_site.py           # regenerate everything, then verify
    python tools/build_site.py --nav     # only refresh the footer nav (no network)
    python tools/build_site.py --check   # verify only, change nothing

Exit code 0 means every page carries the nav exactly once and all required links resolve;
exit 1 means something is broken and the message names the page and the reason.

**Who runs it.** A human before a commit, and the weekly `cv-scholar-hardening-weekly` routine.
It is safe to run any number of times — it is idempotent, a second run reports
`nothing (already current)`.

**What breaks it, and how you would notice.**

| Symptom | Cause | Fix |
|---|---|---|
| `refusing to write an empty contributions page` | API returned nothing (rate limit, network, renamed account) | Wait a minute and rerun, or set `GITHUB_TOKEN`. The old page is left untouched on purpose — a blank page would silently claim we contribute nothing. |
| `no CSS anchor in <page>` | someone renamed the `.foot` / `footer` CSS rule the injector anchors to | Restore the rule name, or update `inject_nav`. |
| `FAIL <page> missing /...` | a page lost its footer block | Rerun without `--check`. |
| Page shows a stale date | nobody ran the generator | Rerun it; the footer prints the generation time so staleness is visible, not hidden. |

### The sitemap half (added 2026-08-01)

**Why it is generated.** It was hand-kept, and it rotted exactly as hand-kept files do: it was
missing `/contributions/` — a page linked from this site's own header — and every project page
served from the same host out of another repository. Those pages existed with nothing pointing a
crawler at them.

**How the dates are decided.** `lastmod` for a page in this repo is the date of the last commit
touching that file (`git log -1 --format=%cs`). For a project page it is the date of the last
commit touching that repo's `docs/` directory, read from the public API. **If either lookup
fails, the entry is written with no `lastmod` at all** — an entry with an unknown date is still a
valid entry; an entry with a guessed date is a lie to a crawler.

**Adding a page.** One line in `OWN_PAGES` (page in this repo) or `PROJECT_PAGES` (page served
from another repo of the account) — nothing else. `--check` walks the same lists and fails if the
sitemap does not match them exactly.

**Every URL here also needs a live check.** `~/.claude/scripts/public_surface_audit.py`
(`EXTRA_SURFACES`) fetches each of these URLs anonymously every night. Without that line a project
page whose Pages got switched off stays advertised to crawlers forever and nobody finds out.

| Symptom | Cause | Fix |
|---|---|---|
| `FAIL sitemap.xml does not list <url>` | a page was declared but the file was not regenerated | Rerun without `--check`. |
| `FAIL sitemap.xml lists an undeclared url` | someone hand-edited the file | Do not hand-edit it; rerun the generator. |
| `does not parse as XML` / `duplicate url(s)` | file truncated or edited by hand | Rerun the generator. |
| `sitemap: no date for <repo>` | API rate limit or network | Harmless — that entry ships without `lastmod`. Rerun later if you want the date. |

**Honesty contract.** States are printed exactly as the API reports them: open, closed and merged
all appear. When nothing is merged the page says so in words. Do not add filtering that hides
closed PRs — `_test_build_site.py` exists specifically to fail if you do.

## _test_build_site.py

Offline test, no network, writes nothing. Feeds the renderer fake rows covering all three states
and asserts the page tells the truth about them.

    python tools/_test_build_site.py     # exit 0 = pass

Verified 2026-07-29 to go red on a mutant that hid closed PRs (3 of 18 checks failed), so a green
run means something.
