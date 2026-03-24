from typing import List
from bs4 import BeautifulSoup
from .utils import Verbosity, LogLevel, clean_html, fetch_resource, log


def process_charter(
    wg_name: str, output_file: str, verbose: Verbosity = Verbosity.STATUS
) -> List[str]:
    """Fetch the WG charter and write to output_file. Returns list of updated files."""
    url = f"https://datatracker.ietf.org/doc/charter-ietf-{wg_name}/"
    log(f"Fetching charter for {wg_name}...", verbose, level=LogLevel.STATUS)

    # Try fetching as markdown first
    res = fetch_resource(url, headers={"Accept": "text/markdown"})
    if not res:
        log(f"Error: Could not fetch charter from {url}", verbose, level=LogLevel.ERROR)
        return []

    charter_text = ""
    if "text/markdown" in res.headers.get("Content-Type", ""):
        charter_text = res.text
    else:
        # Fallback to HTML cleaning
        html = res.text
        bs_soup = BeautifulSoup(html, "html.parser")

        # The charter text is usually in a div with class 'card-body' on the datatracker.
        charter_div = bs_soup.find("div", class_="card-body")

        if not charter_div:
            # Fallback to charter-text or similar
            charter_div = bs_soup.find("div", class_="charter-text")

        if not charter_div:
            # Fallback to looking for the "Charter" heading
            heading = None
            for h2 in bs_soup.find_all("h2"):
                if h2.string and "Charter" in h2.string:
                    heading = h2
                    break
            if heading:
                charter_div = heading.find_next("div")

        if charter_div:
            charter_text = clean_html(str(charter_div))
        else:
            # Last resort: clean the whole page but it might be noisy
            log(
                "Warning: Could not isolate charter text, cleaning entire page.",
                verbose,
                level=LogLevel.PROGRESS,
            )
            charter_text = clean_html(html)

    if charter_text:
        with open(output_file, "w", encoding="utf-8") as out_fh:
            out_fh.write(f"Working Group Charter: {wg_name}\n")
            out_fh.write(f"Source: {url}\n")
            out_fh.write("=" * 80 + "\n\n")
            out_fh.write(charter_text + "\n")

        log(f"Done! Charter written to {output_file}.", verbose, level=LogLevel.STATUS)
        return [output_file]
    return []
