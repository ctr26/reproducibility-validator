# Reproducibility Validator

## Vision
Website that validates codebases to verify scientific research can be reproduced.

## Business Model
- **Ad-funded** (free to use)
- Scientists submit repos, get reproducibility score
- Badges for papers/repos that pass

## Core Features

### Analysis
- [ ] Environment detection (requirements.txt, environment.yml, Dockerfile)
- [ ] Dependency pinning check
- [ ] Random seed detection
- [ ] Data availability check
- [ ] Documentation quality score
- [ ] Test coverage estimation

### Output
- Reproducibility score (0-100)
- Specific recommendations
- Embeddable badge for README/paper
- Report PDF for journals

## Tech Stack
- Frontend: Astro/vanilla (cheap, static)
- Backend: Cloudflare Workers
- Analysis: Python workers (containerized)
- Ads: Google AdSense / Carbon Ads

## Target Users
- Researchers submitting papers
- Reviewers verifying submissions
- Journals wanting reproducibility badges
- Lab PIs ensuring standards

## Differentiators
- Free (ad-supported)
- Fast feedback
- Actionable recommendations
- Journal-accepted badges

## Constraints
- Cheap to run
- Scalable (cloud-first)
- Minimal dependencies

---

*GitHub: craggles17/reproducibility-validator*
*Created: 2026-02-16*
