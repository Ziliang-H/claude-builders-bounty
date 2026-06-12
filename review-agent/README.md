# Claude Review Agent

`claude-review` is a zero-dependency CLI that reviews a public GitHub pull request diff and prints a structured Markdown review comment.

## Setup

```bash
chmod +x claude-review
```

## Usage

```bash
./claude-review --pr https://github.com/owner/repo/pull/123
```

The output contains:

- Summary of changes in 2-3 sentences.
- Identified risks.
- Improvement suggestions.
- Confidence score: Low, Medium, or High.

## GitHub Action

Copy `.github/workflows/claude-review.yml` into a repository to post generated review text into the Actions summary for every pull request. The workflow does not require secrets for public PR diffs.

## How It Works

The CLI downloads the public `.diff` for the PR, counts changed files, additions, deletions, and hunks, then applies deterministic review heuristics for risk and confidence. It is intentionally transparent and works without external AI credentials, which makes it safe for default CI runs.
