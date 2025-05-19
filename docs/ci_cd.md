# CI/CD Pipeline Setup

This document provides instructions for setting up Continuous Integration and Continuous Deployment (CI/CD) pipelines for the Raindrop Import Scripts project using GitHub Actions and JetBrains Pipelines.

## GitHub Actions

GitHub Actions is a CI/CD platform that allows you to automate your build, test, and deployment pipeline directly from your GitHub repository.

### Setting Up GitHub Actions

1. Create a `.github/workflows` directory in your repository if it doesn't already exist:

```bash
mkdir -p .github/workflows
```

2. Create a workflow file (e.g., `python-tests.yml`) in the `.github/workflows` directory:

```yaml
name: Python Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10']

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: 1.5.1
        virtualenvs-create: true
        virtualenvs-in-project: true
    - name: Install dependencies
      run: |
        poetry install --no-interaction
    - name: Run tests
      run: |
        poetry run pytest
```

3. For code coverage reporting, add the following to your workflow file:

```yaml
    - name: Run tests with coverage
      run: |
        poetry run pytest --cov=. --cov-report=xml
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

4. Commit and push these changes to your repository. GitHub Actions will automatically run the workflow on push and pull requests to the main branch.

## JetBrains Pipelines

JetBrains Space Pipelines is a CI/CD solution integrated with JetBrains Space.

### Setting Up JetBrains Pipelines

1. Create a `.space.kts` file in the root of your repository:

```kotlin
job("Build and Test") {
    container(image = "python:3.10") {
        env["PIP_CACHE_DIR"] = "/tmp/pip-cache"
        
        // Install Poetry
        shellScript {
            content = """
                curl -sSL https://install.python-poetry.org | python3 -
                export PATH="/root/.local/bin:$PATH"
                poetry --version
            """
        }
        
        // Install dependencies
        shellScript {
            content = """
                export PATH="/root/.local/bin:$PATH"
                poetry install --no-interaction
            """
        }
        
        // Run tests
        shellScript {
            content = """
                export PATH="/root/.local/bin:$PATH"
                poetry run pytest
            """
        }
        
        // Run tests with coverage
        shellScript {
            content = """
                export PATH="/root/.local/bin:$PATH"
                poetry run pytest --cov=. --cov-report=xml --cov-report=term
            """
        }
    }
    
    // Cache pip dependencies
    cache {
        storeKey = "pip-cache"
        localPath = "/tmp/pip-cache"
    }
}
```

2. Commit and push this file to your repository. JetBrains Space will automatically detect and run the pipeline.

## Setting Up Code Coverage Reporting

To add code coverage reporting to your project:

1. Install the required packages:

```bash
poetry add --dev pytest-cov codecov
```

2. Add a `.coveragerc` file to the root of your repository:

```ini
[run]
source = .
omit = 
    tests/*
    .venv/*
    .tox/*
    setup.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:
    pass
    raise ImportError
```

3. Update your GitHub Actions workflow to upload coverage reports to Codecov (as shown above).

4. For JetBrains Pipelines, you can add a step to upload coverage reports to a service like Codecov:

```kotlin
shellScript {
    content = """
        export PATH="/root/.local/bin:$PATH"
        pip install codecov
        codecov -f coverage.xml -t ${'$'}CODECOV_TOKEN
    """
    env["CODECOV_TOKEN"] = Secrets("CODECOV_TOKEN")
}
```

5. Add a Codecov badge to your README.md:

```markdown
[![codecov](https://codecov.io/gh/username/raindrop-import-scripts/branch/main/graph/badge.svg)](https://codecov.io/gh/username/raindrop-import-scripts)
```

## Continuous Deployment

For automated releases:

1. Add a GitHub Actions workflow for publishing to PyPI:

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: 1.5.1
    - name: Build and publish
      env:
        PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
      run: |
        poetry config pypi-token.pypi $PYPI_TOKEN
        poetry build
        poetry publish
```

2. Store your PyPI token as a secret in your GitHub repository settings.

## Conclusion

With these configurations, your project will have automated testing, code coverage reporting, and deployment capabilities using both GitHub Actions and JetBrains Pipelines.