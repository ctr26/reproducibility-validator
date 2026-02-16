# Reproducibility Validator

**Verify your research code is reproducible. Free, fast, actionable.**

A free, ad-supported tool that analyzes scientific code repositories and generates reproducibility scores with actionable recommendations.

---

## Features

- ⚡ **Fast Analysis** - Results in seconds
- 🎯 **Actionable Advice** - Specific fixes with code examples
- 🏆 **Journal-Ready Badges** - Embed verification badges in papers/repos
- 💰 **100% Free** - Ad-supported, always free for researchers
- 🔍 **Comprehensive** - Checks environment, seeds, data, docs, tests
- 📊 **Transparent** - Open-source scoring algorithm

---

## How It Works

1. **Submit** your GitHub/GitLab repository URL
2. **Analysis** checks for reproducibility signals:
   - Environment files (requirements.txt, Dockerfile, etc.)
   - Dependency version pinning
   - Random seed detection
   - Data availability
   - Documentation quality
   - Test coverage
3. **Get Results**:
   - Overall score (0-100)
   - Category breakdown
   - Prioritized recommendations
   - Embeddable badge

---

## Scoring Categories

| Category | Weight | Checks |
|----------|--------|--------|
| **Environment** | 25% | Dependency files, version pinning, Python version |
| **Randomness** | 20% | Random seeds, deterministic flags |
| **Data** | 20% | Data availability, download scripts, samples |
| **Documentation** | 20% | README, installation, usage examples |
| **Testing** | 15% | Tests, CI/CD, coverage tools |

**Total: 100 points**

---

## Badge Example

[![Reproducibility](https://img.shields.io/badge/reproducibility-85%2F100-brightgreen)](https://reproducibility-validator.com)

Embed in your README:
```markdown
[![Reproducibility](https://reproducibility-validator.com/api/badge/YOUR_REPO_ID)](https://reproducibility-validator.com)
```

---

## Deployment

### Prerequisites
- Cloudflare account (free tier)
- Node.js 18+ (for Wrangler CLI)
- Git

### 1. Deploy Frontend (Cloudflare Pages)

```bash
cd web/
npx wrangler pages publish .
```

### 2. Create KV Namespace

```bash
npx wrangler kv:namespace create "ANALYSIS_RESULTS"
npx wrangler kv:namespace create "ANALYSIS_RESULTS" --preview
```

Copy the namespace IDs to `wrangler.toml`.

### 3. Deploy API (Cloudflare Workers)

```bash
cd api/
npx wrangler publish
```

### 4. Deploy Analysis Engine (Optional)

For serverless Python analysis:

**AWS Lambda**:
```bash
docker build -t repro-validator .
# Push to ECR and deploy to Lambda
```

**Google Cloud Run**:
```bash
gcloud run deploy repro-validator \
  --source . \
  --platform managed \
  --region us-central1
```

---

## Local Development

### Run Analysis Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Analyze a repository
python api/analyze.py https://github.com/username/repo

# Test scoring
python api/scoring.py
```

### Test Frontend

```bash
cd web/
python -m http.server 8000
# Visit http://localhost:8000
```

### Test Worker Locally

```bash
cd api/
npx wrangler dev
```

---

## Configuration

All checks are defined in `data/checks.json`. You can:
- Add new checks
- Adjust point values
- Change category weights
- Add new patterns to detect

Example check:
```json
{
  "id": "seed_detection",
  "name": "Random seed set",
  "description": "Code contains random seed initialization",
  "points": 10,
  "patterns": [
    "random.seed\\(",
    "np.random.seed\\(",
    "torch.manual_seed\\("
  ]
}
```

---

## Architecture

```
┌─────────────┐
│   Browser   │ → Cloudflare Pages (static frontend)
└──────┬──────┘
       ▼
┌─────────────────────┐
│ Cloudflare Workers  │ → API endpoints, rate limiting
└──────┬──────────────┘
       ▼
┌─────────────────────┐
│  Python Container   │ → Repository analysis
│  (Lambda/Cloud Run) │
└──────┬──────────────┘
       ▼
┌─────────────────────┐
│  Cloudflare KV      │ → Results storage (30-day TTL)
└─────────────────────┘
```

---

## Cost Breakdown

| Service | Tier | Cost |
|---------|------|------|
| Cloudflare Pages | Free | $0/mo |
| Cloudflare Workers | Paid | $5/mo |
| Cloudflare KV | 1GB | ~$1/mo |
| AWS Lambda (optional) | Free tier | $0-10/mo |
| Domain | .com | $12/year |
| **Total** | | **~$100/year** |

**Revenue** (at 1,000 analyses/day): $200-500/month from ads

---

## Roadmap

### Phase 1 (MVP) ✅
- [x] Basic analysis engine
- [x] Scoring algorithm
- [x] Badge generation
- [x] Static frontend
- [x] Cloudflare Workers API

### Phase 2 (Q2 2026)
- [ ] PDF report generation
- [ ] Email notifications
- [ ] Historical tracking
- [ ] R/Julia support

### Phase 3 (Q3 2026)
- [ ] GitHub App (auto-PR with fixes)
- [ ] Journal partnerships
- [ ] Premium tier (private repos)
- [ ] Public API

---

## Contributing

We welcome contributions! Areas to help:
- Add check definitions for new frameworks
- Improve pattern detection
- Add support for other languages (R, Julia, MATLAB)
- UI/UX improvements
- Documentation

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Citation

If you use Reproducibility Validator in your research, please cite:

```bibtex
@software{reproducibility_validator,
  title = {Reproducibility Validator},
  author = {[Your Name]},
  year = {2026},
  url = {https://reproducibility-validator.com}
}
```

---

## Support

- 📧 Email: support@reproducibility-validator.com
- 💬 GitHub Issues: [Report a bug](https://github.com/craggles17/reproducibility-validator/issues)
- 🐦 Twitter: [@ReproValidator](https://twitter.com/ReproValidator)

---

**Made with ❤️ for the research community**
