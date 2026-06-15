#!/usr/bin/env python3
"""Render a Hebrew markdown report to a self-contained, RTL, UTF-8 HTML page.

Why: S3 serves raw .md without charset → browsers guess the encoding and Hebrew
comes out as gibberish. An HTML page with an explicit charset + RTL renders
correctly everywhere, and reads far better than raw markdown.

Markdown is rendered client-side by marked.js (CDN) so we don't depend on a
Python markdown lib. The source markdown is embedded in a non-executed
<script type="text/markdown"> block (only </script> needs escaping).

Usage: md_to_html.py <input.md> <output.html>
"""
import sys
import html

TEMPLATE = """<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --bg:#faf6ef; --ink:#1f2a37; --steel:#2f4858; --rust:#b4541f; --line:#e7ddcd; }}
  body {{ background:var(--bg); color:var(--ink); margin:0;
    font-family:"Heebo","Segoe UI",Arial,sans-serif; line-height:1.7; }}
  .wrap {{ max-width:820px; margin:0 auto; padding:40px 24px 80px; }}
  #content h1 {{ color:var(--steel); font-size:1.9rem; border-bottom:3px solid var(--rust);
    padding-bottom:.3em; margin-top:0; }}
  #content h2 {{ color:var(--steel); margin-top:1.8em; border-bottom:1px solid var(--line);
    padding-bottom:.2em; }}
  #content h3 {{ color:var(--steel); }}
  #content table {{ border-collapse:collapse; width:100%; margin:1em 0; background:#fff;
    box-shadow:0 1px 3px rgba(0,0,0,.06); }}
  #content th, #content td {{ border:1px solid var(--line); padding:.55em .8em; text-align:right; }}
  #content th {{ background:var(--steel); color:#fff; }}
  #content tr:nth-child(even) td {{ background:#fbf8f2; }}
  #content a {{ color:var(--rust); }}
  #content code {{ background:#f0e9dc; padding:.1em .35em; border-radius:4px; }}
  #content blockquote {{ border-right:4px solid var(--rust); margin:0; padding:.2em 1em; color:#555; }}
  .meta {{ color:#8a7f6c; font-size:.85rem; margin-bottom:2em; }}
</style>
</head>
<body>
<div class="wrap">
  <div id="content">טוען…</div>
  <div class="meta">נשמר ב-S3 · נוצר אוטומטית מהדוח של דפנה</div>
</div>
<script type="text/markdown" id="src">
{md}
</script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
  const src = document.getElementById('src').textContent;
  document.getElementById('content').innerHTML = marked.parse(src);
</script>
</body>
</html>
"""


def main():
    inp, outp = sys.argv[1], sys.argv[2]
    with open(inp, encoding="utf-8") as f:
        md = f.read()
    # Only </script> can break out of the embedded block.
    md = md.replace("</script", "<\\/script")
    title = md.splitlines()[0].lstrip("# ").strip() if md.strip() else "דוח"
    with open(outp, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(title=html.escape(title), md=md))
    print("wrote", outp)


if __name__ == "__main__":
    main()
