# Testing and Code Coverage

This document provides instructions for running tests and generating code coverage reports for the Raindrop Import Scripts project.

## Running Tests

To run the tests for this project, you can use the following command:

```bash
poetry run test
```

This will run all the tests in the project using pytest.

## Generating Code Coverage Reports

To generate code coverage reports, you can use the following command:

```bash
poetry run test-cov
```

This will run all the tests and generate code coverage reports in both XML and terminal formats. The XML report is useful for CI/CD integration, while the terminal report provides a quick overview of the coverage.

### Understanding the Coverage Report

The coverage report shows the percentage of code that is covered by tests. It breaks down the coverage by file and shows which lines are covered and which are not.

Here's an example of what the terminal report might look like:

```
---------- coverage: platform darwin, python 3.11.0-final-0 -----------
Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
common/__init__.py                            0      0   100%
common/cli.py                                45      5    89%   24-25, 67-69
common/config.py                             32      2    94%   45-46
common/logging.py                            15      0   100%
common/plugins.py                            28      2    93%   31-32
common/validation.py                         18      0   100%
evernote/__init__.py                          0      0   100%
evernote/enex2csv.py                         42      4    90%   78-81
pocket/__init__.py                            0      0   100%
pocket/pocket2csv.py                         38      3    92%   62-64
raindrop_import.py                           52      5    90%   88-92
-----------------------------------------------------------------------
TOTAL                                       270     21    92%
```

### Improving Code Coverage

To improve code coverage, you can:

1. Write tests for uncovered code
2. Remove or refactor unused code
3. Add appropriate exception handling for edge cases

## Continuous Integration

Code coverage reporting is integrated into the CI/CD pipeline. See [CI/CD Pipeline Setup](ci_cd.md) for more information on how code coverage is reported in the CI/CD pipeline.

## Codecov Integration

If you've set up Codecov integration as described in the CI/CD documentation, you can view detailed coverage reports on the Codecov website. The reports include:

- Overall coverage percentage
- Coverage trends over time
- Coverage breakdown by file
- Line-by-line coverage visualization

To view the Codecov report, click on the Codecov badge in the README.md file.