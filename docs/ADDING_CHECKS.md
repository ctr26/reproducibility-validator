# Adding New Checks

This guide explains how to add new reproducibility checks to the validator.

---

## Check Definition Structure

All checks are defined in `data/checks.json`. The structure is:

```json
{
  "checks": {
    "category_name": {
      "weight": 25,
      "items": [
        {
          "id": "check_id",
          "name": "Human-readable name",
          "description": "What this check validates",
          "points": 10,
          "severity": "critical",  // optional
          "files": ["file1.txt", "file2.py"],  // optional
          "directories": ["dir/"],  // optional
          "patterns": ["regex1", "regex2"]  // optional
        }
      ]
    }
  }
}
```

---

## Categories

The validator has 5 categories, each with a weight:

| Category | Weight | Purpose |
|----------|--------|---------|
| `environment` | 25% | Dependency management |
| `randomness` | 20% | Seed control and determinism |
| `data` | 20% | Data availability |
| `documentation` | 20% | Documentation quality |
| `testing` | 15% | Tests and CI/CD |

**Total must equal 100%**

---

## Check Types

### 1. File Existence Checks

Verify that specific files exist in the repository.

**Example**: Check for README file

```json
{
  "id": "readme_exists",
  "name": "README exists",
  "description": "Repository has a README file",
  "points": 5,
  "files": ["README.md", "README.rst", "README.txt"]
}
```

The check passes if **any** of the listed files exist.

### 2. Pattern Matching Checks

Search code/documentation for regex patterns.

**Example**: Check for random seed

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

Searches all `.py` files by default. Use `file_globs` to customize.

### 3. Directory Checks

Verify that specific directories exist.

**Example**: Check for test directory

```json
{
  "id": "tests_exist",
  "name": "Tests exist",
  "description": "Repository contains test files",
  "points": 8,
  "directories": ["tests/", "test/"]
}
```

---

## Adding a New Check

### Step 1: Define the Check

Add to `data/checks.json` in the appropriate category:

```json
{
  "id": "container_definition",
  "name": "Container definition exists",
  "description": "Repository has Docker or Singularity container",
  "points": 8,
  "files": ["Dockerfile", "Singularity", "container.def"]
}
```

### Step 2: Add Recommendation (Optional)

Add to the `recommendations` section:

```json
{
  "container_definition": {
    "fix": "Add a Dockerfile to containerize your environment",
    "example": "FROM python:3.11\nCOPY requirements.txt .\nRUN pip install -r requirements.txt"
  }
}
```

### Step 3: Update Analysis Logic (If Needed)

Most checks work automatically via:
- `_find_files()` for file checks
- `_search_code_patterns()` for pattern checks
- `_find_directories()` for directory checks

For complex checks, add custom logic to `api/analyze.py`:

```python
def _check_custom_feature(self, repo_path: str) -> tuple[List[CheckResult], Dict]:
    """Custom check logic."""
    results = []
    findings = {}
    
    # Your custom analysis here
    custom_data = self._analyze_something_custom(repo_path)
    
    check = self.checks['category']['items'][0]
    results.append(CheckResult(
        check_id=check['id'],
        passed=custom_data is not None,
        points_earned=check['points'] if custom_data else 0,
        points_possible=check['points'],
        category='category_name',
        message=check['name']
    ))
    
    findings['custom_metric'] = custom_data
    return results, findings
```

Then call it from `analyze_repository()`:

```python
custom_results, custom_findings = self._check_custom_feature(repo_path)
check_results.extend(custom_results)
raw_findings['custom'] = custom_findings
```

---

## Check Best Practices

### 1. Point Values

| Points | Meaning |
|--------|---------|
| 2-3 | Nice to have |
| 5 | Important |
| 8-10 | Critical for reproducibility |

**Critical checks** should have `"severity": "critical"` for high-priority recommendations.

### 2. Pattern Writing

Use Python regex syntax (case-insensitive by default):

```json
"patterns": [
  "torch\\.manual_seed\\(",      // Literal dots must be escaped
  "set\\.seed\\(",                 // R seed setting
  "seed.*=.*\\d+",                 // Seed assignment with number
  "reproducib"                     // Partial match (reproducible, reproducibility)
]
```

### 3. File Globs

Patterns can include wildcards:

```json
"files": [
  "*.txt",           // All .txt files
  "data/*.csv",      // CSV files in data/
  "**/*.yml"         // All YAML files recursively
]
```

### 4. Multiple Conditions

For checks that require **all** conditions, create multiple checks:

```json
{
  "id": "seed_set",
  "name": "Random seed initialized",
  "points": 5,
  "patterns": ["seed\\("]
},
{
  "id": "seed_documented",
  "name": "Seed value documented",
  "points": 5,
  "patterns": ["seed.*=.*\\d+"]
}
```

This is better than one 10-point check because it provides more granular feedback.

---

## Example: Adding GPU Reproducibility Checks

Let's add checks for GPU determinism:

### 1. Add to `randomness` category in `data/checks.json`

```json
{
  "id": "gpu_deterministic",
  "name": "GPU determinism configured",
  "description": "Framework configured for deterministic GPU operations",
  "points": 7,
  "severity": "high",
  "patterns": [
    "torch\\.backends\\.cudnn\\.deterministic\\s*=\\s*True",
    "torch\\.backends\\.cudnn\\.benchmark\\s*=\\s*False",
    "TF_DETERMINISTIC_OPS.*=.*1",
    "CUBLAS_WORKSPACE_CONFIG"
  ]
}
```

### 2. Add recommendation

```json
{
  "gpu_deterministic": {
    "fix": "Configure your framework for deterministic GPU operations",
    "example": "# PyTorch\ntorch.backends.cudnn.deterministic = True\ntorch.backends.cudnn.benchmark = False\n\n# TensorFlow\nimport os\nos.environ['TF_DETERMINISTIC_OPS'] = '1'"
  }
}
```

### 3. Test

```bash
# Test with a repo that has GPU code
python api/analyze.py https://github.com/pytorch/examples
```

---

## Language-Specific Checks

### Python
Already supported. Patterns work in `.py` files.

### R
Add R-specific patterns:

```json
{
  "id": "r_seed_detection",
  "name": "R random seed set",
  "points": 10,
  "patterns": [
    "set\\.seed\\(",
    "RNGkind\\("
  ]
}
```

### Julia
```json
{
  "id": "julia_seed_detection",
  "name": "Julia random seed set",
  "points": 10,
  "patterns": [
    "Random\\.seed!\\(",
    "using Random"
  ]
}
```

### MATLAB
```json
{
  "id": "matlab_seed_detection",
  "name": "MATLAB random seed set",
  "points": 10,
  "patterns": [
    "rng\\(",
    "rand\\('seed'"
  ]
}
```

---

## Testing New Checks

### 1. Unit Test

Add to `tests/test_analyze.py`:

```python
def test_new_check():
    """Test your new check."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = {
            'file_with_pattern.py': 'code that should match pattern'
        }
        
        repo_path = create_test_repo(tmpdir, files)
        analyzer = RepositoryAnalyzer('data/checks.json')
        
        results, findings = analyzer._check_category(repo_path)
        
        assert any(r.check_id == 'new_check_id' and r.passed for r in results)
```

### 2. Integration Test

Test on a real repository:

```bash
python api/analyze.py https://github.com/example/repo
```

Look for your new check in the output.

---

## Adjusting Weights

To change category weights, edit the `weight` values in `data/checks.json`:

```json
{
  "environment": {
    "weight": 30,  // Increased from 25
    ...
  },
  "testing": {
    "weight": 10,  // Decreased from 15
    ...
  }
}
```

**Ensure total still equals 100!**

---

## Community Contributions

When contributing new checks:

1. **Focus on measurable signals**: Avoid subjective checks
2. **Provide examples**: Include "good" vs "bad" examples
3. **Document the rationale**: Why is this important for reproducibility?
4. **Test on real repos**: Ensure low false positive rate
5. **Add to multiple categories**: If needed (e.g., data + docs)

---

## Check Ideas

Potential checks to add:

### High Priority
- [ ] License detection (CITATION.cff, LICENSE)
- [ ] Version control best practices (.gitignore, no large files)
- [ ] Virtual environment specification (venv, conda)
- [ ] Hardware specification (GPU model, CPU cores)

### Medium Priority
- [ ] Code formatting (black, ruff, pylint configs)
- [ ] Pre-commit hooks (.pre-commit-config.yaml)
- [ ] Notebook reproducibility (requirements in notebooks)
- [ ] Data versioning (DVC, git-lfs)

### Advanced
- [ ] Static type checking (mypy.ini, type hints)
- [ ] Benchmarking scripts (performance tests)
- [ ] Cross-platform testing (Windows, Linux, macOS CI)
- [ ] Container registry (Docker Hub, Singularity)

---

## Questions?

Open an issue on GitHub or email support@reproducibility-validator.com
