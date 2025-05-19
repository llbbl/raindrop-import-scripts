# Improvement Tasks for Raindrop Import Scripts

This document contains a prioritized list of actionable tasks to improve the raindrop-import-scripts project. Each task is marked with a checkbox that can be checked off when completed.

## Project Structure and Documentation

- [x] Add a detailed project description to pyproject.toml
- [x] Create a CONTRIBUTING.md file with guidelines for contributors
- [x] Add installation instructions for Poetry in the README.md (currently mentions pipenv)
- [x] Create a CHANGELOG.md file to track version changes
- [x] Add badges to README.md (Python version, license, etc.)
- [x] Create a docs/usage.md with more detailed usage examples
- [x] Add docstrings to all modules explaining their purpose

## Code Quality and Standardization

- [x] Fix bug in enex2csv.py: `if len(records) < 0:` should be `if len(records) <= 0:`
- [x] Complete the docstring for convert_html() in pocket2csv.py
- [x] Add type hints to all functions for better code readability and IDE support
- [x] Implement consistent error handling across all scripts
- [x] Add input validation for command line arguments
- [x] Add proper exception handling for file operations
- [x] Implement logging to file option in addition to console output
- [x] Add progress indicators for long-running operations

## Architecture Improvements

- [x] Create a common module for shared functionality (logging, argument parsing)
- [x] Implement a plugin architecture to easily add new import sources
- [x] Create a unified CLI interface for all import scripts
- [x] Separate parsing logic from file I/O operations for better testability
- [x] Add configuration file support for default settings
- [x] Implement a dry-run option to validate imports without writing files

## Testing and Quality Assurance

- [x] Add unit tests for all modules
- [x] Add integration tests for end-to-end workflows
- [x] Document how to setup a CI/CD pipeline with GitHub Actions and JetBrains Pipelines
- [x] Add code coverage reporting
- [x] Add sample files for testing

## Feature Enhancements

- [x] Add support for additional import sources (Chrome bookmarks, Firefox bookmarks)
- [x] Implement direct API import to Raindrop.io
- [x] Implement filtering options for imports (by tag, date, etc.)
- [x] Add support for custom CSV field mapping
- [x] Implement a preview mode to see what will be imported
- [x] Refactor existing Python script pocket2csv.py to an object-oriented design:
  - Convert procedural scripts into classes
  - Update associated unit tests to align with the new object-oriented structure.
- [x] Refactor existing Python script firefox2csv.py to an object-oriented design. Convert procedural scripts into classes. Update associated unit tests to align with the new object-oriented structure. All unit tests should pass.
- [ ] Refactor existing Python script enex2csv.py to an object-oriented design. Convert procedural scripts into classes. Update associated unit tests to align with the new object-oriented structure. All unit tests should pass. We use poetry and run tests with `poetry run pytest`.
- [ ] Refactor existing Python script chrome2csv.py to an object-oriented design. Convert procedural scripts into classes. Update associated unit tests to align with the new object-oriented structure. All unit tests should pass. We use poetry and run tests with `poetry run pytest`.

## Performance and Scalability

- [x] Optimize memory usage for large import files
- [x] Implement chunked processing for very large files
- [ ] Implement progress tracking for long-running imports
- [ ] Add benchmarking tools to measure performance

## Security and Data Handling

- [ ] Add data validation for imported content
- [ ] Implement secure handling of API credentials (if direct API import is added)
- [ ] Add option to sanitize HTML content
- [ ] Implement proper error handling for malformed input files
- [ ] Add data backup option before processing

## User Experience

- [ ] Create a simple web UI for the import tools
- [ ] Add colorized console output for better readability
- [ ] Implement interactive mode for configuration
- [ ] Add support for environment variables for configuration
- [ ] Create detailed error messages with suggestions for resolution
