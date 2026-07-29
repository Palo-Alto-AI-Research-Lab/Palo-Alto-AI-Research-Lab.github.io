# -*- coding: utf-8 -*-
"""Rebuild the generated parts of this site.

  python tools/build_site.py            # contributions page + footer nav on every page
  python tools/build_site.py --nav      # only re-inject the footer nav
  python tools/build_site.py --check    # verify only, change nothing (exit 1 if broken)

Contributions data comes from the public GitHub search API. A token is optional
(set GITHUB_TOKEN to raise the rate limit); without one the anonymous limit is
10 searches/minute, which is plenty for a single run.

Honesty rule: states are printed exactly as GitHub reports them. Never hand-edit
contributions/index.html -- it is generated, your edit would be overwritten.
"""
import io, json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNT = "Palo-Alto-AI-Research-Lab"

PAGES = ["index.html", "scholar/index.html", "scholar/publications/index.html",
         "scholar/ru/index.html", "scholar/writing/index.html", "contributions/index.html"]
REQUIRED_LINKS = ["/resume.pdf", "/resume.json", "/scholar/", "/scholar/publications/", "/contributions/"]

NAV_EN = ('<div class="sitenav"><b>Anton Dziatkovskii</b> &middot; '
          '<a href="/">Candidate one-pager</a> &middot; '
          '<a href="/resume.pdf">Resume (PDF, ATS)</a> &middot; '
          '<a href="/resume.json">Resume (JSON)</a> &middot; '
          '<a href="/scholar/">Academic profile</a> &middot; '
          '<a href="/scholar/publications/">All publications</a> &middot; '
          '<a href="/contributions/">Open-source contributions</a> &middot; '
          '<a href="/scholar/writing/">Writing</a> &middot; '
          '<a href="/scholar/ru/">Rus</a> &middot; '
          '<a href="https://github.com/Palo-Alto-AI-Research-Lab">GitHub</a></div>')
NAV_RU = ('<div class="sitenav"><b>Антон Дзятковский</b> &middot; '
          '<a href="/">Главная страница</a> &middot; '
          '<a href="/resume.pdf">Резюме (PDF, ATS)</a> &middot; '
          '<a href="/resume.json">Резюме (JSON)</a> &middot; '
          '<a href="/scholar/">Академический профиль</a> &middot; '
          '<a href="/scholar/publications/">Все публикации</a> &middot; '
          '<a href="/contributions/">Вклад в открытый код</a> &middot; '
          '<a href="/scholar/writing/">Эссе</a> &middot; '
          '<a href="https://github.com/Palo-Alto-AI-Research-Lab">GitHub</a></div>')

CSS_DOC = ("  .sitenav{margin-top:3rem;padding-top:1rem;border-top:1px solid #e2ded3;"
           "font-size:.9rem;line-height:1.9}\n  .sitenav a{margin:0 2px}\n")
CSS_INDEX = ("  .sitenav { margin-top:44px; padding-top:14px; border-top:1px solid var(--border);"
             " font-size:.92em; line-height:2; }\n  .sitenav a { margin:0 2px; }\n")


# ---------------------------------------------------------------- fetch
def fetch_prs():
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    hdr = {"Accept": "application/vnd.github+json", "User-Agent": "palo-alto-lab-site"}
    if tok:
        hdr["Authorization"] = "Bearer " + tok
    items, page = [], 1
    while page <= 10:
        url = ("https://api.github.com/search/issues?q=is:pr+author:%s"
               "&per_page=100&sort=created&order=desc&page=%d" % (ACCOUNT, page))
        req = urllib.request.Request(url, headers=hdr)
        d = json.load(urllib.request.urlopen(req, timeout=45))
        items += d["items"]
        if len(items) >= d["total_count"] or not d["items"]:
            break
        page += 1
        time.sleep(2)
    if not items:
        raise SystemExit("refusing to write an empty contributions page (API returned nothing)")
    return items


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def classify(repo):
    """Ecosystem lists are a different kind of contribution than code into a vendor repo."""
    return "list" if "awesome" in repo.lower() else "code"


# ---------------------------------------------------------------- render
def render(items, stamp):
    rows = []
    for i in items:
        repo = i["repository_url"].split("/repos/", 1)[1]
        merged = bool((i.get("pull_request") or {}).get("merged_at"))
        state = "merged" if merged else i["state"]
        rows.append({"repo": repo, "num": i["number"], "title": i["title"],
                     "url": i["html_url"], "state": state,
                     "date": i["created_at"][:10], "kind": classify(repo)})
    rows.sort(key=lambda r: r["date"], reverse=True)

    n = len(rows)
    n_open = sum(r["state"] == "open" for r in rows)
    n_merged = sum(r["state"] == "merged" for r in rows)
    n_closed = sum(r["state"] == "closed" for r in rows)
    n_repos = len(set(r["repo"] for r in rows))
    n_orgs = len(set(r["repo"].split("/")[0] for r in rows))

    def table(kind):
        out = []
        for r in (x for x in rows if x["kind"] == kind):
            out.append(
                '<div class="item"><div class="ln"><span class="st st-%s">%s</span> '
                '<a href="%s" target="_blank" rel="noopener"><span class="rp">%s</span> '
                '#%s</a> <span class="dt">%s</span></div>'
                '<div class="ti">%s</div></div>'
                % (r["state"], r["state"], r["url"], esc(r["repo"]), r["num"],
                   r["date"], esc(r["title"])))
        return "\n".join(out)

    merged_line = ("<b>%d merged.</b>" % n_merged if n_merged else
                   "<b>None merged yet.</b> Vendor cookbook queues are long and most of these are "
                   "still waiting for a first reviewer. One was closed with a substantive maintainer "
                   "review rather than silence &mdash; that review has been the single most useful "
                   "signal we have received so far, and it is listed below like everything else.")

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Open-source contributions &mdash; Anton Dziatkovskii</title>
<meta name="description" content="Every pull request opened from the Palo Alto AI Research Lab account into someone else's repository, with its real status. Generated from the GitHub API.">
<link rel="canonical" href="https://palo-alto-ai-research-lab.github.io/contributions/">
<style>
  body{
    background:#fdfdfd;color:#111;
    font-family:"Bitstream Charter","Iowan Old Style",Palatino,Georgia,"Times New Roman",serif;
    font-size:18px;line-height:1.55;
    max-width:47rem;margin:0 auto;padding:4rem 1.4rem 6rem;
  }
  h1{font-size:2.1rem;line-height:1.12;margin:0 0 .2rem;font-weight:600;letter-spacing:-.01em}
  .role{color:#666;font-style:italic;font-size:1.05rem;margin:0 0 1.5rem}
  a{color:#0000ee;text-decoration:none;border-bottom:1px solid transparent}
  a:hover{border-bottom-color:#0000ee}
  a:visited{color:#551a8b}
  h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.14em;color:#666;font-weight:600;margin:2.6rem 0 .8rem;padding-bottom:.35rem;border-bottom:1px solid #e2ded3}
  p{margin:0 0 1rem;max-width:65ch}
  .tally{display:flex;flex-wrap:wrap;gap:.4rem 1.6rem;margin:0 0 1.2rem;font-variant-numeric:tabular-nums}
  .tally div{white-space:nowrap}
  .tally b{font-size:1.5rem;font-weight:600;margin-right:.35rem}
  .tally span{color:#666;font-size:.85rem;text-transform:uppercase;letter-spacing:.08em}
  .item{padding:.5rem 0;border-bottom:1px solid #eee9dd}
  .item:last-child{border-bottom:none}
  .ln{font-size:.9rem}
  .rp{font-weight:600}
  .dt{color:#888;font-size:.82rem;font-variant-numeric:tabular-nums}
  .ti{color:#333;font-size:.95rem;margin-top:.1rem}
  .st{display:inline-block;min-width:4.2rem;text-align:center;font-size:.7rem;text-transform:uppercase;
      letter-spacing:.08em;padding:.1rem .4rem;border-radius:3px;border:1px solid;margin-right:.5rem;
      font-family:-apple-system,"Segoe UI",Roboto,sans-serif}
  .st-open{color:#1a7f37;border-color:#1a7f37}
  .st-merged{color:#6639ba;border-color:#6639ba}
  .st-closed{color:#8b949e;border-color:#8b949e}
  .foot{margin-top:3.2rem;padding-top:1rem;border-top:1px solid #e2ded3;color:#666;font-size:.85rem}
  .sitenav{margin-top:3rem;padding-top:1rem;border-top:1px solid #e2ded3;font-size:.9rem;line-height:1.9}
  .sitenav a{margin:0 2px}
  @media (max-width:520px){ body{padding:2.2rem 1.1rem 4rem;font-size:17px} }
</style>
</head>
<body>

<h1>Open-source contributions</h1>
<p class="role">Every pull request opened from the lab account into someone else&rsquo;s repository &mdash; open, closed and merged alike.</p>

<div class="tally">
  <div><b>%(n)d</b><span>pull requests</span></div>
  <div><b>%(n_repos)d</b><span>repositories</span></div>
  <div><b>%(n_orgs)d</b><span>organisations</span></div>
  <div><b>%(n_open)d</b><span>open</span></div>
  <div><b>%(n_merged)d</b><span>merged</span></div>
  <div><b>%(n_closed)d</b><span>closed</span></div>
</div>

<p>%(merged_line)s</p>

<p>This page is generated straight from the GitHub API by
<a href="https://github.com/%(account)s/%(account)s.github.io/blob/main/tools/build_site.py">tools/build_site.py</a>,
so it cannot quietly drift from what is actually on GitHub, and nothing can be left off it to make the
record look better.</p>

<h2>Code, recipes and evals into vendor &amp; framework repositories</h2>
%(code)s

<h2>Entries into ecosystem lists</h2>
%(lists)s

%(nav)s

<div class="foot">Generated %(stamp)s from <code>is:pr author:%(account)s</code> via the GitHub search API. Counts are whatever the API returns at generation time &mdash; not curated.</div>

</body>
</html>
""" % dict(n=n, n_repos=n_repos, n_orgs=n_orgs, n_open=n_open, n_merged=n_merged,
           n_closed=n_closed, merged_line=merged_line, account=ACCOUNT,
           code=table("code"), lists=table("list"), nav=NAV_EN, stamp=stamp)


# ---------------------------------------------------------------- nav
def inject_nav(rel):
    p = os.path.join(ROOT, rel)
    s = io.open(p, encoding="utf-8").read()
    orig = s
    nav = NAV_RU if "/ru/" in rel else NAV_EN
    is_index = (rel == "index.html")
    if ".sitenav" not in s.split("</style>")[0]:
        anchor = r"^\s*footer \{[^\n]*\n" if is_index else r"^\s*\.foot\{[^\n]*\n"
        m = re.search(anchor, s, re.M)
        if not m:
            raise SystemExit("no CSS anchor in " + rel)
        css = CSS_INDEX if is_index else CSS_DOC
        s = s[:m.end()] + css + s[m.end():]
    if '<div class="sitenav">' in s:
        s = re.sub(r'<div class="sitenav">.*?</div>', nav, s, count=1, flags=re.S)
    else:
        m = re.search(r'^\s*<footer>' if is_index else r'<div class="foot">', s, re.M)
        if not m:
            raise SystemExit("no footer anchor in " + rel)
        pad = "  " if is_index else ""
        s = s[:m.start()] + pad + nav + "\n\n" + s[m.start():]
    if s != orig:
        io.open(p, "w", encoding="utf-8").write(s)
        return True
    return False


# ---------------------------------------------------------------- check
def patch_counter(items):
    """Keep the one-pager's headline number honest by regenerating it with the page."""
    repos = len(set(i["repository_url"].split("/repos/", 1)[1] for i in items))
    txt = "%d pull requests across %d repos" % (len(items), repos)
    p = os.path.join(ROOT, "index.html")
    s = io.open(p, encoding="utf-8").read()
    new = re.sub(r'(<span id="prcount">).*?(</span>)', r'\g<1>' + txt + r'\g<2>', s, count=1, flags=re.S)
    if new != s:
        io.open(p, "w", encoding="utf-8").write(new)
        print("index.html counter ->", txt)
    elif '<span id="prcount">' not in s:
        print("WARNING: no <span id=\"prcount\"> in index.html, counter not shown")


def check():
    bad = []
    for rel in PAGES:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            bad.append((rel, "MISSING FILE")); continue
        s = io.open(p, encoding="utf-8").read()
        if s.count('<div class="sitenav">') != 1:
            bad.append((rel, "nav count = %d" % s.count('<div class="sitenav">')))
        miss = [l for l in REQUIRED_LINKS if 'href="%s"' % l not in s]
        if miss:
            bad.append((rel, "missing " + " ".join(miss)))
    for rel, why in bad:
        print("  FAIL %-34s %s" % (rel, why))
    if not bad:
        for rel in PAGES:
            print("  OK   %s" % rel)
    return 1 if bad else 0


def main():
    args = sys.argv[1:]
    if "--check" in args:
        sys.exit(check())
    if "--nav" not in args:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        items = fetch_prs()
        out = os.path.join(ROOT, "contributions", "index.html")
        if not os.path.isdir(os.path.dirname(out)):
            os.makedirs(os.path.dirname(out))
        io.open(out, "w", encoding="utf-8").write(render(items, stamp))
        print("contributions/index.html: %d PRs, generated %s" % (len(items), stamp))
        patch_counter(items)
    touched = [r for r in PAGES if os.path.exists(os.path.join(ROOT, r)) and inject_nav(r)]
    print("nav updated in:", touched or "nothing (already current)")
    sys.exit(check())


if __name__ == "__main__":
    main()
