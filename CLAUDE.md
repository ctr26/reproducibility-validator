# Reproducibility Validator

## Problem
Scientific code is often not reproducible. Researchers publish papers but their code lacks:
- Pinned dependencies
- Random seed management
- Data availability documentation
- Tests

Reviewers and journals have no quick way to assess reproducibility.

## Solution
A website that analyzes codebases and scores reproducibility:
- Checks environment files, dependency pinning, random seeds
- Outputs a 0-100 score with actionable recommendations
- Generates embeddable badges for papers/READMEs
- Free to use, ad-funded

## Tech
- Static frontend (vanilla HTML/JS)
- Cloudflare Workers API
- Python analysis engine
- ~$12/month to run

See PROJECT_SPEC.md for full details.
