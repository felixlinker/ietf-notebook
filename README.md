# ietf-notebook

Automate gathering of [NotebookLM](https://notebooklm.google.com/)-ready documents for an [IETF](https://www.ietf.org/) Working Group.

This tool gathers Working Group charters, drafts, meeting minutes, PDF slides, mailing list archives, and GitHub issues into a set of clean text files and PDFs suitable for ingestion into NotebookLM.

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
- `--force`: Force re-downloading of existing files. By default, the tool skips files that already exist in the destination.
- `--quiet`: No messages except for errors and the final resource summary.
- `--verbose`: Detailed progress reporting.

### Default Behavior

- **Charters, Meetings, and Documents**: Existing files are skipped unless `--force` is used.
- **Mailing List Discovery**: The tool automatically finds the mailing list for the WG from the Datatracker.
- **IMAP Retrieval**: Mailing list archives are fetched via IMAP from `imap.ietf.org` and cached locally in `.imap-cache/`.
- **GitHub Strategy**: The tool first checks for `archive.json` on the `gh-pages` branch (common in repos using [Martin Thomson's template](https://github.com/martinthomson/internet-draft-template)).
- **GitHub Auth**: To avoid rate limits when fetching from the API, set the `GITHUB_TOKEN` environment variable.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
