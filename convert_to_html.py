"""
将 生活与工作手册.md 转换为自包含的 HTML 文件（无需任何外部依赖，双击即可在浏览器中打开）
"""
import re
from pathlib import Path
from html import escape

ROOT = Path(__file__).parent
MD_FILE = ROOT / "生活与工作手册.md"
HTML_FILE = ROOT / "生活与工作手册.html"

# ── 内嵌 CSS ────────────────────────────────────────────────
CSS = """
:root {
    --text: #1a1a1a; --bg: #fff; --accent: #1a5276; --border: #d5d8dc;
    --code-bg: #f4f6f7; --table-stripe: #f7f9fc;
    --warning-bg: #fef9e7; --warning-border: #f9e79f;
    --tip-bg: #eaf2f8; --tip-border: #aed6f1; --muted: #7f8c8d;
}
@media (prefers-color-scheme: dark) {
    :root {
        --text: #ddd; --bg: #1a1a2e; --accent: #85c1e9; --border: #444;
        --code-bg: #2c2c3e; --table-stripe: #252540;
        --warning-bg: #3e3520; --warning-border: #7d6608;
        --tip-bg: #1a3a4a; --tip-border: #1a5276; --muted: #aaa;
    }
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans SC", -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 16px; line-height: 1.8; color: var(--text); background: var(--bg);
    max-width: 860px; margin: 0 auto; padding: 40px 24px 80px;
}
h1 { font-size: 2em; text-align: center; margin: 32px 0 8px; color: var(--accent); }
h2 { font-size: 1.4em; margin: 48px 0 16px; padding-bottom: 6px; border-bottom: 2px solid var(--accent); color: var(--accent); }
h3 { font-size: 1.15em; margin: 28px 0 10px; }
h4 { font-size: 1.05em; margin: 20px 0 8px; }
p { margin: 10px 0; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

nav.toc { background: var(--code-bg); border-radius: 8px; padding: 20px 28px; margin: 24px 0 32px; }
nav.toc ol { padding-left: 20px; }
nav.toc li { margin: 4px 0; }

table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.95em; }
th, td { border: 1px solid var(--border); padding: 8px 12px; text-align: left; }
th { background: var(--accent); color: #fff; font-weight: 600; }
tr:nth-child(even) td { background: var(--table-stripe); }

code { font-family: "Cascadia Code", "Fira Code", "JetBrains Mono", Consolas, monospace; font-size: 0.9em; background: var(--code-bg); padding: 2px 6px; border-radius: 4px; }
pre { background: var(--code-bg); border-radius: 8px; padding: 16px 20px; overflow-x: auto; margin: 12px 0; line-height: 1.6; }
pre code { padding: 0; background: none; }

blockquote { border-left: 4px solid var(--accent); padding: 8px 16px; margin: 16px 0; background: var(--tip-bg); border-radius: 0 6px 6px 0; }
hr { border: none; border-top: 1px solid var(--border); margin: 40px 0; }

.dashboard-btn {
    position: fixed; top: 16px; right: 24px;
    background: var(--accent); color: #fff;
    padding: 10px 20px; border-radius: 8px;
    font-size: 0.9em; font-weight: 600;
    text-decoration: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    transition: opacity 0.2s, transform 0.2s; z-index: 1000;
}
.dashboard-btn:hover { opacity: 0.9; transform: translateY(-1px); text-decoration: none; color: #fff; }

@media print {
    body { max-width: 100%; padding: 0; font-size: 12pt; line-height: 1.6; }
    h2 { break-before: page; }
    h2:first-of-type { break-before: avoid; }
    nav.toc { break-after: page; }
    pre, table { break-inside: avoid; }
    a { color: inherit; }
    .dashboard-btn { display: none; }
}
"""


def parse_markdown(text: str) -> str:
    """手工解析 Markdown 为 HTML"""
    lines = text.split("\n")
    out = []
    i = 0
    in_code_block = False
    code_buf = []
    in_table = False
    table_rows = []
    table_align = []

    def flush_table():
        nonlocal in_table, table_rows, table_align
        if not table_rows:
            return
        html = ["<table>"]
        for ri, row in enumerate(table_rows):
            tag = "th" if ri == 0 else "td"
            html.append("<tr>")
            for ci, cell in enumerate(row):
                align = ""
                if ri > 0 and ci < len(table_align):
                    a = table_align[ci]
                    if a == "c": align = ' style="text-align:center"'
                    elif a == "r": align = ' style="text-align:right"'
                html.append(f"<{tag}{align}>{cell}</{tag}>")
            html.append("</tr>")
        html.append("</table>")
        out.append("\n".join(html))
        table_rows = []
        table_align = []
        in_table = False

    def flush_code():
        nonlocal code_buf
        if code_buf:
            out.append("<pre><code>" + "\n".join(code_buf) + "</code></pre>")
            code_buf = []

    def inline_format(s: str) -> str:
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return s

    def process_inline(line: str) -> str:
        line = escape(line)
        line = inline_format(line)
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', line)
        return line

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            if in_code_block:
                flush_code()
                in_code_block = False
            else:
                if in_table: flush_table()
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_buf.append(escape(line))
            i += 1
            continue

        if "|" in line and line.strip().startswith("|"):
            if in_table:
                if re.match(r"^\|[\s\-:|]+\|$", line.strip()):
                    parts = [c.strip() for c in line.strip().split("|")[1:-1]]
                    for p in parts:
                        if p.startswith(":") and p.endswith(":"):
                            table_align.append("c")
                        elif p.endswith(":"):
                            table_align.append("r")
                        else:
                            table_align.append("l")
                    i += 1
                    continue
                cells = [process_inline(c.strip()) for c in line.strip().split("|")[1:-1]]
                table_rows.append(cells)
            else:
                if in_table: flush_table()
                in_table = True
                table_rows = []
                table_align = []
                cells = [process_inline(c.strip()) for c in line.strip().split("|")[1:-1]]
                table_rows.append(cells)
            i += 1
            continue
        else:
            if in_table: flush_table()

        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            text_inner = process_inline(m.group(2))
            anchor = re.sub(r"[^\w一-鿿]+", "-", m.group(2).strip()).strip("-").lower()
            out.append(f"<h{level} id=\"{anchor}\">{text_inner}</h{level}>")
            i += 1
            continue

        if line.strip() == "---" or line.strip() == "***":
            out.append("<hr>")
            i += 1
            continue

        if line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(process_inline(lines[i][1:].lstrip()))
                i += 1
            out.append("<blockquote>" + "<br>".join(buf) + "</blockquote>")
            continue

        if not line.strip():
            out.append("")
            i += 1
            continue

        para_lines = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].startswith(">") and not lines[i].startswith("```") and "|" not in lines[i]:
            para_lines.append(process_inline(lines[i]))
            i += 1
        if para_lines:
            out.append("<p>" + "<br>".join(para_lines) + "</p>")
        else:
            i += 1

    if in_code_block: flush_code()
    if in_table: flush_table()

    return "\n".join(out)


def strip_markdown_toc(text: str) -> str:
    """Remove the inline TOC section from markdown (## 目录 through the next ---)."""
    # Pattern: "## 目录" line, followed by lines until the next "---"
    pattern = r'\n## 目录\n\n.*?\n\n---\n'
    text = re.sub(pattern, '\n', text, flags=re.DOTALL)
    return text


def build_toc(body_html: str) -> str:
    """从 H2 标题生成目录，排除目录和副标题"""
    h2s = re.findall(r'<h2 id="([^"]+)">(.+?)</h2>', body_html)
    if not h2s:
        return ""
    items = []
    for anchor, title in h2s:
        clean_title = re.sub(r"<[^>]+>", "", title)
        # Skip the TOC heading itself and subtitle lines
        if clean_title.strip() in ("目录", "—— Yu Ming Charter School 教育交流研究生指南（2026.08 – 2027.05）"):
            continue
        items.append(f'<li><a href="#{anchor}">{clean_title}</a></li>')
    if not items:
        return ""
    return '<nav class="toc"><h3>目录</h3><ol>\n' + "\n".join(items) + '\n</ol></nav>'


def main():
    md_text = MD_FILE.read_text(encoding="utf-8")
    md_text = strip_markdown_toc(md_text)
    body = parse_markdown(md_text)
    toc = build_toc(body)

    title_match = re.search(r"<h1[^>]*>(.+?)</h1>", body)
    page_title = title_match.group(1) if title_match else "生活与工作手册"

    # Insert TOC after the first h1 heading
    if toc and title_match:
        tag = title_match.group(0)
        body = body.replace(tag, tag + "\n" + toc, 1)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>给海玲的美国之行生活手册</title>
<style>{CSS}</style>
</head>
<body>
<a class="dashboard-btn" href="/dashboard" title="数据仪表盘">📊 数据仪表盘</a>
{body}
</body>
</html>"""

    HTML_FILE.write_text(html, encoding="utf-8")
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(f"HTML 已生成：{HTML_FILE}")


if __name__ == "__main__":
    main()
