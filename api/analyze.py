"""
Repository Analysis Engine

Analyzes GitHub/GitLab repositories for reproducibility signals:
- Environment files and dependency pinning
- Random seed usage in code
- Data availability indicators
- Documentation quality
- Test coverage

Designed to run in a containerized environment (Cloudflare Workers + Python).
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import tempfile
import subprocess

from scoring import CheckResult, ReproducibilityScorer


@dataclass
class AnalysisResult:
    """Complete analysis result for a repository."""
    repo_url: str
    commit_hash: str
    timestamp: str
    check_results: List[CheckResult]
    score_data: Dict
    recommendations: List[Dict]
    badge_data: Dict
    raw_findings: Dict


class RepositoryAnalyzer:
    """Analyze a repository for reproducibility signals."""
    
    def __init__(self, checks_config_path: str = "data/checks.json"):
        """Initialize analyzer with check definitions."""
        with open(checks_config_path, 'r') as f:
            self.config = json.load(f)
        
        self.checks = self.config['checks']
        self.scorer = ReproducibilityScorer(checks_config_path)
    
    def analyze_repository(self, repo_path: str) -> AnalysisResult:
        """
        Run full analysis on a repository.
        
        Args:
            repo_path: Path to cloned repository
            
        Returns:
            AnalysisResult with scores and recommendations
        """
        import datetime
        
        # Get repo metadata
        commit_hash = self._get_commit_hash(repo_path)
        timestamp = datetime.datetime.utcnow().isoformat()
        
        # Run all checks
        check_results = []
        raw_findings = {}
        
        # Environment checks
        env_results, env_findings = self._check_environment(repo_path)
        check_results.extend(env_results)
        raw_findings['environment'] = env_findings
        
        # Randomness checks
        random_results, random_findings = self._check_randomness(repo_path)
        check_results.extend(random_results)
        raw_findings['randomness'] = random_findings
        
        # Data availability checks
        data_results, data_findings = self._check_data_availability(repo_path)
        check_results.extend(data_results)
        raw_findings['data'] = data_findings
        
        # Documentation checks
        doc_results, doc_findings = self._check_documentation(repo_path)
        check_results.extend(doc_results)
        raw_findings['documentation'] = doc_findings
        
        # Testing checks
        test_results, test_findings = self._check_testing(repo_path)
        check_results.extend(test_results)
        raw_findings['testing'] = test_findings
        
        # Calculate scores
        score_data = self.scorer.calculate_score(check_results)
        recommendations = self.scorer.generate_recommendations(check_results)
        badge_data = self.scorer.format_badge_data(score_data['overall_score'])
        
        return AnalysisResult(
            repo_url=self._get_repo_url(repo_path),
            commit_hash=commit_hash,
            timestamp=timestamp,
            check_results=check_results,
            score_data=score_data,
            recommendations=recommendations,
            badge_data=badge_data,
            raw_findings=raw_findings
        )
    
    def _check_environment(self, repo_path: str) -> tuple[List[CheckResult], Dict]:
        """Check for environment files and dependency pinning."""
        results = []
        findings = {}
        
        # Check for environment files
        env_files = self.checks['environment']['items'][0]['files']
        found_files = self._find_files(repo_path, env_files)
        findings['found_env_files'] = found_files
        
        env_file_check = self.checks['environment']['items'][0]
        results.append(CheckResult(
            check_id=env_file_check['id'],
            passed=len(found_files) > 0,
            points_earned=env_file_check['points'] if found_files else 0,
            points_possible=env_file_check['points'],
            category='environment',
            message=env_file_check['name']
        ))
        
        # Check dependency pinning
        pinned, total_deps = self._check_dependency_pinning(repo_path, found_files)
        findings['pinned_dependencies'] = pinned
        findings['total_dependencies'] = total_deps
        
        pin_check = self.checks['environment']['items'][1]
        pinning_ratio = pinned / total_deps if total_deps > 0 else 0
        passed = pinning_ratio >= 0.9  # 90% pinned = pass
        
        results.append(CheckResult(
            check_id=pin_check['id'],
            passed=passed,
            points_earned=int(pin_check['points'] * pinning_ratio),
            points_possible=pin_check['points'],
            category='environment',
            message=pin_check['name']
        ))
        
        # Check Python version
        py_version_files = self.checks['environment']['items'][2]['files']
        found_py_files = self._find_files(repo_path, py_version_files)
        findings['python_version_files'] = found_py_files
        
        py_check = self.checks['environment']['items'][2]
        results.append(CheckResult(
            check_id=py_check['id'],
            passed=len(found_py_files) > 0,
            points_earned=py_check['points'] if found_py_files else 0,
            points_possible=py_check['points'],
            category='environment',
            message=py_check['name']
        ))
        
        return results, findings
    
    def _check_randomness(self, repo_path: str) -> tuple[List[CheckResult], Dict]:
        """Check for random seed control and determinism."""
        results = []
        findings = {}
        
        # Scan Python files for seed patterns
        seed_patterns = self.checks['randomness']['items'][0]['patterns']
        seed_matches = self._search_code_patterns(repo_path, seed_patterns, ['*.py'])
        findings['seed_matches'] = seed_matches
        
        seed_check = self.checks['randomness']['items'][0]
        results.append(CheckResult(
            check_id=seed_check['id'],
            passed=len(seed_matches) > 0,
            points_earned=seed_check['points'] if seed_matches else 0,
            points_possible=seed_check['points'],
            category='randomness',
            message=seed_check['name']
        ))
        
        # Check for seed documentation
        doc_patterns = [r'seed.*=.*\d+', r'random.*seed', r'reproducib']
        doc_matches = self._search_code_patterns(
            repo_path, doc_patterns, ['README.md', '*.md', '*.py']
        )
        findings['seed_documentation'] = doc_matches
        
        doc_check = self.checks['randomness']['items'][1]
        results.append(CheckResult(
            check_id=doc_check['id'],
            passed=len(doc_matches) > 0,
            points_earned=doc_check['points'] if doc_matches else 0,
            points_possible=doc_check['points'],
            category='randomness',
            message=doc_check['name']
        ))
        
        # Check for deterministic flags
        det_patterns = self.checks['randomness']['items'][2]['patterns']
        det_matches = self._search_code_patterns(repo_path, det_patterns, ['*.py'])
        findings['deterministic_flags'] = det_matches
        
        det_check = self.checks['randomness']['items'][2]
        results.append(CheckResult(
            check_id=det_check['id'],
            passed=len(det_matches) > 0,
            points_earned=det_check['points'] if det_matches else 0,
            points_possible=det_check['points'],
            category='randomness',
            message=det_check['name']
        ))
        
        return results, findings
    
    def _check_data_availability(self, repo_path: str) -> tuple[List[CheckResult], Dict]:
        """Check for data availability and access."""
        results = []
        findings = {}
        
        # Check for data availability statements
        data_patterns = self.checks['data']['items'][0]['patterns']
        data_matches = self._search_code_patterns(
            repo_path, data_patterns, ['README.md', '*.md', 'docs/*.md']
        )
        findings['data_availability_statements'] = data_matches
        
        avail_check = self.checks['data']['items'][0]
        results.append(CheckResult(
            check_id=avail_check['id'],
            passed=len(data_matches) > 0,
            points_earned=avail_check['points'] if data_matches else 0,
            points_possible=avail_check['points'],
            category='data',
            message=avail_check['name']
        ))
        
        # Check for data scripts
        data_script_files = self.checks['data']['items'][1]['files']
        found_scripts = self._find_files(repo_path, data_script_files)
        findings['data_scripts'] = found_scripts
        
        script_check = self.checks['data']['items'][1]
        results.append(CheckResult(
            check_id=script_check['id'],
            passed=len(found_scripts) > 0,
            points_earned=script_check['points'] if found_scripts else 0,
            points_possible=script_check['points'],
            category='data',
            message=script_check['name']
        ))
        
        # Check for sample data
        data_dirs = self.checks['data']['items'][2]['directories']
        found_dirs = self._find_directories(repo_path, data_dirs)
        findings['data_directories'] = found_dirs
        
        sample_check = self.checks['data']['items'][2]
        results.append(CheckResult(
            check_id=sample_check['id'],
            passed=len(found_dirs) > 0,
            points_earned=sample_check['points'] if found_dirs else 0,
            points_possible=sample_check['points'],
            category='data',
            message=sample_check['name']
        ))
        
        return results, findings
    
    def _check_documentation(self, repo_path: str) -> tuple[List[CheckResult], Dict]:
        """Check documentation quality."""
        results = []
        findings = {}
        
        # Check for README
        readme_files = self.checks['documentation']['items'][0]['files']
        found_readme = self._find_files(repo_path, readme_files)
        findings['readme_files'] = found_readme
        
        readme_check = self.checks['documentation']['items'][0]
        results.append(CheckResult(
            check_id=readme_check['id'],
            passed=len(found_readme) > 0,
            points_earned=readme_check['points'] if found_readme else 0,
            points_possible=readme_check['points'],
            category='documentation',
            message=readme_check['name']
        ))
        
        # Check for installation instructions
        install_patterns = self.checks['documentation']['items'][1]['patterns']
        install_matches = self._search_code_patterns(
            repo_path, install_patterns, ['README.md', '*.md']
        )
        findings['installation_instructions'] = install_matches
        
        install_check = self.checks['documentation']['items'][1]
        results.append(CheckResult(
            check_id=install_check['id'],
            passed=len(install_matches) > 0,
            points_earned=install_check['points'] if install_matches else 0,
            points_possible=install_check['points'],
            category='documentation',
            message=install_check['name']
        ))
        
        # Check for usage examples
        usage_patterns = self.checks['documentation']['items'][2]['patterns']
        usage_matches = self._search_code_patterns(
            repo_path, usage_patterns, ['README.md', '*.md']
        )
        findings['usage_examples'] = usage_matches
        
        usage_check = self.checks['documentation']['items'][2]
        results.append(CheckResult(
            check_id=usage_check['id'],
            passed=len(usage_matches) > 0,
            points_earned=usage_check['points'] if usage_matches else 0,
            points_possible=usage_check['points'],
            category='documentation',
            message=usage_check['name']
        ))
        
        # Check for expected output documentation
        output_patterns = self.checks['documentation']['items'][3]['patterns']
        output_matches = self._search_code_patterns(
            repo_path, output_patterns, ['README.md', '*.md', 'docs/*.md']
        )
        findings['expected_output'] = output_matches
        
        output_check = self.checks['documentation']['items'][3]
        results.append(CheckResult(
            check_id=output_check['id'],
            passed=len(output_matches) > 0,
            points_earned=output_check['points'] if output_matches else 0,
            points_possible=output_check['points'],
            category='documentation',
            message=output_check['name']
        ))
        
        return results, findings
    
    def _check_testing(self, repo_path: str) -> tuple[List[CheckResult], Dict]:
        """Check for tests and CI/CD."""
        results = []
        findings = {}
        
        # Check for test files
        test_dirs = self.checks['testing']['items'][0]['directories']
        found_test_dirs = self._find_directories(repo_path, test_dirs)
        
        test_patterns = self.checks['testing']['items'][0]['patterns']
        test_files = self._find_files_by_pattern(repo_path, test_patterns)
        
        findings['test_directories'] = found_test_dirs
        findings['test_files'] = test_files
        
        test_check = self.checks['testing']['items'][0]
        has_tests = len(found_test_dirs) > 0 or len(test_files) > 0
        results.append(CheckResult(
            check_id=test_check['id'],
            passed=has_tests,
            points_earned=test_check['points'] if has_tests else 0,
            points_possible=test_check['points'],
            category='testing',
            message=test_check['name']
        ))
        
        # Check for CI/CD
        ci_files = self.checks['testing']['items'][1]['files']
        found_ci = self._find_files(repo_path, ci_files)
        findings['ci_files'] = found_ci
        
        ci_check = self.checks['testing']['items'][1]
        results.append(CheckResult(
            check_id=ci_check['id'],
            passed=len(found_ci) > 0,
            points_earned=ci_check['points'] if found_ci else 0,
            points_possible=ci_check['points'],
            category='testing',
            message=ci_check['name']
        ))
        
        # Check for coverage tools
        coverage_patterns = self.checks['testing']['items'][2]['patterns']
        coverage_matches = self._search_code_patterns(
            repo_path, coverage_patterns, ['*.cfg', '*.ini', 'pyproject.toml', '*.yml', '*.yaml']
        )
        findings['coverage_config'] = coverage_matches
        
        cov_check = self.checks['testing']['items'][2]
        results.append(CheckResult(
            check_id=cov_check['id'],
            passed=len(coverage_matches) > 0,
            points_earned=cov_check['points'] if coverage_matches else 0,
            points_possible=cov_check['points'],
            category='testing',
            message=cov_check['name']
        ))
        
        return results, findings
    
    # Helper methods
    
    def _find_files(self, repo_path: str, filenames: List[str]) -> List[str]:
        """Find files matching given names."""
        found = []
        repo = Path(repo_path)
        
        for filename in filenames:
            # Handle glob patterns
            if '*' in filename or '/' in filename:
                matches = list(repo.glob(filename))
                found.extend([str(m.relative_to(repo)) for m in matches])
            else:
                # Exact filename search
                for path in repo.rglob(filename):
                    found.append(str(path.relative_to(repo)))
        
        return found
    
    def _find_files_by_pattern(self, repo_path: str, patterns: List[str]) -> List[str]:
        """Find files matching glob patterns."""
        found = []
        repo = Path(repo_path)
        
        for pattern in patterns:
            matches = list(repo.rglob(pattern))
            found.extend([str(m.relative_to(repo)) for m in matches])
        
        return found
    
    def _find_directories(self, repo_path: str, dir_names: List[str]) -> List[str]:
        """Find directories matching given names."""
        found = []
        repo = Path(repo_path)
        
        for dir_name in dir_names:
            dir_name_clean = dir_name.rstrip('/')
            for path in repo.rglob(dir_name_clean):
                if path.is_dir():
                    found.append(str(path.relative_to(repo)))
        
        return found
    
    def _search_code_patterns(
        self, repo_path: str, patterns: List[str], file_globs: List[str]
    ) -> List[Dict]:
        """Search for regex patterns in specified files."""
        matches = []
        repo = Path(repo_path)
        
        # Find all matching files
        files_to_search = set()
        for glob in file_globs:
            files_to_search.update(repo.rglob(glob))
        
        # Search each file
        for file_path in files_to_search:
            if not file_path.is_file():
                continue
            
            try:
                content = file_path.read_text(errors='ignore')
                
                for pattern in patterns:
                    regex = re.compile(pattern, re.IGNORECASE)
                    for match in regex.finditer(content):
                        matches.append({
                            'file': str(file_path.relative_to(repo)),
                            'pattern': pattern,
                            'match': match.group(),
                            'line': content[:match.start()].count('\n') + 1
                        })
            except Exception:
                continue
        
        return matches
    
    def _check_dependency_pinning(
        self, repo_path: str, env_files: List[str]
    ) -> tuple[int, int]:
        """Count pinned vs unpinned dependencies."""
        pinned = 0
        total = 0
        repo = Path(repo_path)
        
        for env_file in env_files:
            file_path = repo / env_file
            if not file_path.exists():
                continue
            
            content = file_path.read_text(errors='ignore')
            
            if 'requirements' in env_file:
                # Parse requirements.txt
                for line in content.split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    total += 1
                    # Check for exact version pinning (==)
                    if '==' in line:
                        pinned += 1
            
            elif 'environment.yml' in env_file:
                # Parse conda environment
                import yaml
                try:
                    env_config = yaml.safe_load(content)
                    if 'dependencies' in env_config:
                        for dep in env_config['dependencies']:
                            if isinstance(dep, str):
                                total += 1
                                if '=' in dep or '==' in dep:
                                    pinned += 1
                except Exception:
                    pass
            
            elif 'pyproject.toml' in env_file:
                # Parse pyproject.toml (simplified)
                for line in content.split('\n'):
                    if '=' in line and '"' in line:
                        total += 1
                        if '==' in line:
                            pinned += 1
        
        return pinned, total
    
    def _get_commit_hash(self, repo_path: str) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except Exception:
            return 'unknown'
    
    def _get_repo_url(self, repo_path: str) -> str:
        """Get repository remote URL."""
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except Exception:
            return 'unknown'


def analyze_repo_from_url(repo_url: str, checks_config: str = "data/checks.json") -> Dict:
    """
    Clone and analyze a repository from URL.
    
    Args:
        repo_url: GitHub/GitLab repository URL
        checks_config: Path to checks configuration
        
    Returns:
        Analysis result as dictionary
    """
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone repository
        subprocess.run(['git', 'clone', '--depth', '1', repo_url, tmpdir], check=True)
        
        # Run analysis
        analyzer = RepositoryAnalyzer(checks_config)
        result = analyzer.analyze_repository(tmpdir)
        
        # Convert to dict for JSON serialization
        return {
            'repo_url': result.repo_url,
            'commit_hash': result.commit_hash,
            'timestamp': result.timestamp,
            'score': result.score_data['overall_score'],
            'rating': result.score_data['rating'],
            'category_scores': result.score_data['category_scores'],
            'recommendations': result.recommendations,
            'badge_data': result.badge_data
        }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        repo_url = sys.argv[1]
        result = analyze_repo_from_url(repo_url)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python analyze.py <repo_url>")
