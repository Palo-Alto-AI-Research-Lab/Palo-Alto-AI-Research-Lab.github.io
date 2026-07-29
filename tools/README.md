# tools/ — how the generated parts of this site are built

Most of this site is hand-written HTML. Two things are **generated** and must not be
hand-edited, because the generator overwrites them:

- `contributions/index.html` — the public list of every pull request opened from this account
- the footer link block (`<div class="sitenav">`) on every page
- the `<span id="prcount">` counter on the one-pager

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

**Honesty contract.** States are printed exactly as the API reports them: open, closed and merged
all appear. When nothing is merged the page says so in words. Do not add filtering that hides
closed PRs — `_test_build_site.py` exists specifically to fail if you do.

## _test_build_site.py

Offline test, no network, writes nothing. Feeds the renderer fake rows covering all three states
and asserts the page tells the truth about them.

    python tools/_test_build_site.py     # exit 0 = pass

Verified 2026-07-29 to go red on a mutant that hid closed PRs (3 of 18 checks failed), so a green
run means something.
