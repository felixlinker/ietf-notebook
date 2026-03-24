# ietf-notebook

Automate gathering of [NotebookLM(https://notebooklm.google.com/)]-ready documents for an [IETF](https://www.ietf.org/) Working Group.

This tool gathers Working Group charters, drafts, meeting minutes, PDF slides, mailing list archives, and GitHub issues into a set of clean text files and PDFs suitable for ingestion into NotebookLM.

## Installation

```bash
pipx install ietf-notebook
```

## Usage

```bash
ietf-notebook [wg_shortname] --destination [folder] --github [owner/repo] --months [number]
```

### Options

- `wg`: IETF Working Group short name (e.g., `httpbis`).
- `--destination`: Folder to save files in (default: current directory).
- `--github`: GitHub short name (e.g., `ietf-wg-httpbis/wg-materials`).
- `--months`: Number of months of mailing list history to fetch (default: all).
- `--force`: Force re-downloading of existing files. By default, the tool skips files that already exist in the destination.
- `--quiet`: No messages except for errors and the final resource summary.
- `--verbose`: Detailed progress reporting (default is high-level status only).

### Default Behavior

- **Charters, Meetings, and Mbox**: Existing files are skipped unless `--force` is used.
- **Mailing List Discovery**: The tool automatically finds the mailing list for the WG from the Datatracker.
- **IMAP Retrieval**: Mailing list archives are fetched via IMAP from `imap.ietf.org` and cached locally in `.imap-cache/`.
- **GitHub Issues**: GitHub issues are always re-fetched by default (equivalent to `--force`) to ensure the latest comments are included.
- **PDF Materials**: PDF slides are downloaded directly into the destination folder with names like `ietf124-slides-124-aipref-overview-00.pdf`.
- **Markdown**: The tool automatically prioritizes raw Markdown content for charters and minutes.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
