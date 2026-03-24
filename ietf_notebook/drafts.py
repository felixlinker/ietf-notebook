import os
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .utils import LogLevel, Verbosity, log, fetch_resource


def get_adopted_drafts(
    wg_name: str, verbose: Verbosity = Verbosity.STATUS
) -> List[Dict[str, Any]]:
    """Scrape WG documents page for active drafts."""
    url = f"https://datatracker.ietf.org/wg/{wg_name}/documents/"
    log(f"Finding adopted drafts for {wg_name}...", verbose, level=LogLevel.STATUS)
    res = fetch_resource(url)
    if not res:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    drafts = []

    # Strategy: look for links starting with /doc/draft-ietf-{wg_name}-
    # The link text contains the draft name + version
    pattern = f"/doc/draft-ietf-{wg_name}-"
    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href")
        if not isinstance(href, str) or not href.startswith(pattern):
            continue

        text = a_tag.get_text(strip=True)
        # Text usually looks like "draft-ietf-aipref-vocab-05"
        if text.startswith(f"draft-ietf-{wg_name}-"):
            # Use regex to find "draft-..." + extension
            match = re.search(
                r"(draft-ietf-" + re.escape(wg_name) + r"-.*?)-(\d+)$", text
            )
            if match:
                draft_name = match.group(1)
                try:
                    current_rev = int(match.group(2))
                    drafts.append({"name": draft_name, "max_rev": current_rev})
                except ValueError:
                    continue

    # De-duplicate and keep the highest revision found
    unique_drafts: Dict[str, int] = {}
    for draft_entry in drafts:
        name = str(draft_entry["name"])
        rev = int(draft_entry["max_rev"])
        if name not in unique_drafts or rev > unique_drafts[name]:
            unique_drafts[name] = rev

    result = [{"name": name, "max_rev": rev} for name, rev in unique_drafts.items()]
    return result


def process_drafts(
    wg_name: str,
    destination: str,
    force: bool = False,
    verbose: Verbosity = Verbosity.STATUS,
) -> List[str]:
    """Download all revisions of WG drafts as text."""
    updated = []
    drafts = get_adopted_drafts(wg_name, verbose)
    if not drafts:
        log(f"No adopted drafts found for {wg_name}.", verbose, level=LogLevel.STATUS)
        return []

    for draft in drafts:
        name = draft["name"]
        max_rev = draft["max_rev"]
        log(
            f"Processing draft: {name} (revs 00 to {max_rev:02d})",
            verbose,
            level=LogLevel.STATUS,
        )

        for rev in range(max_rev + 1):
            rev_str = f"{rev:02d}"
            filename = f"{name}-{rev_str}.txt"
            filepath = os.path.join(destination, filename)

            if not force and os.path.exists(filepath):
                continue

            url = f"https://www.ietf.org/archive/id/{name}-{rev_str}.txt"
            log(f"Downloading {filename}...", verbose, level=LogLevel.PROGRESS)
            res = fetch_resource(url)
            if res:
                with open(filepath, "w", encoding="utf-8") as out_fh:
                    out_fh.write(str(res.text))
                updated.append(filepath)

    return updated
