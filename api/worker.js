/**
 * Cloudflare Worker - API Endpoints
 * 
 * Handles:
 * - POST /api/analyze - Queue analysis job
 * - GET /api/badge/{id} - Serve SVG badge
 * - GET /api/results/{id} - Fetch analysis results
 * - GET /api/verify/{id} - Badge verification
 */

// KV namespace binding (configured in wrangler.toml)
// ANALYSIS_RESULTS

/**
 * Main request handler
 */
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  const path = url.pathname
  
  // CORS headers
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  }
  
  // Handle preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders })
  }
  
  try {
    // Route requests
    if (path === '/api/analyze' && request.method === 'POST') {
      return await handleAnalyze(request, corsHeaders)
    }
    
    if (path.startsWith('/api/badge/')) {
      return await handleBadge(path, corsHeaders)
    }
    
    if (path.startsWith('/api/results/')) {
      return await handleResults(path, corsHeaders)
    }
    
    if (path.startsWith('/api/verify/')) {
      return await handleVerify(path, corsHeaders)
    }
    
    return new Response('Not Found', { status: 404, headers: corsHeaders })
    
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
}

/**
 * POST /api/analyze
 * Queue a repository analysis
 */
async function handleAnalyze(request, corsHeaders) {
  const body = await request.json()
  const repoUrl = body.repo_url
  
  // Validate URL
  if (!isValidRepoUrl(repoUrl)) {
    return new Response(JSON.stringify({ error: 'Invalid repository URL' }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
  
  // Rate limiting (simple IP-based)
  const clientIP = request.headers.get('CF-Connecting-IP')
  const rateLimitKey = `rate_limit:${clientIP}`
  const rateLimitCount = await ANALYSIS_RESULTS.get(rateLimitKey)
  
  if (rateLimitCount && parseInt(rateLimitCount) > 10) {
    return new Response(JSON.stringify({ error: 'Rate limit exceeded. Try again later.' }), {
      status: 429,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
  
  // Increment rate limit counter (expires in 1 hour)
  await ANALYSIS_RESULTS.put(rateLimitKey, (parseInt(rateLimitCount || 0) + 1).toString(), {
    expirationTtl: 3600
  })
  
  // Generate analysis ID
  const analysisId = await generateAnalysisId(repoUrl)
  
  // Check if analysis already exists (cache)
  const cached = await ANALYSIS_RESULTS.get(`analysis:${analysisId}`)
  if (cached) {
    return new Response(JSON.stringify({
      analysis_id: analysisId,
      status: 'complete',
      result: JSON.parse(cached)
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
  
  // Queue analysis job
  // In production: trigger external Python worker (AWS Lambda, etc.)
  // For now: return pending status
  await ANALYSIS_RESULTS.put(`job:${analysisId}`, JSON.stringify({
    repo_url: repoUrl,
    status: 'pending',
    created_at: new Date().toISOString()
  }), {
    expirationTtl: 86400 // 24 hours
  })
  
  // TODO: Trigger Python analysis worker
  // await triggerPythonAnalysis(repoUrl, analysisId)
  
  return new Response(JSON.stringify({
    analysis_id: analysisId,
    status: 'pending',
    poll_url: `/api/results/${analysisId}`
  }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  })
}

/**
 * GET /api/badge/{id}
 * Serve SVG badge
 */
async function handleBadge(path, corsHeaders) {
  const badgeId = path.split('/').pop()
  
  // Fetch analysis result
  const analysisData = await ANALYSIS_RESULTS.get(`analysis:${badgeId}`)
  
  if (!analysisData) {
    // Return default badge
    return new Response(generateDefaultBadge(), {
      headers: {
        ...corsHeaders,
        'Content-Type': 'image/svg+xml',
        'Cache-Control': 'max-age=300'
      }
    })
  }
  
  const result = JSON.parse(analysisData)
  const svg = generateBadgeSVG(result.score, result.rating)
  
  return new Response(svg, {
    headers: {
      ...corsHeaders,
      'Content-Type': 'image/svg+xml',
      'Cache-Control': 'max-age=3600'
    }
  })
}

/**
 * GET /api/results/{id}
 * Fetch analysis results
 */
async function handleResults(path, corsHeaders) {
  const analysisId = path.split('/').pop()
  
  // Check if analysis is complete
  const result = await ANALYSIS_RESULTS.get(`analysis:${analysisId}`)
  
  if (result) {
    return new Response(result, {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
  
  // Check if job is still pending
  const job = await ANALYSIS_RESULTS.get(`job:${analysisId}`)
  
  if (job) {
    return new Response(JSON.stringify({
      status: 'pending',
      message: 'Analysis in progress'
    }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
  
  return new Response(JSON.stringify({
    error: 'Analysis not found'
  }), {
    status: 404,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  })
}

/**
 * GET /api/verify/{id}
 * Verify badge authenticity
 */
async function handleVerify(path, corsHeaders) {
  const analysisId = path.split('/').pop()
  
  const result = await ANALYSIS_RESULTS.get(`analysis:${analysisId}`)
  
  if (!result) {
    return new Response(JSON.stringify({
      verified: false,
      message: 'Analysis not found'
    }), {
      status: 404,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
  
  const data = JSON.parse(result)
  
  return new Response(JSON.stringify({
    verified: true,
    repo_url: data.repo_url,
    score: data.score,
    rating: data.rating,
    timestamp: data.timestamp,
    commit_hash: data.commit_hash
  }), {
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  })
}

/**
 * Helper: Validate repository URL
 */
function isValidRepoUrl(url) {
  try {
    const parsed = new URL(url)
    const validHosts = ['github.com', 'gitlab.com', 'bitbucket.org']
    return validHosts.some(host => parsed.hostname.endsWith(host))
  } catch {
    return false
  }
}

/**
 * Helper: Generate analysis ID from repo URL
 */
async function generateAnalysisId(repoUrl) {
  const encoder = new TextEncoder()
  const data = encoder.encode(repoUrl)
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
  return hashHex.substring(0, 16)
}

/**
 * Helper: Generate SVG badge
 */
function generateBadgeSVG(score, rating) {
  const colorMap = {
    'excellent': '#44cc11',
    'good': '#97ca00',
    'fair': '#dfb317',
    'poor': '#fe7d37',
    'critical': '#e05d44'
  }
  
  const color = colorMap[rating] || '#9f9f9f'
  const scoreText = `${Math.round(score)}/100`
  
  return `<svg xmlns="http://www.w3.org/2000/svg" width="150" height="20">
    <linearGradient id="b" x2="0" y2="100%">
      <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
      <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
      <rect width="150" height="20" rx="3" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
      <rect width="100" height="20" fill="#555"/>
      <rect x="100" width="50" height="20" fill="${color}"/>
      <rect width="150" height="20" fill="url(#b)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="Verdana,sans-serif" font-size="11">
      <text x="50" y="14">reproducibility</text>
      <text x="125" y="14">${scoreText}</text>
    </g>
  </svg>`
}

/**
 * Helper: Default badge (no score)
 */
function generateDefaultBadge() {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="150" height="20">
    <rect width="150" height="20" rx="3" fill="#9f9f9f"/>
    <text x="75" y="14" fill="#fff" text-anchor="middle" font-family="Verdana,sans-serif" font-size="11">
      not analyzed
    </text>
  </svg>`
}
