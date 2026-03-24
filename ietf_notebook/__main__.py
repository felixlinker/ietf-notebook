import argparse
import os
from .mbox import sync_mailing_list
from .github import download_github_issues, process_github_issues
from .meetings import process_meetings
from .charter import process_charter
from .drafts import process_documents
from .utils import Verbosity, LogLevel, log


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automate creation of NotebookLM-ready documents for an IETF Working Group."
    )
    parser.add_argument("wg", help="IETF Working Group short name (e.g., 'httpbis')")
    parser.add_argument(
        "--github", help="GitHub owner/repo (e.g., 'ietf-wg-httpbis/wg-materials')"
    )
    parser.add_argument(
        "--months",
        type=int,
        default=None,
        help="Number of months of mailing list archives to fetch (default: all)",
    )
    parser.add_argument(
        "--destination",
        default=".",
        help="Destination folder (default: current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite resources that already exist in the destination",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output errors")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Detailed progress reporting"
    )

    args = parser.parse_args()

    if not os.path.exists(args.destination):
        os.makedirs(args.destination)

    verbosity = Verbosity.STATUS
    if args.quiet:
        verbosity = Verbosity.QUIET
    elif args.verbose:
        verbosity = Verbosity.VERBOSE

    if verbosity != Verbosity.QUIET:
        print(f"Processing WG: {args.wg}")
        print(f"Destination: {args.destination}")
        if args.force:
            print("Force mode: overwriting existing files.")
        else:
            print("Default mode: skipping existing files (except GitHub issues).")
        print("-" * 40)

    results = []

    # 1. Charter
    charter_file = os.path.join(args.destination, f"{args.wg}-charter.txt")
    if not args.force and os.path.exists(charter_file):
        log(
            f"Skipping charter: {charter_file} already exists.",
            verbosity,
            level=LogLevel.PROGRESS,
        )
    else:
        results.extend(process_charter(args.wg, charter_file, verbose=verbosity))

    # 2. Meetings
    results.extend(
        process_meetings(args.wg, args.destination, force=args.force, verbose=verbosity)
    )

    # 3. Mailing List
    results.extend(
        sync_mailing_list(
            args.wg, args.destination, months=args.months, verbose=verbosity
        )
    )

    # 4. Documents (Drafts & RFCs)
    results.extend(
        process_documents(args.wg, args.destination, force=args.force, verbose=verbosity)
    )

    # 5. GitHub Issues
    if args.github:
        gh_json = os.path.join(args.destination, f"{args.wg}-github-issues.json")
        gh_txt = os.path.join(args.destination, f"{args.wg}-github-issues.txt")

        if download_github_issues(args.github, gh_json, verbose=verbosity):
            results.extend(process_github_issues(gh_json, gh_txt, verbose=verbosity))
            try:
                os.remove(gh_json)
            except OSError as err:
                log(f"Error cleaning up {gh_json}: {err}", verbosity, level=LogLevel.ERROR)
    else:
        log(
            "Skip GitHub issues: no GitHub repo provided.",
            verbosity,
            level=LogLevel.PROGRESS,
        )

    if verbosity != Verbosity.QUIET:
        print("-" * 40)
        print("All tasks completed.")

    if results:
        print("\n## Updated Resources")
        for res in sorted(list(set(results))):
            rel_path = os.path.relpath(res, os.getcwd())
            print(f"- {rel_path}")


if __name__ == "__main__":
    main()
