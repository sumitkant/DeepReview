#!/usr/bin/env python3
"""Render a deep-review result as one self-contained HTML file.

    python render_review.py DOCUMENT REVIEW_JSON OUT_HTML

DOCUMENT     the reviewed file: .pdf (needs `pip install pymupdf`) or .txt / .md
REVIEW_JSON  {"review_markdown": str, "anchored_comments": [{comment_id, severity, summary,
             body_markdown, suggested_edit, location: {page, quote: {exact}}, grounding_urls}]}

The page opens with a summary (findings, must fix, minor, can ignore, needs verification), then
shows the document on the left with each comment's quoted passage highlighted in its category
colour, and the comments on the right. Clicking either side jumps to the other. Each
comment has Accept / Dismiss and a note; "Export decisions" saves them as JSON for the rewrite step.
"""
import base64, html, json, pathlib, re, sys, unicodedata

SEV = ["CRITICAL", "MAJOR", "MINOR", "SUGGESTION"]
# Display categories: (key, label, what it means)
BUCKETS = [("must", "Must fix", "Major and critical"), ("minor", "Minor", "Typos and small issues"),
           ("ignore", "Can ignore", "Optional suggestions"), ("verify", "Needs verification", "Not confirmed yet")]
FONT_URL = "https://fonts.googleapis.com/css2?family=Google+Sans+Flex:wght@400;500;600;700&display=swap"


def bucket(c):
    if c.get("needs_verification") or str(c.get("verdict", "")).upper() == "UNVERIFIED":
        return "verify"
    return {"CRITICAL": "must", "MAJOR": "must", "MINOR": "minor"}.get(c["severity"], "ignore")


def norm(s):
    return re.sub(r"[^0-9a-z]", "", unicodedata.normalize("NFKC", s).lower())


def find_span(units, quote):
    """units: list of normalized strings. Return (first, last) unit index covering quote, or None.
    Falls back to the longest leading part of the quote that can be found (at least 24 characters)."""
    stream, owner = [], []
    for i, u in enumerate(units):
        stream.append(u)
        owner.extend([i] * len(u))
    stream = "".join(stream)
    q = norm(quote)
    n = len(q)
    while n >= min(24, len(q)) and n > 0:
        at = stream.find(q[:n])
        if at >= 0:
            return owner[at], owner[at + n - 1]
        n = int(n * 0.8) if n > 24 else n - 1
    return None


def md(text):
    """Small Markdown subset to HTML: headings, bullets, fenced code, bold, italic, inline code, links."""
    def inline(s):
        s = html.escape(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])", r"<em>\1</em>", s)
        return re.sub(r"(https?://[^\s<)]+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', s)
    out, para, in_list, in_code = [], [], False, False

    def flush():
        nonlocal para, in_list
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
        if in_list:
            out.append("</ul>")
            in_list = False
    for line in (text or "").splitlines():
        if line.strip().startswith("```"):
            flush()
            out.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
        elif in_code:
            out.append(html.escape(line))
        elif re.match(r"\s*#{1,6}\s", line):
            flush()
            out.append("<h4>" + inline(re.sub(r"^\s*#+\s*", "", line)) + "</h4>")
        elif re.match(r"\s*[-*]\s+", line):
            if para:
                out.append("<p>" + inline(" ".join(para)) + "</p>")
                para = []
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + inline(re.sub(r"^\s*[-*]\s+", "", line)) + "</li>")
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
    flush()
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def pdf_pages(path, comments, dpi=110):
    try:
        import pymupdf as fitz
    except ImportError:
        try:
            import fitz
        except ImportError:
            sys.exit("PDF input needs PyMuPDF:  pip install pymupdf")
    doc = fitz.open(path)
    pages, words = [], []
    for p in doc:
        w = [x for x in p.get_text("words") if norm(x[4])]
        words.append(w)
        pix = p.get_pixmap(dpi=dpi)
        try:
            img, mime = pix.tobytes("jpg"), "image/jpeg"
        except Exception:
            img, mime = pix.tobytes("png"), "image/png"
        pages.append({"w": p.rect.width, "h": p.rect.height, "boxes": [],
                      "src": f"data:{mime};base64," + base64.b64encode(img).decode()})
    missing = []
    for c in comments:
        loc = c.get("location") or {}
        quote = ((loc.get("quote") or {}).get("exact")) or ""
        hint = loc.get("page")
        order = ([hint - 1] if isinstance(hint, int) and 0 < hint <= len(pages) else []) + list(range(len(pages)))
        hit = None
        for pi in dict.fromkeys(order):
            span = find_span([norm(x[4]) for x in words[pi]], quote) if quote else None
            if span:
                hit = (pi, span)
                break
        if not hit:
            missing.append(c["comment_id"])
            c["_page"] = hint
            continue
        pi, (a, b) = hit
        c["_page"] = pi + 1
        lines = []
        for x0, y0, x1, y1, *_ in words[pi][a:b + 1]:
            if lines and abs((y0 + y1) / 2 - (lines[-1][1] + lines[-1][3]) / 2) < (y1 - y0) * 0.6 and x0 >= lines[-1][0]:
                lines[-1] = [lines[-1][0], min(lines[-1][1], y0), max(lines[-1][2], x1), max(lines[-1][3], y1)]
            else:
                lines.append([x0, y0, x1, y1])
        W, H = pages[pi]["w"], pages[pi]["h"]
        for x0, y0, x1, y1 in lines:
            pages[pi]["boxes"].append((c["comment_id"], c["_bucket"], 100 * x0 / W, 100 * y0 / H,
                                       100 * (x1 - x0) / W, 100 * (y1 - y0) / H))
    body = []
    for i, p in enumerate(pages, 1):
        boxes = "".join(f'<div class="hl b-{s}" data-cid="{html.escape(cid)}" '
                        f'style="left:{l:.2f}%;top:{t:.2f}%;width:{w:.2f}%;height:{h:.2f}%"></div>'
                        for cid, s, l, t, w, h in p["boxes"])
        body.append(f'<div class="page" id="page-{i}"><img src="{p["src"]}" alt="Page {i}">{boxes}'
                    f'<span class="pageno">Page {i}</span></div>')
    return "\n".join(body), missing


def text_pages(path, comments):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    toks = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    units = [norm(text[a:b]) for a, b in toks]
    marks, missing = [], []
    for c in comments:
        quote = (((c.get("location") or {}).get("quote") or {}).get("exact")) or ""
        span = find_span(units, quote) if quote else None
        c["_page"] = None
        if span:
            marks.append((toks[span[0]][0], toks[span[1]][1], c))
        else:
            missing.append(c["comment_id"])
    out, pos = [], 0
    for a, b, c in sorted(marks, key=lambda m: m[0]):
        if a < pos:
            continue
        out.append(html.escape(text[pos:a]))
        out.append(f'<mark class="hl b-{c["_bucket"]}" data-cid="{html.escape(c["comment_id"])}">'
                   f'{html.escape(text[a:b])}</mark>')
        pos = b
    out.append(html.escape(text[pos:]))
    return '<div class="page textpage"><pre>' + "".join(out) + "</pre></div>", missing


CSS = """
:root{--ink:#16202e;--muted:#566174;--glass:rgba(255,255,255,.58);--glass2:rgba(255,255,255,.78);--edge:rgba(255,255,255,.75);
--shadow:0 10px 34px rgba(31,45,80,.14);--bg1:#e9eefb;--bg2:#f6ecf5;--blob1:#9db8ff;--blob2:#ffc2d4;--blob3:#b6f0dc;
--all:#2f5fd0;--must:#d93025;--minor:#c77700;--ignore:#4d7c6f;--verify:#7a4fd1;--field:rgba(255,255,255,.6)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--ink:#e9edf5;--muted:#a3adbd;--glass:rgba(28,33,46,.56);--glass2:rgba(40,46,62,.8);
--edge:rgba(255,255,255,.13);--shadow:0 10px 34px rgba(0,0,0,.45);--bg1:#0f1320;--bg2:#1a1424;--blob1:#27408f;--blob2:#6a2647;--blob3:#155247;
--all:#8fb0ff;--must:#ff8a80;--minor:#ffc15e;--ignore:#86cdb9;--verify:#c3a6ff;--field:rgba(0,0,0,.25)}}
:root[data-theme=dark]{--ink:#e9edf5;--muted:#a3adbd;--glass:rgba(28,33,46,.56);--glass2:rgba(40,46,62,.8);
--edge:rgba(255,255,255,.13);--shadow:0 10px 34px rgba(0,0,0,.45);--bg1:#0f1320;--bg2:#1a1424;--blob1:#27408f;--blob2:#6a2647;--blob3:#155247;
--all:#8fb0ff;--must:#ff8a80;--minor:#ffc15e;--ignore:#86cdb9;--verify:#c3a6ff;--field:rgba(0,0,0,.25)}
*{box-sizing:border-box;font-family:"Google Sans Flex","Google Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
html,body{margin:0;height:100%}
body{color:var(--ink);font-size:14px;line-height:1.5;background:linear-gradient(135deg,var(--bg1),var(--bg2));background-attachment:fixed;display:flex;flex-direction:column}
body::before{content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;background:
radial-gradient(42vmax 42vmax at 8% 4%,var(--blob1),transparent 62%),radial-gradient(38vmax 38vmax at 96% 12%,var(--blob2),transparent 60%),
radial-gradient(46vmax 46vmax at 60% 108%,var(--blob3),transparent 62%);opacity:.75}
.glass{background:var(--glass);-webkit-backdrop-filter:blur(18px) saturate(160%);backdrop-filter:blur(18px) saturate(160%);
border:1px solid var(--edge);box-shadow:var(--shadow);border-radius:18px}
header{margin:14px 16px 0;padding:12px 16px}
.top{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.top h1{font-size:16px;font-weight:600;margin:0;flex:1 1 240px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
button{font-size:13px;color:var(--ink);background:var(--field);border:1px solid var(--edge);border-radius:999px;padding:6px 14px;cursor:pointer}
button:hover{border-color:var(--all)}button.primary{background:var(--all);border-color:var(--all);color:#fff;font-weight:600}
:root[data-theme=dark] button.primary{color:#0f1320}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) button.primary{color:#0f1320}}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:10px;margin-top:12px}
.stat{--c:var(--all);text-align:left;border-radius:14px;padding:10px 14px;background:var(--glass2);border:1px solid var(--edge);border-left:5px solid var(--c);display:block}
.stat b{display:block;font-size:26px;font-weight:700;line-height:1.1;color:var(--c);font-variant-numeric:tabular-nums}
.stat span{display:block;font-size:13px;font-weight:600}.stat small{display:block;font-size:11px;color:var(--muted)}
.stat.on{outline:2px solid var(--c);outline-offset:1px}
.b-all{--c:var(--all)}.b-must{--c:var(--must)}.b-minor{--c:var(--minor)}.b-ignore{--c:var(--ignore)}.b-verify{--c:var(--verify)}
main{flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1.25fr) minmax(330px,1fr);gap:14px;padding:14px 16px 16px}
#doc,#side{overflow:auto;padding:14px;min-height:0}
.page{position:relative;margin:0 auto 14px;max-width:900px;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.18)}
.page img{display:block;width:100%;height:auto}.pageno{position:absolute;right:8px;bottom:5px;font-size:11px;color:#556}
.textpage{padding:20px;background:var(--glass2);color:var(--ink)}.textpage pre{white-space:pre-wrap;font-size:13px;line-height:1.55;margin:0;background:none;padding:0}
.hl{position:absolute;border-radius:3px;cursor:pointer;background:var(--c);opacity:.3;mix-blend-mode:multiply}
.hl.active{opacity:.55;outline:2px solid var(--c);outline-offset:1px}
mark.hl{position:static;opacity:1;mix-blend-mode:normal;color:inherit;background:color-mix(in srgb,var(--c) 28%,transparent)}
.card{background:var(--glass2);border:1px solid var(--edge);border-left:5px solid var(--c,var(--all));border-radius:14px;padding:12px 14px;margin-bottom:12px}
.card.active{outline:2px solid var(--c,var(--all));outline-offset:1px}.card.dismissed{opacity:.45}
.card.accepted{box-shadow:inset 0 0 0 1px var(--ignore)}.card.accepted h3::after{content:" \\2713";color:var(--ignore)}
.card h3{font-size:14px;font-weight:600;margin:8px 0 6px}.card h4{font-size:13px;font-weight:600;margin:12px 0 4px}
.badge{display:inline-block;font-size:11px;font-weight:600;border-radius:999px;padding:2px 10px;color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);border:1px solid color-mix(in srgb,var(--c) 45%,transparent)}
.meta{float:right;color:var(--muted);font-size:12px}
.body p,.overall p{margin:6px 0}.body ul,.overall ul{margin:6px 0;padding-left:20px}
code{background:var(--field);border-radius:5px;padding:0 4px;font-size:12.5px}
pre{background:var(--field);border-radius:10px;padding:10px;overflow:auto;white-space:pre-wrap}pre code{background:none;padding:0}
.fix{border-left:3px solid var(--all);padding:8px 12px;margin:8px 0;background:var(--field);border-radius:0 10px 10px 0;white-space:pre-wrap}
.fix b{display:block;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;font-weight:600}
.actions{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}
textarea{flex:1 1 100%;width:100%;min-height:36px;font-size:13px;color:var(--ink);background:var(--field);border:1px solid var(--edge);border-radius:10px;padding:6px 10px}
.actions button.on{background:var(--all);border-color:var(--all);color:#fff}
.src{font-size:12px;color:var(--muted);word-break:break-all}a{color:var(--all)}
@media (max-width:900px){html,body{height:auto}body{display:block}main{grid-template-columns:1fr}#doc{max-height:62vh}}
"""

JS = """
const KEY='deep-review:'+document.title, cards=[...document.querySelectorAll('.card[data-cid]')];
let state={}, filter='all';try{state=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){}};
function paint(){cards.forEach(c=>{const s=state[c.dataset.cid]||{};c.classList.toggle('accepted',s.decision==='accept');
 c.classList.toggle('dismissed',s.decision==='dismiss');c.querySelectorAll('[data-d]').forEach(b=>b.classList.toggle('on',b.dataset.d===s.decision));
 const t=c.querySelector('textarea');if(t&&t.value!==(s.note||''))t.value=s.note||'';c.style.display=(filter==='all'||c.dataset.b===filter)?'':'none'});
 document.querySelectorAll('.hl').forEach(h=>h.style.display=(filter==='all'||h.dataset.b===filter)?'':'none');
 document.querySelectorAll('.stat').forEach(s=>s.classList.toggle('on',s.dataset.f===filter));
 const n=cards.filter(c=>(state[c.dataset.cid]||{}).decision).length;document.getElementById('progress').textContent=n+' of '+cards.length+' decided';
 const g=document.getElementById('general');if(g.value!==(state._general||''))g.value=state._general||''}
function focusC(cid,from){document.querySelectorAll('.active').forEach(e=>e.classList.remove('active'));
 const card=cards.find(c=>c.dataset.cid===cid),hl=[...document.querySelectorAll('.hl')].filter(h=>h.dataset.cid===cid);
 if(card)card.classList.add('active');hl.forEach(h=>h.classList.add('active'));
 if(from!=='card'&&card)card.scrollIntoView({behavior:'smooth',block:'center'});
 if(from!=='doc'&&hl[0])hl[0].scrollIntoView({behavior:'smooth',block:'center'})}
document.querySelectorAll('.hl').forEach(h=>{const c=cards.find(x=>x.dataset.cid===h.dataset.cid);if(c)h.dataset.b=c.dataset.b;
 h.addEventListener('click',()=>focusC(h.dataset.cid,'doc'))});
cards.forEach(c=>{c.addEventListener('click',e=>{if(!e.target.closest('.actions'))focusC(c.dataset.cid,'card')});
 c.querySelectorAll('[data-d]').forEach(b=>b.addEventListener('click',()=>{const s=state[c.dataset.cid]=state[c.dataset.cid]||{};
  s.decision=s.decision===b.dataset.d?undefined:b.dataset.d;save();paint()}));
 const t=c.querySelector('textarea');t.addEventListener('input',()=>{(state[c.dataset.cid]=state[c.dataset.cid]||{}).note=t.value;save()})});
document.querySelectorAll('.stat').forEach(s=>s.addEventListener('click',()=>{filter=(filter===s.dataset.f)?'all':s.dataset.f;paint()}));
document.getElementById('general').addEventListener('input',e=>{state._general=e.target.value;save()});
document.getElementById('acceptmust').addEventListener('click',()=>{cards.forEach(c=>{const s=state[c.dataset.cid]=state[c.dataset.cid]||{};if(!s.decision&&c.dataset.b==='must')s.decision='accept'});save();paint()});
document.getElementById('export').addEventListener('click',()=>{const out={document:DATA.document,summary:DATA.summary,general_instructions:state._general||'',
 decisions:DATA.comments.map(c=>Object.assign({},c,{decision:(state[c.comment_id]||{}).decision||'undecided',note:(state[c.comment_id]||{}).note||''}))};
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{type:'application/json'}));a.download='review_decisions.json';a.click()});
document.getElementById('theme').addEventListener('click',()=>{const r=document.documentElement,d=r.dataset.theme==='dark'||(!r.dataset.theme&&matchMedia('(prefers-color-scheme:dark)').matches);r.dataset.theme=d?'light':'dark'});
paint();
"""


def main(doc_path, review_path, out_path):
    review = json.loads(pathlib.Path(review_path).read_text(encoding="utf-8"))
    comments = review.get("anchored_comments") or []
    for i, c in enumerate(comments, 1):
        c.setdefault("comment_id", f"C{i}")
        c["severity"] = c.get("severity", "MINOR").upper() if str(c.get("severity", "")).upper() in SEV else "MINOR"
        c["_bucket"] = bucket(c)
    is_pdf = doc_path.lower().endswith(".pdf")
    doc_html, missing = (pdf_pages if is_pdf else text_pages)(doc_path, comments)
    name = pathlib.Path(doc_path).name
    labels = {k: lab for k, lab, _ in BUCKETS}
    counts = {k: sum(c["_bucket"] == k for c in comments) for k, _, _ in BUCKETS}
    cards = []
    for c in comments:
        cid, b = html.escape(c["comment_id"]), c["_bucket"]
        fix = (c.get("suggested_edit") or "").strip()
        urls = c.get("grounding_urls") or []
        where = f"Page {c['_page']}" if c.get("_page") else ""
        if c["comment_id"] in missing:
            where += " · passage not located"
        cards.append(
            f'<article class="card b-{b}" data-cid="{cid}" data-b="{b}"><span class="meta">{cid} · {html.escape(where)}</span>'
            f'<span class="badge">{labels[b]} · {c["severity"].title()}</span><h3>{html.escape(c.get("summary", ""))}</h3>'
            f'<div class="body">{md(c.get("body_markdown", ""))}</div>'
            + (f'<div class="fix"><b>Suggested fix</b>{html.escape(fix)}</div>' if fix else "")
            + (('<div class="src">Sources: ' + " · ".join(
                f'<a href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(u)}</a>' for u in urls) + "</div>") if urls else "")
            + '<div class="actions"><button data-d="accept">Accept</button><button data-d="dismiss">Dismiss</button>'
              '<textarea placeholder="Note for the rewrite (optional): how to apply this, or the fact to use"></textarea></div></article>')
    tiles = [f'<button class="stat b-all" data-f="all"><b>{len(comments)}</b><span>Findings</span><small>Everything the review raised</small></button>']
    tiles += [f'<button class="stat b-{k}" data-f="{k}"><b>{counts[k]}</b><span>{lab}</span><small>{sub}</small></button>'
              for k, lab, sub in BUCKETS if k != "verify" or counts[k]]
    summary = {"findings": len(comments), "must_fix": counts["must"], "minor": counts["minor"],
               "can_ignore": counts["ignore"], "needs_verification": counts["verify"]}
    data = {"document": name, "summary": summary, "comments": [
        {"comment_id": c["comment_id"], "category": labels[c["_bucket"]], "severity": c["severity"], "summary": c.get("summary", ""),
         "quote": (((c.get("location") or {}).get("quote") or {}).get("exact")) or "", "page": c.get("_page"),
         "body_markdown": c.get("body_markdown", ""), "suggested_edit": c.get("suggested_edit", "")} for c in comments]}
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review: {html.escape(name)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONT_URL}"><style>{CSS}</style></head><body>
<header class="glass"><div class="top"><h1>Review · {html.escape(name)}</h1><span id="progress" style="color:var(--muted);font-size:12px"></span>
<button id="acceptmust">Accept all must-fix</button><button id="export" class="primary">Export decisions</button><button id="theme" aria-label="Toggle light or dark theme">Theme</button></div>
<div class="stats" aria-label="Summary of findings">{''.join(tiles)}</div></header>
<main><section id="doc" class="glass">{doc_html}</section><section id="side" class="glass">
<article class="card overall"><h3>Overall feedback</h3><div class="overall">{md(review.get("review_markdown", ""))}</div>
<h4>Instructions for the rewrite</h4><textarea id="general" placeholder="Anything that applies to the whole rewrite: tone, length, what to leave alone"></textarea></article>
{''.join(cards)}</section></main>
<script>const DATA={json.dumps(data, ensure_ascii=False).replace("</", "<\\/")};{JS}</script></body></html>"""
    pathlib.Path(out_path).write_text(page, encoding="utf-8")
    print(f"wrote {out_path}: {summary['findings']} findings ({summary['must_fix']} must fix, {summary['minor']} minor, "
          f"{summary['can_ignore']} can ignore, {summary['needs_verification']} need verification); "
          f"{len(comments) - len(missing)} located" + (f", not located: {', '.join(missing)}" if missing else ""))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
