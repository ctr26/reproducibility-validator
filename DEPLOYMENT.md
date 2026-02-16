# Deployment Guide

Complete guide to deploying the Reproducibility Validator to production.

---

## Prerequisites

- [Cloudflare account](https://dash.cloudflare.com/sign-up) (free tier)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/) installed
- Domain name (optional, can use workers.dev subdomain)
- Git and Node.js 18+

---

## Step 1: Set Up Cloudflare

### 1.1 Create Account

1. Sign up at https://dash.cloudflare.com/sign-up
2. Verify email
3. (Optional) Add your domain

### 1.2 Install Wrangler

```bash
npm install -g wrangler

# Login to Cloudflare
wrangler login
```

---

## Step 2: Deploy Frontend

### 2.1 Prepare Frontend

```bash
cd ~/projects/reproducibility-validator/web/
```

No build step needed (vanilla HTML/CSS/JS).

### 2.2 Deploy to Cloudflare Pages

```bash
npx wrangler pages publish .
```

Follow prompts:
- Project name: `reproducibility-validator`
- Production branch: `main`

Your site will be live at:
`https://reproducibility-validator.pages.dev`

### 2.3 (Optional) Custom Domain

If you have a domain:

1. Go to Cloudflare Dashboard → Pages → reproducibility-validator
2. Custom domains → Set up a custom domain
3. Add: `reproducibility-validator.com`
4. Cloudflare will configure DNS automatically

---

## Step 3: Create KV Namespaces

KV stores analysis results and badges.

```bash
# Production namespace
npx wrangler kv:namespace create "ANALYSIS_RESULTS"

# Preview/staging namespace
npx wrangler kv:namespace create "ANALYSIS_RESULTS" --preview
```

Copy the namespace IDs from output:
```
✨ Success! Created KV namespace: ANALYSIS_RESULTS
ID: abc123def456
Preview ID: preview789xyz
```

---

## Step 4: Configure Worker

### 4.1 Update `wrangler.toml`

Edit `api/wrangler.toml` and replace placeholder IDs:

```toml
kv_namespaces = [
  { binding = "ANALYSIS_RESULTS", id = "abc123def456", preview_id = "preview789xyz" }
]
```

### 4.2 (Optional) Add Secrets

If using GitHub token for higher rate limits:

```bash
cd ~/projects/reproducibility-validator/api/
echo "ghp_YOUR_TOKEN_HERE" | npx wrangler secret put GITHUB_TOKEN
```

---

## Step 5: Deploy API Worker

### 5.1 Test Locally First

```bash
cd ~/projects/reproducibility-validator/api/
npx wrangler dev
```

Visit http://localhost:8787/api/health to verify.

### 5.2 Deploy to Production

```bash
npx wrangler publish
```

Your API will be live at:
`https://reproducibility-validator-api.YOUR_SUBDOMAIN.workers.dev`

---

## Step 6: Deploy Analysis Engine

You have 3 options for running the Python analysis:

### Option A: Cloudflare Workers (Pyodide)

**Pros**: All on Cloudflare, lowest latency  
**Cons**: Limited Python stdlib, slower startup

```bash
# Install Pyodide integration
npm install @cloudflare/pyodide-worker

# Update worker to use Pyodide
# (See docs/PYODIDE_INTEGRATION.md)
```

### Option B: AWS Lambda (Recommended)

**Pros**: Full Python, cheap, fast  
**Cons**: Requires AWS account

```bash
# Build Docker image
cd ~/projects/reproducibility-validator/
docker build -t repro-validator .

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker tag repro-validator:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/repro-validator:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/repro-validator:latest

# Create Lambda function
aws lambda create-function \
  --function-name repro-validator \
  --package-type Image \
  --code ImageUri=YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/repro-validator:latest \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
  --timeout 30 \
  --memory-size 512

# Get function URL
aws lambda create-function-url-config \
  --function-name repro-validator \
  --auth-type NONE \
  --cors AllowOrigins='*'
```

Update `api/worker.js` to call Lambda:

```javascript
const ANALYSIS_ENDPOINT = 'https://YOUR_LAMBDA_URL.lambda-url.us-east-1.on.aws/analyze';
```

### Option C: Google Cloud Run

**Pros**: Auto-scaling, free tier  
**Cons**: Requires Google Cloud account

```bash
# Build and deploy
gcloud run deploy repro-validator \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 30s

# Get service URL
gcloud run services describe repro-validator --region us-central1 --format 'value(status.url)'
```

---

## Step 7: Connect Frontend to API

Update `web/index.html` to point to your worker:

```javascript
// Change this line in index.html:
const response = await fetch('https://reproducibility-validator-api.YOUR_SUBDOMAIN.workers.dev/api/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ repo_url: repoUrl })
});
```

Redeploy frontend:

```bash
cd ~/projects/reproducibility-validator/web/
npx wrangler pages publish .
```

---

## Step 8: Set Up Advertising

### Google AdSense

1. Sign up at https://www.google.com/adsense
2. Add site: `reproducibility-validator.com`
3. Wait for approval (1-2 weeks)
4. Get ad code
5. Add to `web/index.html`:

```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-YOUR_ID"
     crossorigin="anonymous"></script>

<!-- Ad placement -->
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-YOUR_ID"
     data-ad-slot="YOUR_SLOT_ID"
     data-ad-format="auto"></ins>
<script>
     (adsbygoogle = window.adsbygoogle || []).push({});
</script>
```

### Carbon Ads (Alternative)

1. Apply at https://www.carbonads.net/
2. Wait for approval
3. Add code snippet to `web/index.html`

---

## Step 9: Monitoring & Analytics

### Cloudflare Analytics

Built-in, no setup needed:
- Dashboard → Workers → reproducibility-validator-api → Metrics

### Sentry (Error Tracking)

```bash
npm install @sentry/browser

# Add to web/index.html
<script src="https://browser.sentry-cdn.com/YOUR_DSN.min.js"></script>
```

### Custom Metrics

Log to Cloudflare Workers Analytics Engine:

```javascript
// In worker.js
export default {
  async fetch(request, env, ctx) {
    const start = Date.now();
    
    // ... handle request
    
    const duration = Date.now() - start;
    ctx.waitUntil(
      env.ANALYTICS.writeDataPoint({
        blobs: [url.pathname],
        doubles: [duration],
        indexes: ['analysis_time']
      })
    );
  }
}
```

---

## Step 10: Testing Production

### Health Check

```bash
curl https://reproducibility-validator-api.YOUR_SUBDOMAIN.workers.dev/health
```

Expected:
```json
{"status":"healthy","service":"reproducibility-validator-api"}
```

### Analysis Test

```bash
curl -X POST https://reproducibility-validator-api.YOUR_SUBDOMAIN.workers.dev/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"repo_url":"https://github.com/numpy/numpy"}'
```

Expected:
```json
{
  "analysis_id": "abc123",
  "status": "pending",
  "poll_url": "/api/results/abc123"
}
```

### Badge Test

Visit:
`https://reproducibility-validator.pages.dev/api/badge/test`

Should show an SVG badge.

---

## Cost Breakdown

### Cloudflare (Monthly)

| Service | Free Tier | Paid |
|---------|-----------|------|
| Pages | 500 builds/mo | $20/mo |
| Workers | 100k req/day | $5/mo |
| KV | 1GB + 100k reads | $0.50/GB |
| **Total** | **$0** | **$5-25/mo** |

### AWS Lambda (Optional)

| Service | Free Tier | After Free |
|---------|-----------|------------|
| Invocations | 1M/mo | $0.20/1M |
| Duration | 400k GB-seconds/mo | $0.0000166667/GB-s |
| **Total** | **$0** | **~$2-10/mo** |

**Total monthly cost: $5-35** for 10k-100k analyses/month

---

## Scaling

### 1,000 analyses/day
- **Cost**: $5/mo (Cloudflare Workers paid tier)
- **Revenue**: $200-500/mo (ads)
- **Net**: ~$450/mo

### 10,000 analyses/day
- **Cost**: $25/mo (Cloudflare + Lambda)
- **Revenue**: $2,000-5,000/mo
- **Net**: ~$4,800/mo

### 100,000 analyses/day
- **Cost**: $100/mo (Workers + Lambda + KV)
- **Revenue**: $20,000-50,000/mo
- **Net**: ~$49,000/mo

---

## Maintenance

### Weekly
- [ ] Check error rates (Sentry)
- [ ] Monitor ad revenue
- [ ] Review slow queries

### Monthly
- [ ] Update check definitions (new frameworks)
- [ ] Analyze user feedback
- [ ] Optimize scoring weights

### Quarterly
- [ ] Major feature releases
- [ ] Security audits
- [ ] Performance optimization

---

## Troubleshooting

### Worker not responding

```bash
# Check logs
npx wrangler tail

# Redeploy
npx wrangler publish
```

### KV storage issues

```bash
# List keys
npx wrangler kv:key list --namespace-id=YOUR_ID

# Get value
npx wrangler kv:key get "analysis:test" --namespace-id=YOUR_ID
```

### Analysis timeout

Increase timeout in `wrangler.toml`:

```toml
[env.production]
# Max is 30 seconds on paid plan
limits = { cpu_ms = 30000 }
```

---

## Security Checklist

- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] CORS configured correctly
- [ ] Secrets stored in Wrangler (not code)
- [ ] KV expiration set (30 days)
- [ ] Analysis runs in sandboxed container
- [ ] No credentials in repos being analyzed

---

## Next Steps

1. Set up custom domain
2. Configure Google AdSense
3. Add analytics
4. Monitor first week of traffic
5. Collect user feedback
6. Iterate on checks

---

## Support

- Cloudflare Docs: https://developers.cloudflare.com/workers/
- GitHub Issues: https://github.com/craggles17/reproducibility-validator/issues
- Email: support@reproducibility-validator.com
