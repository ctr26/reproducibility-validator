"""
SVG Badge Generator

Creates dynamic badges for reproducibility scores.
Designed to work in Cloudflare Workers environment.
"""

from typing import Dict


def generate_badge_svg(score: float, rating: str) -> str:
    """
    Generate SVG badge for reproducibility score.
    
    Args:
        score: Reproducibility score (0-100)
        rating: Rating label (excellent, good, fair, poor, critical)
        
    Returns:
        SVG markup as string
    """
    # Color mapping
    color_map = {
        'excellent': '#44cc11',
        'good': '#97ca00',
        'fair': '#dfb317',
        'poor': '#fe7d37',
        'critical': '#e05d44'
    }
    
    color = color_map.get(rating, '#9f9f9f')
    score_text = f"{int(score)}/100"
    
    # Calculate text widths (approximate)
    label_width = 100
    score_width = 50
    total_width = label_width + score_width
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{total_width}" height="20" role="img" aria-label="reproducibility: {score_text}">
    <title>reproducibility: {score_text}</title>
    <linearGradient id="s" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <clipPath id="r">
        <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
    </clipPath>
    <g clip-path="url(#r)">
        <rect width="{label_width}" height="20" fill="#555"/>
        <rect x="{label_width}" width="{score_width}" height="20" fill="{color}"/>
        <rect width="{total_width}" height="20" fill="url(#s)"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
        <text aria-hidden="true" x="{label_width/2 * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(label_width-10)*10}">reproducibility</text>
        <text x="{label_width/2 * 10}" y="140" transform="scale(.1)" fill="#fff" textLength="{(label_width-10)*10}">reproducibility</text>
        <text aria-hidden="true" x="{(label_width + score_width/2) * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(score_width-10)*10}">{score_text}</text>
        <text x="{(label_width + score_width/2) * 10}" y="140" transform="scale(.1)" fill="#fff" textLength="{(score_width-10)*10}">{score_text}</text>
    </g>
</svg>'''
    
    return svg


def generate_detailed_badge_svg(score_data: Dict) -> str:
    """
    Generate a more detailed multi-line badge with category breakdown.
    
    Args:
        score_data: Dict with overall score and category scores
        
    Returns:
        SVG markup as string
    """
    overall = score_data['overall_score']
    rating = score_data['rating']
    categories = score_data['category_scores']
    
    color_map = {
        'excellent': '#44cc11',
        'good': '#97ca00',
        'fair': '#dfb317',
        'poor': '#fe7d37',
        'critical': '#e05d44'
    }
    
    main_color = color_map.get(rating, '#9f9f9f')
    
    # Build category lines
    y_offset = 25
    height = 20 + (len(categories) * 18)
    width = 200
    
    category_rects = []
    category_texts = []
    
    for i, (cat_name, cat_data) in enumerate(categories.items()):
        cat_score = cat_data['score']
        cat_rating = get_rating_from_score(cat_score)
        cat_color = color_map.get(cat_rating, '#9f9f9f')
        
        y = y_offset + (i * 18)
        
        # Background rect
        category_rects.append(
            f'<rect x="5" y="{y}" width="190" height="14" rx="2" fill="#f5f5f5"/>'
        )
        
        # Score bar (proportional width)
        bar_width = int((cat_score / 100) * 120)
        category_rects.append(
            f'<rect x="70" y="{y+1}" width="{bar_width}" height="12" rx="2" fill="{cat_color}"/>'
        )
        
        # Text
        category_texts.append(
            f'<text x="8" y="{y+10}" font-family="Verdana,sans-serif" font-size="9" fill="#333">{cat_name[:3].upper()}</text>'
        )
        category_texts.append(
            f'<text x="193" y="{y+10}" font-family="Verdana,sans-serif" font-size="9" fill="#333" text-anchor="end">{int(cat_score)}</text>'
        )
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">
    <title>Reproducibility Score: {int(overall)}/100</title>
    
    <!-- Header -->
    <rect width="{width}" height="20" rx="3" fill="{main_color}"/>
    <text x="{width/2}" y="14" font-family="Verdana,sans-serif" font-size="11" fill="#fff" text-anchor="middle" font-weight="bold">
        Reproducibility: {int(overall)}/100
    </text>
    
    <!-- Category breakdown -->
    {chr(10).join(category_rects)}
    {chr(10).join(category_texts)}
</svg>'''
    
    return svg


def get_rating_from_score(score: float) -> str:
    """Convert numeric score to rating label."""
    if score >= 90:
        return 'excellent'
    elif score >= 75:
        return 'good'
    elif score >= 60:
        return 'fair'
    elif score >= 40:
        return 'poor'
    else:
        return 'critical'


# Cloudflare Worker endpoint handler
def handle_badge_request(repo_id: str, detailed: bool = False) -> tuple[str, Dict]:
    """
    Handle badge request in Cloudflare Worker.
    
    Args:
        repo_id: Base64-encoded repository URL or analysis ID
        detailed: Whether to generate detailed badge
        
    Returns:
        Tuple of (svg_content, headers)
    """
    # In production, fetch from KV storage
    # For now, return example
    
    # Mock data (replace with KV lookup)
    score_data = {
        'overall_score': 85.0,
        'rating': 'good',
        'category_scores': {
            'environment': {'score': 90},
            'randomness': {'score': 80},
            'data': {'score': 85},
            'documentation': {'score': 90},
            'testing': {'score': 70}
        }
    }
    
    if detailed:
        svg = generate_detailed_badge_svg(score_data)
    else:
        svg = generate_badge_svg(score_data['overall_score'], score_data['rating'])
    
    headers = {
        'Content-Type': 'image/svg+xml',
        'Cache-Control': 'max-age=3600',  # Cache for 1 hour
        'Access-Control-Allow-Origin': '*'
    }
    
    return svg, headers


if __name__ == '__main__':
    # Test badge generation
    print("Simple Badge:")
    print(generate_badge_svg(85, 'good'))
    
    print("\n\nDetailed Badge:")
    score_data = {
        'overall_score': 85.0,
        'rating': 'good',
        'category_scores': {
            'env': {'score': 90},
            'random': {'score': 80},
            'data': {'score': 85},
            'docs': {'score': 90},
            'test': {'score': 70}
        }
    }
    print(generate_detailed_badge_svg(score_data))
