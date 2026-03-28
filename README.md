# ietf-notebook

Automate gathering of [NotebookLM](https://notebooklm.google.com/)-ready documents for an [IETF](https://www.ietf.org/) Working Group.

This tool gathers Working Group charters, drafts, meeting minutes, PDF slides, meeting transcripts, mailing list archives, and GitHub issues into a set of clean text files and PDFs suitable for ingestion into NotebookLM.

## Installation

```bash
pipx install ietf-notebook
```

## Usage

```bash
ietf-notebook [wg_shortname] _OPTIONS_
```

### Options

- `wg_shortname`: IETF Working Group short name (e.g., `httpbis`).
- `--destination`: Folder to save files in (default: current directory).
- `--github`: GitHub org/repo for issues (e.g., `ietf-wg-httpbis/wg-materials`).
- `--github-label`: Include only GitHub issues with this label (can be specified multiple times).
- `--exclude-github-label`: Exclude GitHub issues with this label (can be specified multiple times).
- `--months`: Number of months of mailing list history to fetch (default: all).
- `--create`: See "NotebookLM Export" below.
- `--force`: Force re-downloading of existing files. By default, the tool skips files that already exist in the destination.
- `--quiet`: No messages except for errors and the final resource summary.
- `--verbose`: Detailed progress reporting.

### Default Behavior

- **Charters, Meetings, and Documents**: Existing files are skipped unless `--force` is used.
- **Mailing List Discovery**: The tool automatically finds the mailing list for the WG from the Datatracker.
- **IMAP Retrieval**: Mailing list archives are fetched via IMAP from `imap.ietf.org` and cached locally in `~/.cache/ietf-notebook/{wg_name}/imap-cache/`.
- **GitHub Strategy**: The tool first checks for `archive.json` on the `gh-pages` branch.
- **Transcripts**: Meeting transcripts are fetched from the `ietf-minutes-data` repository and cached locally in `~/.cache/ietf-notebook/{wg_name}/transcript-cache/`.
- **GitHub Auth**: To avoid rate limits when fetching from the API, set the `GITHUB_TOKEN` environment variable.
- **NotebookLM Export**: Use the `--create` flag to automatically create a new notebook in NotebookLM Enterprise and upload all generated archives as sources.

### NotebookLM Export (Enterprise only)

If you have a Google Workspace Enterprise account with NotebookLM enabled, you can programmatically create a notebook and upload your gathered resources.

```bash
ietf-notebook httpbis --create [MY_PROJECT_ID]
```

**Requirements:**
1.  **Google Cloud Project**: You must have a GCP project with the **Discovery Engine API** enabled.
2.  **OAuth Credentials**: You need an "OAuth 2.0 Client ID" (Type: Desktop App) from the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
3.  **Client Secrets**: Save the JSON file as `client_secrets.json` in `~/.config/ietf-notebook/` (or specify its path with `--credentials-file`).

The first time you run this, a browser window will open to authorize the application. Your access permissions will be cached in `~/.config/ietf-notebook/token.json` (or you can specify with `--token-file`).

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
