#!/usr/bin/env python3
"""Extract the comments from a saved Google Deep Review page (review.html) into JSON and text.

    python extract_google_review.py review.html out_prefix

Writes out_prefix.json ({"overall": str, "comments": [...]}) and out_prefix.txt.
Only for comparing a Google run with a kit run; the pipeline does not need it.
"""
import json, re, sys
from html.parser import HTMLParser

MARKS = ("severity-badge", "comment-summary", "comment-body", "suggested-fix-inline",
         "comment-location-footer", "overall-summary-body", "comment-card-header")


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        c = dict(attrs).get("class") or ""
        if "mat-icon" in c:
            self.skip += 1
            return
        for k in MARKS:
            if k in c:
                self.out.append(f"\n@@{k}@@ ")
                break
        if tag in ("p", "li", "br", "div", "h1", "h2", "h3"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag == "mat-icon" and self.skip:
            self.skip -= 1

    def handle_data(self, d):
        if not self.skip and d.strip():
            self.out.append(d.strip() + " ")


def main(src, prefix):
    t = open(src, encoding="utf-8", errors="replace").read()
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<svg.*?</svg>", "", t, flags=re.S)
    t = re.sub(r'src="data:[^"]+"', 'src=""', t)
    p = P()
    p.feed(t)
    text = re.sub(r"\n\s*\n+", "\n", "".join(p.out))
    parts = re.split(r"@@(" + "|".join(MARKS) + r")@@", text)
    overall, comments, cur = "", [], None
    for kind, body in zip(parts[1::2], parts[2::2]):
        body = re.sub(r"\s*\bDismiss\b\s*$", "", body.strip()).strip()
        if kind == "overall-summary-body":
            overall = re.sub(r"\s*Read more\s*$", "", body)
        elif kind == "comment-card-header":
            cur = {"severity": "", "summary": "", "body": "", "suggested_fix": "", "page": None}
            comments.append(cur)
        elif cur is not None:
            if kind == "severity-badge":
                cur["severity"] = body.split()[0].upper() if body else ""
            elif kind == "comment-summary":
                cur["summary"] = body
            elif kind == "comment-body":
                cur["body"] = body
            elif kind == "suggested-fix-inline":
                cur["suggested_fix"] = body
            elif kind == "comment-location-footer":
                m = re.search(r"Page (\d+)", body)
                cur["page"] = int(m.group(1)) if m else None
    json.dump({"overall": overall, "comments": comments}, open(prefix + ".json", "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    lines = ["OVERALL", overall, ""]
    for i, c in enumerate(comments, 1):
        lines += [f"G{i} [{c['severity']}] p{c['page']} {c['summary']}", c["body"],
                  ("FIX: " + c["suggested_fix"]) if c["suggested_fix"] else "", ""]
    open(prefix + ".txt", "w", encoding="utf-8").write("\n".join(lines))
    print(len(comments), "comments")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
