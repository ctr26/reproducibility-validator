"""
Unit tests for scoring algorithm.
Run with: pytest tests/
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from scoring import CheckResult, ReproducibilityScorer


def test_perfect_score():
    """Test repository with all checks passing."""
    results = [
        CheckResult('env_file_exists', True, 10, 10, 'environment', 'Environment file exists'),
        CheckResult('dependencies_pinned', True, 10, 10, 'environment', 'Dependencies pinned'),
        CheckResult('python_version_specified', True, 5, 5, 'environment', 'Python version specified'),
        CheckResult('seed_detection', True, 10, 10, 'randomness', 'Random seed set'),
        CheckResult('seed_documented', True, 5, 5, 'randomness', 'Seed documented'),
        CheckResult('deterministic_flags', True, 5, 5, 'randomness', 'Deterministic flags'),
        CheckResult('data_availability', True, 8, 8, 'data', 'Data availability'),
        CheckResult('data_scripts', True, 7, 7, 'data', 'Data scripts'),
        CheckResult('sample_data', True, 5, 5, 'data', 'Sample data'),
        CheckResult('readme_exists', True, 5, 5, 'documentation', 'README exists'),
        CheckResult('installation_instructions', True, 5, 5, 'documentation', 'Installation instructions'),
        CheckResult('usage_examples', True, 5, 5, 'documentation', 'Usage examples'),
        CheckResult('expected_output', True, 5, 5, 'documentation', 'Expected output'),
        CheckResult('tests_exist', True, 8, 8, 'testing', 'Tests exist'),
        CheckResult('ci_configured', True, 5, 5, 'testing', 'CI configured'),
        CheckResult('test_coverage', True, 2, 2, 'testing', 'Test coverage'),
    ]
    
    scorer = ReproducibilityScorer('data/checks.json')
    score_data = scorer.calculate_score(results)
    
    assert score_data['overall_score'] == 100.0
    assert score_data['rating'] == 'excellent'


def test_no_checks_passing():
    """Test repository with no checks passing."""
    results = [
        CheckResult('env_file_exists', False, 0, 10, 'environment', 'Environment file exists'),
        CheckResult('dependencies_pinned', False, 0, 10, 'environment', 'Dependencies pinned'),
        CheckResult('readme_exists', False, 0, 5, 'documentation', 'README exists'),
    ]
    
    scorer = ReproducibilityScorer('data/checks.json')
    score_data = scorer.calculate_score(results)
    
    assert score_data['overall_score'] == 0.0
    assert score_data['rating'] == 'critical'


def test_partial_score():
    """Test repository with some checks passing."""
    results = [
        CheckResult('env_file_exists', True, 10, 10, 'environment', 'Environment file exists'),
        CheckResult('dependencies_pinned', False, 0, 10, 'environment', 'Dependencies pinned'),
        CheckResult('python_version_specified', True, 5, 5, 'environment', 'Python version specified'),
        CheckResult('seed_detection', True, 10, 10, 'randomness', 'Random seed set'),
        CheckResult('readme_exists', True, 5, 5, 'documentation', 'README exists'),
        CheckResult('tests_exist', False, 0, 8, 'testing', 'Tests exist'),
    ]
    
    scorer = ReproducibilityScorer('data/checks.json')
    score_data = scorer.calculate_score(results)
    
    # Should be somewhere in the middle
    assert 40 < score_data['overall_score'] < 80


def test_recommendations_generation():
    """Test recommendation generation for failed checks."""
    results = [
        CheckResult('env_file_exists', False, 0, 10, 'environment', 'Environment file exists'),
        CheckResult('dependencies_pinned', False, 0, 10, 'environment', 'Dependencies pinned'),
        CheckResult('seed_detection', False, 0, 10, 'randomness', 'Random seed set'),
    ]
    
    scorer = ReproducibilityScorer('data/checks.json')
    recommendations = scorer.generate_recommendations(results)
    
    assert len(recommendations) == 3
    assert all('fix' in rec for rec in recommendations)
    assert recommendations[0]['priority'] in ['critical', 'high', 'medium', 'low']


def test_badge_data_generation():
    """Test badge data formatting."""
    scorer = ReproducibilityScorer('data/checks.json')
    
    # Excellent score
    badge_excellent = scorer.format_badge_data(95.0)
    assert badge_excellent['color'] == '#44cc11'
    assert badge_excellent['status'] == 'Excellent'
    
    # Good score
    badge_good = scorer.format_badge_data(80.0)
    assert badge_good['color'] == '#97ca00'
    assert badge_good['status'] == 'Good'
    
    # Fair score
    badge_fair = scorer.format_badge_data(65.0)
    assert badge_fair['color'] == '#dfb317'
    assert badge_fair['status'] == 'Fair'
    
    # Poor score
    badge_poor = scorer.format_badge_data(50.0)
    assert badge_poor['color'] == '#fe7d37'
    assert badge_poor['status'] == 'Needs Work'
    
    # Critical score
    badge_critical = scorer.format_badge_data(30.0)
    assert badge_critical['color'] == '#e05d44'
    assert badge_critical['status'] == 'Critical Issues'


def test_category_weights_sum_to_100():
    """Ensure category weights add up to 100%."""
    scorer = ReproducibilityScorer('data/checks.json')
    total_weight = sum(cat['weight'] for cat in scorer.checks.values())
    assert total_weight == 100


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
