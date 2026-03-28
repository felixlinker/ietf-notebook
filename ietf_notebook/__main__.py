import argparse
import os
from .mbox import sync_mailing_list
from .github import download_github_issues, process_github_issues
from .meetings import process_meetings
from .charter import process_charter
from .drafts import process_documents
from .transcripts import process_transcripts
from .utils import Verbosity, LogLevel, log, get_config_dir, get_wg_title
from .notebooklm import (
    get_credentials,
    create_notebook,
    upload_source,
)


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
        "--github-label",
        action="append",
        help="Include only GitHub issues with this label (can be specified multiple times)",
    )
    parser.add_argument(
        "--exclude-github-label",
        action="append",
        help="Exclude GitHub issues with this label (can be specified multiple times)",
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

    parser.add_argument(
        "--create",
        metavar="GCP_PROJECT_ID",
        help="Upload the generated files to a new notebook in NotebookLM",
    )
    parser.add_argument(
        "--credentials-file",
        default=os.path.join(get_config_dir(), "client_secrets.json"),
        help="Path to the Google Cloud OAuth client secrets file",
    )
    parser.add_argument(
        "--token-file",
        default=os.path.join(get_config_dir(), "token.json"),
        help="Path to the Google Cloud OAuth token file",
    )

    args = parser.parse_args()

    if args.create and not args.gcp_project:
        parser.error("--gcp-project is required when using --create")

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

    # 4. Transcripts
    results.extend(
        process_transcripts(
            args.wg, args.destination, force=args.force, verbose=verbosity
        )
    )

    # 5. Documents (Drafts & RFCs)
    results.extend(
        process_documents(
            args.wg, args.destination, force=args.force, verbose=verbosity
        )
    )

    # 6. GitHub Issues
    if args.github:
        gh_json = os.path.join(args.destination, f"{args.wg}-github-issues.json")
        gh_txt = os.path.join(args.destination, f"{args.wg}-github-issues.txt")

        if download_github_issues(args.github, gh_json, verbose=verbosity):
            results.extend(
                process_github_issues(
                    gh_json,
                    gh_txt,
                    include_labels=args.github_label,
                    exclude_labels=args.exclude_github_label,
                    verbose=verbosity,
                )
            )
            try:
                os.remove(gh_json)
            except OSError as err:
                log(
                    f"Error cleaning up {gh_json}: {err}",
                    verbosity,
                    level=LogLevel.ERROR,
                )
    else:
        log(
            "Skip GitHub issues: no GitHub repo provided.",
            verbosity,
            level=LogLevel.PROGRESS,
        )

    if args.create:
        gcp_project = args.create
        print("-" * 40)
        print("Exporting to NotebookLM...")

        creds = get_credentials(
            args.credentials_file, args.token_file, verbose=verbosity
        )
        if creds:
            wg_title = get_wg_title(args.wg)
            notebook_title = f"IETF {wg_title} Working Group"
            notebook_id = create_notebook(
                gcp_project, notebook_title, creds, verbose=verbosity
            )

            if notebook_id:
                success_count = 0
                # Filter results to include only text files for upload
                upload_files = [f for f in results if f.endswith(".txt")]
                for file_path in sorted(list(set(upload_files))):
                    if upload_source(
                        gcp_project,
                        notebook_id,
                        file_path,
                        creds,
                        verbose=verbosity,
                    ):
                        success_count += 1

                if success_count > 0:
                    print(
                        f"Successfully uploaded {success_count} files "
                        f"to notebook '{notebook_title}'."
                    )
                else:
                    log(
                        "No files were uploaded to the notebook.",
                        verbosity,
                        level=LogLevel.ERROR,
                    )
            else:
                log("Failed to create notebook.", verbosity, level=LogLevel.ERROR)
        else:
            log("Authentication failed.", verbosity, level=LogLevel.ERROR)

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
