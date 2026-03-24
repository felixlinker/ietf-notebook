import email
import html
import imaplib
import os
import re
from datetime import datetime, timedelta
from email import policy
from email.message import EmailMessage
from typing import List, Optional

from .utils import LogLevel, Verbosity, get_mailing_list_name, log

IMAP_SERVER = "imap.ietf.org"
IMAP_PORT = 993
IMAP_USER = "anonymous"
IMAP_PASS = "mnot+ietf-notebook@ietf.org"
BATCH_SIZE = 50


def extract_text_content(msg: EmailMessage) -> str:
    """Extract plain text from an EmailMessage, ignoring attachments and HTML."""
    try:
        body_part = msg.get_body(preferencelist=("plain",))
        if body_part:
            part_content = body_part.get_content()
            return str(part_content) if part_content is not None else ""
    except (AttributeError, ValueError, TypeError):
        pass

    # Fallback to manual walk for edge cases
    body = ""
    for part in msg.walk():
        if part.get_content_type() == "text/plain" and part.get_filename() is None:
            try:
                content = part.get_content()
                if isinstance(content, str):
                    body += content
            except (AttributeError, ValueError, TypeError):
                pass
    return body


def clean_email_text(text: str) -> str:
    """Strip signatures and quoted replies from the text, and decode HTML entities."""
    # Decode HTML entities like &nbsp;
    text = html.unescape(text)

    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        if line.strip() == "--" or line == "-- ":
            break
        if line.lstrip().startswith(">"):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def _download_batches(
    mail: imaplib.IMAP4_SSL,
    missing_uids: List[bytes],
    cache_dir: str,
    verbose: Verbosity,
) -> int:
    """Download messages in batches and save to cache. Returns count of new messages."""
    new_count = 0
    log(
        f"Downloading {len(missing_uids)} new messages in batches of {BATCH_SIZE}...",
        verbose,
        level=LogLevel.PROGRESS,
    )
    for i in range(0, len(missing_uids), BATCH_SIZE):
        batch = missing_uids[i : i + BATCH_SIZE]
        batch_str = ",".join(b.decode() for b in batch)
        status, msg_data = mail.uid("fetch", batch_str, "(RFC822)")

        if status != "OK" or not msg_data:
            continue

        for item in msg_data:
            if not isinstance(item, tuple) or len(item) < 2:
                continue

            # item[0] is the response header, item[1] is the message body
            header = item[0]
            if not isinstance(header, bytes):
                continue
            resp_header = header.decode()

            # Find UID in the response header
            uid_match = re.search(r"UID\s+(\d+)", resp_header)
            if not uid_match:
                continue

            msg_uid = uid_match.group(1)
            cache_file = os.path.join(cache_dir, f"{msg_uid}.eml")
            body = item[1]
            if not isinstance(body, bytes):
                continue

            with open(cache_file, "wb") as file_handle:
                file_handle.write(body)
            new_count += 1

        if new_count > 0:
            log(
                f"Downloaded {new_count}/{len(missing_uids)} new messages...",
                verbose,
                level=LogLevel.PROGRESS,
            )
    return new_count


def sync_mailing_list(
    wg_name: str,
    dest_folder: str,
    months: Optional[int] = None,
    verbose: Verbosity = Verbosity.STATUS,
) -> List[str]:
    """Sync mailing list via IMAP and cache messages locally. Returns list of updated files."""
    list_name = get_mailing_list_name(wg_name)
    log(
        f"Syncing list '{list_name}' for WG {wg_name} via IMAP...",
        verbose,
        level=LogLevel.STATUS,
    )

    cache_dir = os.path.join(dest_folder, ".imap-cache", list_name)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASS)

        # Quote folder name to handle spaces
        folder = f'"Shared Folders/{list_name}"'
        status, _ = mail.select(folder, readonly=True)
        if status != "OK":
            log(
                f"Error: Could not select IMAP folder '{folder}'",
                verbose,
                level=LogLevel.ERROR,
            )
            return []

        # Determine search criteria
        search_criteria = "ALL"
        if months:
            since_date = (datetime.now() - timedelta(days=30 * months)).strftime(
                "%d-%b-%Y"
            )
            search_criteria = f'(SINCE "{since_date}")'
            log(
                f"Searching for messages since {since_date}...",
                verbose,
                level=LogLevel.PROGRESS,
            )

        status, data = mail.uid("search", search_criteria)
        if status != "OK":
            log("Error: IMAP search failed.", verbose, level=LogLevel.ERROR)
            return []

        uids = data[0].split()
        log(f"Found {len(uids)} potential messages.", verbose, level=LogLevel.PROGRESS)

        # Filter out what we already have in cache
        missing_uids = []
        for uid in uids:
            uid_str = uid.decode()
            cache_file = os.path.join(cache_dir, f"{uid_str}.eml")
            if not os.path.exists(cache_file):
                missing_uids.append(uid)

        new_count = 0
        if missing_uids:
            new_count = _download_batches(mail, missing_uids, cache_dir, verbose)

        mail.logout()
        if new_count > 0:
            log(
                f"Finished downloading {new_count} new messages.",
                verbose,
                level=LogLevel.STATUS,
            )
        else:
            log("No new messages to download.", verbose, level=LogLevel.STATUS)

        # Now process all cached messages into the final archive
        # We only process the UIDs that were found in the search
        output_file = os.path.join(dest_folder, f"{wg_name}-mailing-list.txt")
        process_cache(cache_dir, output_file, [u.decode() for u in uids], verbose)
        return [output_file]

    except (imaplib.IMAP4.error, OSError) as err:
        log(f"IMAP Error: {err}", verbose, level=LogLevel.ERROR)
        return []


def process_cache(
    cache_dir: str,
    output_file: str,
    uids: Optional[List[str]] = None,
    verbose: Verbosity = Verbosity.STATUS,
) -> None:
    """Process cached .eml files and write cleaned text to output_file."""
    log(
        f"Generating mailing list archive: {output_file}...",
        verbose,
        level=LogLevel.STATUS,
    )

    # Get .eml files to process
    if uids:
        eml_files = [f"{uid}.eml" for uid in uids]
    else:
        eml_files = [fname for fname in os.listdir(cache_dir) if fname.endswith(".eml")]
        # Sort them numerically by UID
        eml_files.sort(key=lambda x: int(x.split(".")[0]))

    count = 0
    with open(output_file, "w", encoding="utf-8") as out_fh:
        for eml_file in eml_files:
            cache_path = os.path.join(cache_dir, eml_file)
            if not os.path.exists(cache_path):
                continue

            with open(cache_path, "rb") as file_handle:
                msg = email.message_from_binary_file(file_handle, policy=policy.default)

            subject = msg.get("Subject", "(No Subject)")
            from_addr = msg.get("From", "(Unknown Sender)")
            date_val = msg.get("Date", "(Unknown Date)")

            raw_body = extract_text_content(msg)
            cleaned_body = clean_email_text(raw_body)

            if not cleaned_body and subject == "(No Subject)":
                continue

            out_fh.write(f"Date: {date_val}\n")
            out_fh.write(f"From: {from_addr}\n")
            out_fh.write(f"Subject: {subject}\n\n")
            out_fh.write(cleaned_body + "\n\n")
            out_fh.write("=" * 80 + "\n\n")

            count += 1
            if count % 100 == 0:
                log(f"Processed {count} messages...", verbose, level=LogLevel.PROGRESS)

    log(
        f"Done! Extracted {count} messages to {output_file}.",
        verbose,
        level=LogLevel.STATUS,
    )
