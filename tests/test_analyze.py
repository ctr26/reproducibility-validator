"""
Unit tests for analysis engine.
Run with: pytest tests/
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from analyze import RepositoryAnalyzer


def create_test_repo(tmpdir, files_to_create):
    """Helper to create a test repository structure."""
    repo_path = Path(tmpdir) / 'test_repo'
    repo_path.mkdir()
    
    # Initialize git repo
    os.system(f'cd {repo_path} && git init')
    
    # Create files
    for filename, content in files_to_create.items():
        file_path = repo_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    
    # Commit files
    os.system(f'cd {repo_path} && git add . && git commit -m "Initial commit"')
    
    return str(repo_path)


def test_environment_detection():
    """Test detection of environment files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = {
            'requirements.txt': 'numpy==1.24.3\npandas==2.0.0\n',
            'README.md': '# Test Project\n'
        }
        
        repo_path = create_test_repo(tmpdir, files)
        analyzer = RepositoryAnalyzer('data/checks.json')
        
        results, findings = analyzer._check_environment(repo_path)
        
        # Should find requirements.txt
        assert 'requirements.txt' in findings['found_env_files']
        assert any(r.check_id == 'env_file_exists' and r.passed for r in results)


def test_dependency_pinning():
    """Test dependency pinning detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = {
            'requirements.txt': 'numpy==1.24.3\npandas==2.0.0\nscipy==1.10.1\n',
        }
        
        repo_path = create_test_repo(tmpdir, files)
        analyzer = RepositoryAnalyzer('data/checks.json')
        
        results, findings = analyzer._check_environment(repo_path)
        
        # All dependencies are pinned
        assert findings['pinned_dependencies'] == 3
        assert findings['total_dependencies'] == 3


def test_unpinned_dependencies():
    """Test detection of unpinned dependencies."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = {
            'requirements.txt': 'numpy\npandas>=2.0.0\nscipy==1.10.1\n',
        }
        
        repo_path = create_test_repo(tmpdir, files)
        analyzer = RepositoryAnalyzer('data/checks.json')
        
        results, findings = analyzer._check_environment(repo_path)
        
        # Only 1 out of 3 is pinned
        assert findings['pinned_dependencies'] == 1
        assert findings['total_dependencies'] == 3


def test_seed_detection():
    """Test random seed detection in code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = {
            'main.py': '''
import random
import numpy as np

random.seed(42)
np.random.seed(42)

# Rest of code...
''',
            'README.md': '# Test Project\n'
        }
        
        repo_path = create_test_repo(tmpdir, files)
        analyzer = RepositoryAnalyzer('data/checks.json')
        
        results, findings = analyzer._check_randomness(repo_path)
        
        # Should find both random.seed and np.random.seed
        assert len(findings['seed_matches']) >= 2
        assert any(r.check_id == 'seed_detection' and r.passed for r in results)


def test_documentation_checks():
    """Test documentation quality checks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = {
            'README.md': '''
# Test Project

## Installation
pip install -r requirements.txt

## Usage
python main.py

Expected output: Accuracy of 0.95
'''
        }
        
        repo_path = create_test_repo(tmpdir, files)
        analyzer = RepositoryAnalyzer('data/checks.json')
        
        results, findings = analyzer._check_documentation(repo_path)
        
        # Should pass multiple documentation checks
        passed_checks = [r for r in results if r.passed]
        assert len(passed_checks) >= 3  # README, installation, usage, expected output


def test_testing_detection():
    """Test detection of test files and CI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = {
            'tests/test_main.py': '''
import pytest

def test_example():
    assert True
''',
            '.github/workflows/test.yml': '''
name: Tests
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pytest
'''
        }
        
        repo_path = create_test_repo(tmpdir, files)
        analyzer = RepositoryAnalyzer('data/checks.json')
        
        results, findings = analyzer._check_testing(repo_path)
        
        # Should find test files and CI config
        assert len(findings['test_files']) > 0 or len(findings['test_directories']) > 0
        assert len(findings['ci_files']) > 0


def test_full_analysis():
    """Test full repository analysis pipeline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = {
            'requirements.txt': 'numpy==1.24.3\n',
            'README.md': '''
# Test Project

## Installation
pip install -r requirements.txt

## Usage
python main.py
''',
            'main.py': '''
import random
random.seed(42)
print("Hello")
''',
            'tests/test_main.py': 'def test_example():\n    assert True\n'
        }
        
        repo_path = create_test_repo(tmpdir, files)
        analyzer = RepositoryAnalyzer('data/checks.json')
        
        result = analyzer.analyze_repository(repo_path)
        
        # Check result structure
        assert result.score_data['overall_score'] > 0
        assert result.score_data['rating'] in ['excellent', 'good', 'fair', 'poor', 'critical']
        assert len(result.check_results) > 0
        assert 'badge_data' in result.badge_data


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
