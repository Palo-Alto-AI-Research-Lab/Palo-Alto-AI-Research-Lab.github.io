# -*- coding: utf-8 -*-
"""Offline test for build_site.py -- no network, no writes to the site.

Run:  python tools/_test_build_site.py     (exit 0 = pass, 1 = fail)

It feeds the renderer fake API rows covering all three states and asserts the
page tells the truth about them. It must go RED if the renderer starts hiding
closed PRs, miscounts, or drops the honest "none merged" line.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_site as B

def row(repo, num, state, merged=None, title="t", date="2026-07-24"):
    return {"repository_url": "https://api.github.com/repos/" + repo, "number": num,
            "title": title, "html_url": "https://github.com/%s/pull/%d" % (repo, num),
            "state": state, "created_at": date + "T00:00:00Z",
            "pull_request": {"merged_at": merged}}

fails = []
def ck(name, cond):
    print(("  PASS " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)

# --- 1. all three states are rendered, none swallowed -------------------
items = [row("openai/openai-cookbook", 1, "open"),
         row("deepset-ai/haystack", 2, "closed"),
         row("anthropics/skills", 3, "closed", merged="2026-07-25T00:00:00Z"),
         row("Jenqyang/Awesome-AI-Agents", 4, "open")]
h = B.render(items, "2026-07-29 00:00 UTC")
ck("closed PR is visible on the page", "deepset-ai/haystack" in h)
ck("merged PR is labelled merged", 'st-merged">merged' in h)
ck("open PR is labelled open", 'st-open">open' in h)
ck("closed PR is labelled closed", 'st-closed">closed' in h)
ck("every PR is listed (4 items)", h.count('class="item"') == 4)
ck("tally shows 4 pull requests", "<b>4</b><span>pull requests</span>" in h)
ck("tally counts 1 merged", "<b>1</b><span>merged</span>" in h)
ck("awesome-list goes to the lists section", B.classify("Jenqyang/Awesome-AI-Agents") == "list")
ck("vendor repo goes to the code section", B.classify("openai/openai-cookbook") == "code")
ck("nav is embedded in the generated page", '<div class="sitenav">' in h)
for l in B.REQUIRED_LINKS:
    ck("generated page links %s" % l, 'href="%s"' % l in h)

# --- 2. with nothing merged, the page must SAY so, not stay silent ------
h2 = B.render([row("openai/openai-cookbook", 1, "open")], "2026-07-29 00:00 UTC")
ck("zero merged -> honest 'None merged yet' line", "None merged yet" in h2)
ck("some merged -> no 'None merged yet' line", "None merged yet" not in h)

# --- 3. titles are escaped, not injected -------------------------------
h3 = B.render([row("a/b", 1, "open", title='<script>x</script>&')], "s")
ck("PR title is HTML-escaped", "&lt;script&gt;" in h3 and "<script>x" not in h3)

print("\n%d/%d checks passed" % (13 + len(B.REQUIRED_LINKS) - len(fails) + 3 - 3,
                                 13 + len(B.REQUIRED_LINKS)))
if fails:
    print("FAILED:", fails)
sys.exit(1 if fails else 0)
