---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 94bcf2b5d315f1c98c48e4012527ec7f_c66179b88e6611f1b82d525400287e28
    ReservedCode1: h1YzX2eLycqotcGpfKU3Oed9m63JVyqzURLu1eJRC6u6J1i/EhY5Eb2Oq2vhu3uWs36wmILM3q3H7ZnjL4gmAl1cSyUqhCdBmqLBiEC2q4DIDdMuYnXVSNm94R1ZVCMgLBLLKC8Dk6Ary83aLUzrNYNy3tiO4sM/IZmDqh8Olq3cz+/k5XlgYM8JiLA=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 94bcf2b5d315f1c98c48e4012527ec7f_c66179b88e6611f1b82d525400287e28
    ReservedCode2: h1YzX2eLycqotcGpfKU3Oed9m63JVyqzURLu1eJRC6u6J1i/EhY5Eb2Oq2vhu3uWs36wmILM3q3H7ZnjL4gmAl1cSyUqhCdBmqLBiEC2q4DIDdMuYnXVSNm94R1ZVCMgLBLLKC8Dk6Ary83aLUzrNYNy3tiO4sM/IZmDqh8Olq3cz+/k5XlgYM8JiLA=
---

# ai-code-review-cli

> Lightweight CLI tool for automated AI-powered pull request code review — built for open-source maintainers.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/YOUR_USERNAME/ai-code-review-cli/pulls)

---

## Why ai-code-review-cli?

Maintaining an open-source project means reviewing dozens of pull requests — every week. Manually checking for bugs, security flaws, and style inconsistencies is time-consuming and error-prone.

**ai-code-review-cli** automates the first-pass review using AI, so you can focus on architecture decisions and community engagement. It reads a git diff, sends it to an LLM with a structured review prompt, and produces a human-readable report — directly in your terminal, as Markdown, or as JSON for CI pipelines.

---

## Features

| Feature | Description |
|---|---|
| 🔍 **Automated Diff Review** | Point it at any two git refs and get a full review. |
| 🤖 **Multi-Model Support** | Works with GPT-4o, GPT-4o-mini, or any OpenAI-compatible API. |
| 🛡️ **Severity Classification** | Findings tagged as `critical`, `warning`, or `suggestion`. |
| 📋 **Structured Output** | Terminal, Markdown (GitHub-friendly), or raw JSON. |
| ⚡ **CI-Ready** | Use it in GitHub Actions for automated PR checks. |
| 🪶 **Minimal Dependencies** | Only `openai` — everything else is stdlib. |
| 🌐 **Custom API Base** | Proxy support for restricted network environments. |

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Git installed and accessible from your terminal
- An [OpenAI API key](https://platform.openai.com/api-keys) (or any compatible endpoint)

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/ai-code-review-cli.git
cd ai-code-review-cli

# Install dependencies
pip install openai
```

### Usage

```bash
# Set your API key
export OPENAI_API_KEY="sk-..."

# Review the diff between main and current branch
python cli.py --base main --head HEAD

# Output as GitHub-flavoured Markdown
python cli.py --base main --head HEAD --format markdown

# Write result to a file
python cli.py --base main --head HEAD --format markdown --output review.md

# Use a pre-generated diff file
python cli.py --diff-file my-diff.patch --format json

# Use a custom API endpoint (e.g. local LLM proxy)
python cli.py --base-url http://localhost:11434/v1 --model llama3
```

### GitHub Actions Integration

```yaml
# .github/workflows/ai-review.yml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install openai
      - name: Run AI review
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python cli.py --base origin/${{ github.base_ref }} --head ${{ github.sha }} \
            --format markdown --output review.md
      - name: Post review comment
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('review.md', 'utf8');
            await github.rest.issues.createComment({
              ...context.repo,
              issue_number: context.issue.number,
              body
            });
```

---

## CLI Reference

| Flag | Type | Default | Description |
|---|---|---|---|
| `--base` | `str` | `main` | Base git ref for diff comparison |
| `--head` | `str` | `HEAD` | Head git ref for diff comparison |
| `--diff-file` | `path` | — | Path to a pre-generated diff file |
| `--model` | `str` | `gpt-4o-mini` | OpenAI model name |
| `--max-tokens` | `int` | `2048` | Max tokens for the AI response |
| `--temperature` | `float` | `0.3` | Sampling temperature |
| `--format` | `choice` | `terminal` | Output: `terminal`, `markdown`, `json` |
| `--api-key` | `str` | `$OPENAI_API_KEY` | OpenAI API key |
| `--base-url` | `str` | — | Custom API base URL |
| `--output` | `path` | — | Write output to file |
| `--version` | — | — | Print version and exit |

---

## Example Output

```
Summary: The PR introduces a new caching layer with clean separation of concerns.
  Minor style issues in docstrings and one potential race condition identified.
Verdict: APPROVED
------------------------------------------------------------
  [W][security] src/cache.py:42 — Shared cache dict is not thread-safe.
  [S][style] src/utils.py:17 — Docstring missing for public function `format_key`.
  [S][style] src/utils.py:23 — Line exceeds 88 characters; consider wrapping.
```

---

## Project Structure

```
ai-code-review-cli/
├── cli.py              # Main entry point
├── README.md           # This file
├── LICENSE             # MIT License
└── .github/
    └── workflows/
        └── ai-review.yml   # CI example
```

---

## Roadmap

- [x] **v0.1.0** — Core CLI: git diff ingestion, OpenAI review, terminal/Markdown/JSON output
- [ ] **v0.2.0** — Inline diff annotation with suggestions rendered next to source lines
- [ ] **v0.3.0** — Multi-provider support (Anthropic Claude, Google Gemini, local Ollama)
- [ ] **v0.4.0** — Review history & trend analysis dashboard
- [ ] **v0.5.0** — `review.yaml` config file per repository (custom rules, ignore patterns)
- [ ] **v1.0.0** — GitHub App with automatic PR comment on every push

---

## Contributing

Contributions are welcome! Please open an issue to discuss your idea before submitting a PR.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m "Add amazing feature"`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for full text.

Copyright (c) 2025 YOUR_NAME

---

## Acknowledgements

Built for the open-source community. Inspired by the daily grind of PR review.
*（内容由AI生成，仅供参考）*
