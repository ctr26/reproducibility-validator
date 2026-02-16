"""
Reproducibility Scoring Algorithm

Calculates a 0-100 score based on weighted checks across 5 categories:
- Environment (25%): Dependency management
- Randomness (20%): Seed control and determinism
- Data (20%): Data availability and accessibility
- Documentation (20%): Quality and completeness
- Testing (15%): Test coverage and CI/CD

Each category contains specific checks with point values.
"""

import json
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class CheckResult:
    """Result of a single reproducibility check."""
    check_id: str
    passed: bool
    points_earned: int
    points_possible: int
    category: str
    message: str


class ReproducibilityScorer:
    """Calculate reproducibility scores and generate recommendations."""
    
    def __init__(self, checks_config_path: str = "data/checks.json"):
        """Load check definitions from JSON config."""
        with open(checks_config_path, 'r') as f:
            self.config = json.load(f)
        
        self.checks = self.config['checks']
        self.thresholds = self.config['thresholds']
        self.recommendations = self.config['recommendations']
    
    def calculate_score(self, check_results: List[CheckResult]) -> Dict:
        """
        Calculate overall score and category breakdowns.
        
        Args:
            check_results: List of CheckResult objects
            
        Returns:
            Dict with overall score, category scores, and rating
        """
        category_scores = {}
        
        for category_name, category_config in self.checks.items():
            weight = category_config['weight']
            
            # Calculate points for this category
            earned = sum(r.points_earned for r in check_results if r.category == category_name)
            possible = sum(item['points'] for item in category_config['items'])
            
            # Normalize to 0-100 and apply weight
            if possible > 0:
                normalized = (earned / possible) * 100
                weighted_score = (normalized * weight) / 100
            else:
                weighted_score = 0
            
            category_scores[category_name] = {
                'score': round(normalized, 1) if possible > 0 else 0,
                'weight': weight,
                'weighted_contribution': round(weighted_score, 1),
                'points_earned': earned,
                'points_possible': possible
            }
        
        # Overall score is sum of weighted contributions
        overall_score = sum(cat['weighted_contribution'] for cat in category_scores.values())
        overall_score = round(overall_score, 1)
        
        # Determine rating
        rating = self._get_rating(overall_score)
        
        return {
            'overall_score': overall_score,
            'rating': rating,
            'category_scores': category_scores,
            'max_possible_score': 100
        }
    
    def _get_rating(self, score: float) -> str:
        """Convert numeric score to rating label."""
        if score >= self.thresholds['excellent']:
            return 'excellent'
        elif score >= self.thresholds['good']:
            return 'good'
        elif score >= self.thresholds['fair']:
            return 'fair'
        elif score >= self.thresholds['poor']:
            return 'poor'
        else:
            return 'critical'
    
    def generate_recommendations(self, check_results: List[CheckResult]) -> List[Dict]:
        """
        Generate actionable recommendations for failed checks.
        
        Args:
            check_results: List of CheckResult objects
            
        Returns:
            List of recommendations sorted by priority
        """
        recommendations = []
        
        for result in check_results:
            if not result.passed:
                rec_config = self.recommendations.get(result.check_id, {})
                
                recommendations.append({
                    'check_id': result.check_id,
                    'category': result.category,
                    'priority': self._get_priority(result),
                    'title': result.message,
                    'fix': rec_config.get('fix', 'No specific recommendation available'),
                    'example': rec_config.get('example', ''),
                    'points_impact': result.points_possible
                })
        
        # Sort by priority (critical first) then by points impact
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(
            key=lambda x: (priority_order.get(x['priority'], 99), -x['points_impact'])
        )
        
        return recommendations
    
    def _get_priority(self, result: CheckResult) -> str:
        """Determine priority level for a failed check."""
        # Find the check config
        for category_config in self.checks.values():
            for item in category_config['items']:
                if item['id'] == result.check_id:
                    # Explicit severity if defined
                    if 'severity' in item:
                        return item['severity']
                    
                    # Otherwise base on points
                    if result.points_possible >= 10:
                        return 'critical'
                    elif result.points_possible >= 7:
                        return 'high'
                    elif result.points_possible >= 5:
                        return 'medium'
                    else:
                        return 'low'
        
        return 'medium'
    
    def format_badge_data(self, score: float) -> Dict:
        """
        Format score data for badge generation.
        
        Args:
            score: Overall reproducibility score
            
        Returns:
            Dict with color, label, and message for badge
        """
        rating = self._get_rating(score)
        
        color_map = {
            'excellent': '#44cc11',  # Green
            'good': '#97ca00',       # Light green
            'fair': '#dfb317',       # Yellow
            'poor': '#fe7d37',       # Orange
            'critical': '#e05d44'    # Red
        }
        
        label_map = {
            'excellent': 'Excellent',
            'good': 'Good',
            'fair': 'Fair',
            'poor': 'Needs Work',
            'critical': 'Critical Issues'
        }
        
        return {
            'label': 'reproducibility',
            'message': f"{score:.0f}/100",
            'status': label_map[rating],
            'color': color_map[rating],
            'score': score
        }


def example_usage():
    """Example of how to use the scorer."""
    
    # Simulate some check results
    results = [
        CheckResult('env_file_exists', True, 10, 10, 'environment', 'Environment file exists'),
        CheckResult('dependencies_pinned', False, 0, 10, 'environment', 'Dependencies are pinned'),
        CheckResult('python_version_specified', True, 5, 5, 'environment', 'Python version specified'),
        CheckResult('seed_detection', True, 10, 10, 'randomness', 'Random seed set'),
        CheckResult('seed_documented', False, 0, 5, 'randomness', 'Seed value documented'),
        CheckResult('data_availability', True, 8, 8, 'data', 'Data availability statement'),
        CheckResult('readme_exists', True, 5, 5, 'documentation', 'README exists'),
        CheckResult('tests_exist', False, 0, 8, 'testing', 'Tests exist'),
    ]
    
    scorer = ReproducibilityScorer()
    
    # Calculate score
    score_data = scorer.calculate_score(results)
    print(f"Overall Score: {score_data['overall_score']}/100 ({score_data['rating'].upper()})")
    print("\nCategory Breakdown:")
    for cat, data in score_data['category_scores'].items():
        print(f"  {cat.title()}: {data['score']:.1f}/100 (weight: {data['weight']}%)")
    
    # Generate recommendations
    print("\nRecommendations:")
    recommendations = scorer.generate_recommendations(results)
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"{i}. [{rec['priority'].upper()}] {rec['title']}")
        print(f"   Fix: {rec['fix']}")
        if rec['example']:
            print(f"   Example: {rec['example']}")
        print()
    
    # Badge data
    badge_data = scorer.format_badge_data(score_data['overall_score'])
    print(f"Badge: {badge_data['label']}: {badge_data['message']} - {badge_data['status']}")


if __name__ == '__main__':
    example_usage()
