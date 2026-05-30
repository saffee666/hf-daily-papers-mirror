# HF Daily Papers Mirror

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
