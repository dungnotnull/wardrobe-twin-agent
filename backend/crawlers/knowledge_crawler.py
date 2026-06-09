"""Knowledge base crawler system.

Crawls ArXiv, HuggingFace, and Papers with Code for new VTON/fashion AI research.
Updates SECOND-KNOWLEDGE-BRAIN.md and the knowledge_entries DB table.
"""
from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx

from backend.db.database import db
from backend.core.models import KnowledgeEntry, CrawlResult
from config.settings import settings

logger = logging.getLogger(__name__)

SECOND_BRAIN_PATH = settings.BASE_DIR / "SECOND-KNOWLEDGE-BRAIN.md"


class BaseCrawler(ABC):
    source_name: str = "base"

    @abstractmethod
    async def fetch_entries(self) -> list[dict]:
        ...

    def format_entry(self, raw: dict) -> KnowledgeEntry:
        raise NotImplementedError


class ArXivCrawler(BaseCrawler):
    source_name = "arxiv"

    async def fetch_entries(self) -> list[dict]:
        queries = ["virtual try-on diffusion", "clothing fitting 3D body estimation", "outfit compatibility fashion AI", "garment generation neural network"]
        entries = []
        async with httpx.AsyncClient(timeout=30) as client:
            for query in queries:
                try:
                    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&max_results=5&sortBy=submittedDate&sortOrder=descending"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    entries.extend(self._parse_arxiv_response(resp.text, query))
                except Exception as e:
                    logger.warning("ArXiv crawl failed for '%s': %s", query, e)
        return entries

    def _parse_arxiv_response(self, xml_text: str, query: str) -> list[dict]:
        entries = []
        for entry_xml in re.findall(r'<entry>(.*?)</entry>', xml_text, re.DOTALL):
            title = re.search(r'<title>(.*?)</title>', entry_xml, re.DOTALL)
            link = re.search(r'<id>(.*?)</id>', entry_xml)
            summary = re.search(r'<summary>(.*?)</summary>', entry_xml, re.DOTALL)
            published = re.search(r'<published>(.*?)</published>', entry_xml)
            if title and link:
                entries.append({"title": title.group(1).strip().replace("\n", " "), "url": link.group(1).strip(), "year": int(published.group(1)[:4]) if published else None, "venue": "arXiv", "relevance": query, "metadata": {"summary": summary.group(1).strip()[:200] if summary else ""}})
        return entries

    def format_entry(self, raw: dict) -> KnowledgeEntry:
        return KnowledgeEntry(title=raw["title"], source=self.source_name, url=raw.get("url"), entry_type="paper", year=raw.get("year"), venue=raw.get("venue", "arXiv"), relevance=raw.get("relevance"), metadata=raw.get("metadata", {}))


class HuggingFaceCrawler(BaseCrawler):
    source_name = "huggingface"

    async def fetch_entries(self) -> list[dict]:
        tags = ["virtual-try-on", "fashion", "body-pose", "garment"]
        entries = []
        async with httpx.AsyncClient(timeout=30) as client:
            for tag in tags:
                try:
                    url = f"https://huggingface.co/api/models?filter={tag}&sort=lastModified&direction=-1&limit=5"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    for model in resp.json():
                        entries.append({"title": model.get("modelId", ""), "url": f"https://huggingface.co/{model.get('modelId', '')}", "year": None, "venue": "HuggingFace", "relevance": tag, "metadata": {"downloads": model.get("downloads", 0), "tags": model.get("tags", []), "pipeline_tag": model.get("pipeline_tag", "")}})
                except Exception as e:
                    logger.warning("HuggingFace crawl failed for tag '%s': %s", tag, e)
        return entries

    def format_entry(self, raw: dict) -> KnowledgeEntry:
        return KnowledgeEntry(title=raw["title"], source=self.source_name, url=raw.get("url"), entry_type="model", year=raw.get("year"), venue=raw.get("venue", "HuggingFace"), relevance=raw.get("relevance"), metadata=raw.get("metadata", {}))


class PapersWithCodeCrawler(BaseCrawler):
    source_name = "paperswithcode"

    async def fetch_entries(self) -> list[dict]:
        tasks = ["virtual-try-on", "human-pose-estimation", "fashion-compatibility"]
        entries = []
        async with httpx.AsyncClient(timeout=30) as client:
            for task in tasks:
                try:
                    url = f"https://paperswithcode.com/api/v1/search/?q={task}&page=1&items_per_page=5"
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    for result in resp.json().get("results", []):
                        paper = result.get("paper", {})
                        entries.append({"title": paper.get("title", ""), "url": paper.get("url_abs", paper.get("url", "")), "year": paper.get("publication_date", "")[:4] if paper.get("publication_date") else None, "venue": paper.get("conference", "Papers With Code"), "relevance": task, "metadata": {"task": task, "citation_count": paper.get("citation_count", 0)}})
                except Exception as e:
                    logger.warning("PapersWithCode crawl failed for task '%s': %s", task, e)
        return entries

    def format_entry(self, raw: dict) -> KnowledgeEntry:
        return KnowledgeEntry(title=raw["title"], source=self.source_name, url=raw.get("url"), entry_type="paper", year=raw.get("year"), venue=raw.get("venue", "Papers With Code"), relevance=raw.get("relevance"), metadata=raw.get("metadata", {}))


async def run_all_crawlers() -> list[CrawlResult]:
    crawlers = [ArXivCrawler(), HuggingFaceCrawler(), PapersWithCodeCrawler()]
    results = []
    for crawler in crawlers:
        start = time.time()
        try:
            raw_entries = await crawler.fetch_entries()
            added, skipped = 0, 0
            for raw in raw_entries:
                entry = crawler.format_entry(raw)
                if not entry.title or db.knowledge_entry_exists(entry.title, entry.source):
                    skipped += 1
                    continue
                entry_dict = entry.model_dump()
                entry_dict["added_date"] = entry_dict.get("added_date") or datetime.utcnow().isoformat()
                db.insert_knowledge_entry(entry_dict)
                added += 1
            elapsed = round(time.time() - start, 2)
            result = CrawlResult(source=crawler.source_name, entries_found=len(raw_entries), entries_added=added, entries_skipped=skipped, crawl_time_seconds=elapsed)
            results.append(result)
            db.insert_crawl_log(result.model_dump())
        except Exception as e:
            elapsed = round(time.time() - start, 2)
            results.append(CrawlResult(source=crawler.source_name, entries_found=0, entries_added=0, entries_skipped=0, errors=[str(e)], crawl_time_seconds=elapsed))
    _update_brain_file(results)
    return results


def _update_brain_file(crawl_results: list[CrawlResult]) -> None:
    total_added = sum(r.entries_added for r in crawl_results)
    total_skipped = sum(r.entries_skipped for r in crawl_results)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d")
    entry = f"\n| {timestamp} | auto-crawl | {total_added} added, {total_skipped} skipped | Automated crawl update |\n"
    try:
        content = SECOND_BRAIN_PATH.read_text(encoding="utf-8") if SECOND_BRAIN_PATH.exists() else ""
        marker = "## Knowledge Update Log"
        if marker in content:
            pos = content.find(marker)
            table_start = content.find("| Date | Source |", pos)
            if table_start != -1:
                nl = content.find("\n", table_start)
                nl = content.find("\n", nl + 1)
                content = content[:nl + 1] + entry + content[nl + 1:]
            else:
                content += f"\n{marker}\n\n| Date | Source | Items Added | Summary |\n|------|--------|-------------|--------|\n{entry}\n"
        else:
            content += f"\n{marker}\n\n| Date | Source | Items Added | Summary |\n|------|--------|-------------|--------|\n{entry}\n"
        SECOND_BRAIN_PATH.write_text(content, encoding="utf-8")
    except Exception as e:
        logger.error("Failed to update SECOND-KNOWLEDGE-BRAIN.md: %s", e)


def schedule_crawls() -> None:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        import asyncio
        scheduler = BackgroundScheduler()
        async def _run():
            await run_all_crawlers()
        def _sync_run():
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_run())
            loop.close()
        scheduler.add_job(_sync_run, "cron", day_of_week=settings.CRAWL_SCHEDULE_DAY, hour=settings.CRAWL_SCHEDULE_HOUR)
        scheduler.start()
        logger.info("Crawl scheduler started")
    except Exception as e:
        logger.warning("Could not start crawl scheduler: %s", e)
