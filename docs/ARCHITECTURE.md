# Reproducibility Validator - System Architecture

## Overview

The Reproducibility Validator is a **serverless, ad-funded** platform for analyzing scientific code repositories. It prioritizes **low cost, high scalability, and minimal dependencies**.

---

## System Components

### 1. Static Frontend (web/)
- **Tech**: Vanilla HTML/CSS/JS (no framework needed)
- **Hosting**: Cloudflare Pages (free tier)
- **Features**:
  - Landing page with validator form
  - Real-time score display
  - Badge generation UI
  - Ad placement zones (Google AdSense / Carbon Ads)

**Why vanilla?**
- Zero build step = faster deploys
- No framework lock-in
- Smaller bundle = faster loads
- Cheaper hosting

### 2. API Layer (Cloudflare Workers)
- **Endpoints**:
  - `POST /api/analyze` - Trigger repository analysis
  - `GET /api/badge/{repo_id}` - Serve SVG badges
  - `GET /api/verify/{repo_id}` - Badge verification
  - `GET /api/results/{analysis_id}` - Fetch results

**Worker Flow**:
```
User submits repo URL
  → Worker validates URL
  → Queues analysis job
  → Returns job ID
  → Frontend polls for results
```

**Storage**: Cloudflare KV for:
- Analysis results (TTL: 30 days)
- Badge data (cached)
- Rate limiting counters

### 3. Analysis Engine (Python Container)
- **Runtime**: Cloudflare Workers + Python (via Pyodide or external runner)
- **Alternative**: AWS Lambda (if Pyodide too limited)
  
**Process**:
1. Clone repo (shallow, depth=1)
2. Run checks in parallel:
   - File detection (glob search)
   - Pattern matching (regex)
   - Dependency parsing
   - Code analysis
3. Calculate scores
4. Generate recommendations
5. Store results in KV
6. Return JSON

**Optimizations**:
- Shallow clone (--depth 1)
- Limit repo size (max 100MB)
- Timeout after 30 seconds
- Cache common repos

### 4. Badge System
**SVG Generation**:
- Dynamic SVG template
- Color-coded by score:
  - 90-100: Green (#44cc11)
  - 75-89: Light Green (#97ca00)
  - 60-74: Yellow (#dfb317)
  - 40-59: Orange (#fe7d37)
  - 0-39: Red (#e05d44)

**Verification Endpoint**:
- Embed verification URL in badge
- Journals can verify badge authenticity
- Links to full report

---

## Data Flow

```
┌─────────────┐
│   Browser   │
│  (Frontend) │
└──────┬──────┘
       │ 1. Submit repo URL
       ▼
┌─────────────────────┐
│ Cloudflare Worker   │
│  - Validate input   │
│  - Queue job        │
│  - Return job ID    │
└──────┬──────────────┘
       │ 2. Trigger analysis
       ▼
┌─────────────────────┐
│  Python Container   │
│  - Clone repo       │
│  - Run checks       │
│  - Calculate score  │
└──────┬──────────────┘
       │ 3. Store results
       ▼
┌─────────────────────┐
│  Cloudflare KV      │
│  - Analysis results │
│  - Badge data       │
└──────┬──────────────┘
       │ 4. Fetch results
       ▼
┌─────────────────────┐
│     Browser         │
│  - Display score    │
│  - Show badge       │
│  - List fixes       │
└─────────────────────┘
```

---

## Scoring Algorithm

### Category Weights
| Category        | Weight | Description |
|----------------|--------|-------------|
| Environment    | 25%    | Dependency management, version pinning |
| Randomness     | 20%    | Seed control, deterministic execution |
| Data           | 20%    | Data availability, scripts, samples |
| Documentation  | 20%    | README, instructions, examples |
| Testing        | 15%    | Tests, CI/CD, coverage |

### Point System
Each category has **checks** with point values:
- Critical checks: 10 points
- Important checks: 5-8 points
- Nice-to-have: 2-5 points

**Score Calculation**:
1. Sum points earned per category
2. Normalize to 0-100 per category
3. Apply category weight
4. Sum weighted scores → **Overall Score (0-100)**

### Rating Thresholds
- **Excellent**: 90-100
- **Good**: 75-89
- **Fair**: 60-74
- **Poor**: 40-59
- **Critical**: 0-39

---

## Check Definitions

All checks are defined in **data/checks.json** for easy modification.

### Environment Checks
1. **env_file_exists** (10 pts)
   - Detects: requirements.txt, environment.yml, Dockerfile, pyproject.toml
   
2. **dependencies_pinned** (10 pts, CRITICAL)
   - Verifies: All deps use exact versions (==)
   - Ratio: 90%+ pinned = pass
   
3. **python_version_specified** (5 pts)
   - Detects: .python-version, runtime.txt, Dockerfile

### Randomness Checks
1. **seed_detection** (10 pts)
   - Patterns: `random.seed()`, `np.random.seed()`, `torch.manual_seed()`
   
2. **seed_documented** (5 pts)
   - Finds: Documentation of seed values
   
3. **deterministic_flags** (5 pts)
   - Detects: Framework-specific determinism configs

### Data Checks
1. **data_availability** (8 pts)
   - Patterns: DOI links, Zenodo, Figshare references
   
2. **data_scripts** (7 pts)
   - Files: download_data.py, preprocess.py
   
3. **sample_data** (5 pts)
   - Directories: data/, examples/, sample/

### Documentation Checks
1. **readme_exists** (5 pts)
2. **installation_instructions** (5 pts)
3. **usage_examples** (5 pts)
4. **expected_output** (5 pts)

### Testing Checks
1. **tests_exist** (8 pts)
   - Patterns: test_*.py, tests/ directory
   
2. **ci_configured** (5 pts)
   - Files: .github/workflows/, .gitlab-ci.yml
   
3. **test_coverage** (2 pts)
   - Config: pytest-cov, coverage tools

---

## Badge System

### Badge URL Format
```
https://reproducibility-validator.com/api/badge/{repo_id}
```

### Badge Embed Code
**Markdown**:
```markdown
[![Reproducibility](https://reproducibility-validator.com/api/badge/base64_repo_url)](https://reproducibility-validator.com)
```

**HTML**:
```html
<img src="https://reproducibility-validator.com/api/badge/base64_repo_url" alt="Reproducibility Score">
```

### SVG Template
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="180" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  
  <rect rx="3" width="180" height="20" fill="#555"/>
  <rect rx="3" x="120" width="60" height="20" fill="{COLOR}"/>
  
  <text x="60" y="14" fill="#fff" font-family="DejaVu Sans,Verdana,sans-serif" font-size="11">
    reproducibility
  </text>
  <text x="150" y="14" fill="#fff" font-family="DejaVu Sans,Verdana,sans-serif" font-size="11">
    {SCORE}/100
  </text>
</svg>
```

---

## Ad Strategy

### Placement Zones
1. **Header banner** (728x90 leaderboard)
2. **Sidebar** (300x250 medium rectangle)
3. **Footer** (728x90 leaderboard)
4. **In-results** (responsive native ad)

### Ad Networks
**Primary**: Google AdSense
- Easy integration
- Auto-optimized placements
- Revenue share: ~68% to publisher

**Alternative**: Carbon Ads
- Developer-focused
- Less intrusive
- Fixed CPM, higher quality

### Revenue Projection
- **Traffic**: 1,000 analyses/day
- **Pageviews**: ~3,000/day (avg 3 pages per analysis)
- **CPM**: $2-5 (conservative)
- **Monthly revenue**: $180-450

**Costs**:
- Cloudflare Pages: Free
- Cloudflare Workers: $5/month (paid tier)
- KV storage: ~$1/month
- **Net profit**: $174-444/month at 1k daily analyses

---

## Deployment

### Cloudflare Pages (Frontend)
```bash
cd web/
npx wrangler pages publish .
```

### Cloudflare Workers (API)
```bash
cd api/
npx wrangler publish
```

### KV Namespace
```bash
npx wrangler kv:namespace create "ANALYSIS_RESULTS"
```

### Environment Variables
```bash
# Worker secrets
GITHUB_TOKEN=ghp_xxx  # For higher rate limits
KV_NAMESPACE_ID=xxx
```

---

## Scaling Considerations

### Current Limits (Free/Cheap Tier)
- Cloudflare Workers: 100,000 requests/day (free)
- KV storage: 1GB (free)
- Analysis timeout: 30 seconds
- Max repo size: 100MB

### When to Scale
At **10,000 analyses/day**:
1. Upgrade Cloudflare Workers ($5/mo → $25/mo)
2. Add caching layer (CDN + Redis)
3. Consider dedicated Python workers (AWS Lambda)

### Cost Optimization
- Cache popular repos (e.g., sklearn, pytorch)
- Incremental analysis (only check changed files)
- Batch processing during off-peak
- Rate limit per IP (10 analyses/hour)

---

## Security

### Input Validation
- Whitelist: GitHub, GitLab, Bitbucket URLs only
- Limit: Repos under 100MB
- Sanitize: All user input

### Rate Limiting
- 10 analyses/hour per IP
- 100 analyses/day per repo
- CAPTCHA after 5 failures

### Sandboxing
- Containerized analysis (isolated)
- Read-only filesystem
- No network access during analysis
- Timeout enforcement

---

## Future Enhancements

### Phase 2
- [ ] PDF report generation (for journal submissions)
- [ ] Email notifications
- [ ] Historical tracking (score over time)
- [ ] Multi-language support (R, Julia, MATLAB)

### Phase 3
- [ ] GitHub App integration (auto-PR with fixes)
- [ ] Journal partnerships (official badge verification)
- [ ] Premium tier (private repos, priority analysis)
- [ ] API for programmatic access

### Phase 4
- [ ] Reproducibility marketplace (hire fixers)
- [ ] Conference badges (ICML, NeurIPS acceptance)
- [ ] Citation tracking (papers using badge)

---

## Maintenance

### Monitoring
- Sentry for error tracking
- Cloudflare Analytics for traffic
- Custom metrics: avg score, popular checks

### Updates
- Check definitions: Monthly review
- Scoring weights: Quarterly adjustment based on user feedback
- Pattern library: Add new frameworks/tools as they emerge

---

## Tech Stack Summary

| Component | Technology | Cost |
|-----------|-----------|------|
| Frontend | Vanilla HTML/CSS/JS | Free (Cloudflare Pages) |
| API | Cloudflare Workers | $5/mo |
| Storage | Cloudflare KV | $1/mo |
| Analysis | Python (Pyodide or Lambda) | $0-10/mo |
| Ads | Google AdSense | Revenue source |
| Domain | .com | $12/year |
| **Total** | | **~$100/year** |

**Revenue potential**: $2,000-5,000/year at moderate traffic.

---

**Design Principles:**
1. **Cheap first**: Free tier wherever possible
2. **Scalable by default**: Serverless architecture
3. **Minimal dependencies**: Vanilla > frameworks
4. **User value**: Actionable recommendations > just scores
5. **Transparent**: Open-source checks and scoring logic
