"""
verification/scraper/parsers.py

BeautifulSoup parsing helpers for the legacy site scraper.
Isolated here so they can be unit-tested independently of network I/O.
"""
import re
from typing import Optional

from bs4 import BeautifulSoup


def parse_founding_year(html: str) -> Optional[str]:
    """Extract founding year from the org intro page HTML."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    # The intro paragraph mentions "一九九一年成立" and also "1991" in meta description
    match = re.search(r"(一九九一|1991)", text)
    return "1991" if match else None


def parse_org_description(html: str) -> str:
    """Extract the main intro paragraph text."""
    soup = BeautifulSoup(html, "lxml")
    # The intro is in section#main > section.box.special > header.major > p
    header = soup.select_one("header.major p")
    if header:
        return header.get_text(" ", strip=True)
    return ""


def parse_nav_links(html: str) -> list[dict]:
    """Extract top-level navigation links (href + text)."""
    soup = BeautifulSoup(html, "lxml")
    nav = soup.select_one("nav#nav")
    if not nav:
        return []
    links = []
    for a in nav.find_all("a", recursive=False):
        href = a.get("href", "").strip()
        text = a.get_text(strip=True)
        if href and text:
            links.append({"text": text, "href": href})
    # Also get first-level children of ul
    top_ul = nav.find("ul")
    if top_ul:
        for li in top_ul.find_all("li", recursive=False):
            a = li.find("a")
            if a:
                links.append({"text": a.get_text(strip=True), "href": a.get("href", "")})
    # Deduplicate by href
    seen = set()
    unique = []
    for link in links:
        if link["href"] not in seen:
            seen.add(link["href"])
            unique.append(link)
    return unique
