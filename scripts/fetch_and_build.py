"""Fetch HuggingFace Daily Papers API and generate static site + RSS + JSON."""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://huggingface.co/api/daily_papers"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs"
RSS_FEED_URL = "https://saffee666.github.io/hf-daily-papers-mirror"
SITE_TITLE = "HF Daily Papers Mirror"

HEADERS = {
    "User-Agent": "hf-daily-papers-mirror/1.0",
    "Accept": "application/json",
}

ARCHIVE_JSON = OUTPUT_DIR / "archive.json"


def fetch_papers() -> list[dict]:
    req = urllib.request.Request(API_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def arxiv_url(paper_id: str) -> str:
    return f"https://arxiv.org/abs/{paper_id}"


def arxiv_pdf_url(paper_id: str) -> str:
    return f"https://arxiv.org/pdf/{paper_id}"


def format_date(iso_str: str) -> str:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d")


def load_archive() -> dict:
    if ARCHIVE_JSON.exists():
        return json.loads(ARCHIVE_JSON.read_text(encoding="utf-8"))
    return {"papers": {}, "dates": []}


def save_archive(archive: dict) -> None:
    ARCHIVE_JSON.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_JSON.write_text(
        json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def json_serializer(obj):
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def build(papers: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Update archive
    archive = load_archive()
    if today not in archive["dates"]:
        archive["dates"].insert(0, today)
        archive["dates"] = archive["dates"][:90]  # keep 90 days

    for p in papers:
        pid = p["paper"]["id"]
        entry = {
            "title": p["paper"].get("title", ""),
            "authors": [a["name"] for a in p["paper"].get("authors", [])],
            "summary": p["paper"].get("summary", ""),
            "upvotes": p.get("upvotes", 0),
            "publishedAt": p["paper"].get("publishedAt", ""),
            "submittedOnDailyAt": p["paper"].get("submittedOnDailyAt", ""),
            "githubRepo": p["paper"].get("githubRepo", ""),
            "submittedBy": (p.get("paper", {}).get("submittedOnDailyBy", {}) or {}).get(
                "user", ""
            ),
        }
        archive["papers"][pid] = entry

    save_archive(archive)

    # Sort by upvotes desc
    papers_sorted = sorted(papers, key=lambda p: p.get("upvotes", 0), reverse=True)

    # Generate files
    write_index_html(papers_sorted, today, archive)
    write_rss(papers_sorted, today)
    write_daily_json(papers_sorted, today)
    write_archive_page(archive, today)

    print(f"Generated site for {today}: {len(papers)} papers")


def write_index_html(papers: list[dict], date: str, archive: dict) -> None:
    cards = "\n".join(paper_card(p) for p in papers)

    dates_list = "\n".join(
        f'<li><a href="#" data-date="{d}" onclick="loadDate(\'{d}\')">{d}</a></li>'
        for d in archive["dates"][:14]
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{SITE_TITLE} — {date}</title>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Georgia,'Noto Serif SC',serif;background:#faf9f6;color:#1a1a1a;line-height:1.6}}
  .container{{max-width:800px;margin:0 auto;padding:2rem 1rem}}
  header{{border-bottom:2px solid #1a1a1a;padding-bottom:1rem;margin-bottom:2rem;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:1rem}}
  header h1{{font-size:clamp(1.5rem,4vw,2.2rem);font-weight:700;letter-spacing:-0.02em}}
  header p{{color:#666;font-size:0.9rem}}
  nav{{display:flex;gap:0.5rem;margin-bottom:1.5rem;flex-wrap:wrap}}
  nav a{{padding:0.4rem 1rem;border:1px solid #d4d4d4;border-radius:4px;text-decoration:none;color:#1a1a1a;font-size:0.85rem;transition:background .2s}}
  nav a:hover,nav a.active{{background:#1a1a1a;color:#fff}}
  .paper{{border-bottom:1px solid #e8e8e8;padding:1.5rem 0}}
  .paper:first-child{{border-top:1px solid #e8e8e8}}
  .paper h2{{font-size:1.15rem;font-weight:700;margin-bottom:0.3rem;line-height:1.4}}
  .paper h2 a{{color:#1a1a1a;text-decoration:none}}
  .paper h2 a:hover{{text-decoration:underline}}
  .meta{{font-size:0.82rem;color:#888;margin-bottom:0.5rem;display:flex;gap:1rem;flex-wrap:wrap}}
  .meta .upvotes{{color:#c41e3a;font-weight:600}}
  .summary{{font-size:0.9rem;color:#444;line-height:1.6;max-height:5em;overflow:hidden;position:relative}}
  .summary::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:2em;background:linear-gradient(transparent,#faf9f6)}}
  .links{{margin-top:0.5rem;display:flex;gap:0.75rem;flex-wrap:wrap}}
  .links a{{font-size:0.82rem;color:#2563eb;text-decoration:none;border:1px solid #2563eb;padding:0.25rem 0.75rem;border-radius:3px;transition:all .2s}}
  .links a:hover{{background:#2563eb;color:#fff}}
  .links a.arxiv-pdf{{border-color:#b31b1b;color:#b31b1b}}
  .links a.arxiv-pdf:hover{{background:#b31b1b;color:#fff}}
  .archive-panel{{display:none;background:#fff;border:1px solid #e8e8e8;border-radius:6px;padding:1rem;margin-bottom:1.5rem}}
  .archive-panel.open{{display:block}}
  .archive-panel ul{{list-style:none;columns:2}}
  .archive-panel li a{{color:#2563eb;text-decoration:none;font-size:0.85rem}}
  .archive-panel li a:hover{{text-decoration:underline}}
  footer{{text-align:center;padding:2rem 0;color:#999;font-size:0.8rem}}
  footer a{{color:#666}}
  .rss-link{{padding:0.4rem 0.8rem;background:#f26522;color:#fff!important;border-radius:4px;text-decoration:none;font-size:0.8rem;font-family:sans-serif}}
  @media(max-width:600px){{
    header{{flex-direction:column;align-items:flex-start}}
    .archive-panel ul{{columns:1}}
  }}
</style>
</head>
<body>
<div class="container">
<header>
  <div>
    <h1>{SITE_TITLE}</h1>
    <p>Daily papers from HuggingFace, mirrored for access from China</p>
  </div>
  <a href="rss.xml" class="rss-link">RSS</a>
</header>

<nav>
  <a href="#" class="active">Daily</a>
  <a href="archive.html">Archive</a>
  <a href="#" onclick="document.querySelector('.archive-panel').classList.toggle('open');return false">Date ▾</a>
</nav>

<div class="archive-panel">
  <ul>{dates_list}</ul>
</div>

<main>{cards}</main>

<footer>
  <p>Papers from <a href="https://huggingface.co/papers">HuggingFace Daily Papers</a> — content on <a href="https://arxiv.org">arXiv</a></p>
  <p>Generated {date} · <a href="https://github.com/saffee666/hf-daily-papers-mirror">GitHub</a> · <a href="rss.xml">RSS Feed</a> · <a href="index.json">JSON API</a></p>
</footer>
</div>

<script>
async function loadDate(date) {{
  window.location.href = 'archive.html?date=' + date;
}}
</script>
</body>
</html>"""

    (OUTPUT_DIR / "index.html").write_text(html, encoding="utf-8")


def paper_card(p: dict) -> str:
    paper = p["paper"]
    pid = paper.get("id", "")
    title = paper.get("title", "Untitled")
    upvotes = p.get("upvotes", 0)
    authors = ", ".join(a.get("name", "") for a in paper.get("authors", [])[:5])
    if len(paper.get("authors", [])) > 5:
        authors += " et al."
    submitted_by = (paper.get("submittedOnDailyBy") or {}).get("user", "")
    github = paper.get("githubRepo", "")
    summary = paper.get("summary", "")[:500]

    github_link = (
        f'<a href="{github}" target="_blank">GitHub</a>' if github else ""
    )

    return f"""
<article class="paper">
  <h2><a href="{arxiv_url(pid)}" target="_blank">{title}</a></h2>
  <div class="meta">
    <span>{authors}</span>
    <span class="upvotes">▲ {upvotes}</span>
    {f'<span>by @{submitted_by}</span>' if submitted_by else ''}
  </div>
  <div class="summary">{summary}</div>
  <div class="links">
    <a href="{arxiv_url(pid)}" target="_blank">arXiv</a>
    <a href="{arxiv_pdf_url(pid)}" target="_blank" class="arxiv-pdf">PDF</a>
    {github_link}
  </div>
</article>"""


def write_rss(papers: list[dict], date: str) -> None:
    items = []
    for p in papers:
        paper = p["paper"]
        pid = paper.get("id", "")
        title = paper.get("title", "Untitled")
        authors = ", ".join(
            a.get("name", "") for a in paper.get("authors", [])[:3]
        )
        summary = paper.get("summary", "")[:800]
        pub_date = paper.get("publishedAt", date)

        items.append(f"""    <item>
      <title>{escape_xml(title)}</title>
      <link>{arxiv_url(pid)}</link>
      <guid isPermaLink="false">{pid}</guid>
      <description>{escape_xml(f"{authors} — {summary}")}</description>
      <pubDate>{pub_date}</pubDate>
    </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{SITE_TITLE}</title>
    <link>{RSS_FEED_URL}</link>
    <description>Daily HuggingFace papers mirrored for access from China</description>
    <language>en</language>
    <lastBuildDate>{date}</lastBuildDate>
    <atom:link href="{RSS_FEED_URL}/rss.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>"""

    (OUTPUT_DIR / "rss.xml").write_text(rss, encoding="utf-8")


def escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace(
        '"', "&quot;"
    ).replace("'", "&apos;")


def write_daily_json(papers: list[dict], date: str) -> None:
    data = {
        "date": date,
        "count": len(papers),
        "papers": [
            {
                "id": p["paper"]["id"],
                "title": p["paper"].get("title"),
                "authors": [a["name"] for a in p["paper"].get("authors", [])],
                "summary": p["paper"].get("summary"),
                "upvotes": p.get("upvotes", 0),
                "publishedAt": p["paper"].get("publishedAt"),
                "arxivUrl": arxiv_url(p["paper"]["id"]),
                "arxivPdfUrl": arxiv_pdf_url(p["paper"]["id"]),
                "githubRepo": p["paper"].get("githubRepo"),
            }
            for p in papers
        ],
    }
    (OUTPUT_DIR / "index.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_archive_page(archive: dict, current_date: str) -> None:
    """Generate archive page with date navigation and paper listing."""
    rows = ""
    for pid, entry in sorted(
        archive["papers"].items(),
        key=lambda x: x[1].get("upvotes", 0),
        reverse=True,
    )[:200]:
        authors = ", ".join(entry.get("authors", [])[:3])
        rows += f"""
    <tr>
      <td><a href="{arxiv_url(pid)}">{pid}</a></td>
      <td><a href="{arxiv_url(pid)}">{entry['title']}</a></td>
      <td>{authors}</td>
      <td style="text-align:right">▲ {entry.get('upvotes', 0)}</td>
    </tr>"""

    date_links = "\n".join(
        f'<li><a href="#" onclick="loadArchive(\'{d}\')">{d}</a></li>'
        for d in archive["dates"][:30]
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Archive — {SITE_TITLE}</title>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Georgia,'Noto Serif SC',serif;background:#faf9f6;color:#1a1a1a;line-height:1.6}}
  .container{{max-width:960px;margin:0 auto;padding:2rem 1rem}}
  header{{border-bottom:2px solid #1a1a1a;padding-bottom:1rem;margin-bottom:1.5rem}}
  header h1{{font-size:1.8rem}} header a{{color:#666;text-decoration:none;font-size:0.9rem}}
  .layout{{display:flex;gap:2rem}}
  .sidebar{{flex:0 0 160px}}
  .sidebar ul{{list-style:none;font-size:0.82rem}}
  .sidebar li a{{color:#2563eb;text-decoration:none;display:block;padding:0.15rem 0}}
  .sidebar li a:hover{{text-decoration:underline}}
  .main{{flex:1;overflow-x:auto}}
  table{{width:100%;border-collapse:collapse;font-size:0.9rem}}
  th,td{{text-align:left;padding:0.6rem 0.5rem;border-bottom:1px solid #e8e8e8}}
  th{{font-size:0.75rem;text-transform:uppercase;color:#888;font-weight:600}}
  footer{{text-align:center;padding:2rem 0;color:#999;font-size:0.8rem;margin-top:2rem;border-top:1px solid #e8e8e8}}
  @media(max-width:600px){{.layout{{flex-direction:column}}.sidebar{{flex:none}}}}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>{SITE_TITLE} — Archive</h1>
  <a href="index.html">← Back to today</a>
</header>
<div class="layout">
  <aside class="sidebar">
    <p style="font-weight:600;margin-bottom:0.5rem">Dates</p>
    <ul>{date_links}</ul>
  </aside>
  <div class="main">
    <table>
      <thead><tr><th>ID</th><th>Title</th><th>Authors</th><th>Votes</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>
<footer>
  <p>Archive of <a href="https://huggingface.co/papers">HuggingFace Daily Papers</a></p>
</footer>
</div>
<script>
function loadArchive(date) {{
  const rows = document.querySelectorAll('tbody tr');
  fetch('archive/' + date + '.json').then(r => r.json()).then(data => {{
    const ids = new Set(data.papers.map(p => p.id));
    rows.forEach(row => {{
      row.style.display = ids.has(row.querySelector('td:first-child a').textContent.trim()) ? '' : 'none';
    }});
  }});
}}
</script>
</body>
</html>"""

    (OUTPUT_DIR / "archive.html").write_text(html, encoding="utf-8")


def write_readme() -> None:
    readme = """# HF Daily Papers Mirror

HuggingFace Daily Papers 的国内可访问镜像站。

## 原理

`huggingface.co` 被 GFW 封锁，但论文本体都在 `arxiv.org`（国内可访问）。本项目的 GitHub Action 每日从 `huggingface.co/api/daily_papers` 抓取论文列表，生成静态站托管在 GitHub Pages（`*.github.io` 国内可直连）。

## 使用方式

- **网页浏览**: `https://saffee666.github.io/hf-daily-papers-mirror/`
- **RSS 订阅**: `https://saffee666.github.io/hf-daily-papers-mirror/rss.xml`
- **JSON API**: `https://saffee666.github.io/hf-daily-papers-mirror/index.json`

## 部署

1. Fork 本仓库
2. Settings → Pages → Source: GitHub Actions
3. 修改 `scripts/fetch_and_build.py` 中的 `RSS_FEED_URL` 和 `saffee666`
4. Actions 会自动每日 UTC 0:00 运行，或手动触发

## 本地运行

```bash
pip install -r requirements.txt  # 实际上只需要 Python 标准库
python scripts/fetch_and_build.py
# 输出在 docs/ 目录
```

## 文件说明

- `scripts/fetch_and_build.py` — 抓取 API + 生成静态站
- `.github/workflows/fetch-daily.yml` — GitHub Actions 定时任务
- `docs/` — 构建产物（index.html, rss.xml, index.json, archive.html）
"""
    (Path(__file__).resolve().parent.parent / "README.md").write_text(
        readme, encoding="utf-8"
    )


def main():
    write_readme()
    papers = fetch_papers()
    build(papers)


if __name__ == "__main__":
    main()
