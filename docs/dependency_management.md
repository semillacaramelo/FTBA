
# Dependency Management

## Python-Deriv-API Library

This project uses the `python-deriv-api` library for interacting with the Deriv API. Previously, this library was included as a git submodule (directly cloned into the repository). 

We've now changed to a more maintainable approach:

1. The library is now specified as a dependency in `setup.py` and installed directly from the source repository
2. This eliminates the need to track the library code in our own repository
3. Updates can be managed by simply updating the dependency specification

### Important Notes on Deriv API Package

The Deriv API package has several important considerations:

1. **Naming Inconsistency**:
   - The GitHub repository is named `python-deriv-api`
   - The package is imported in code as `deriv_api`
   - The correct dependency specification uses `#egg=python-deriv-api`

2. **Version Requirements**:
   - The package requires `websockets==10.3` specifically
   - Using any other version of `websockets` will cause dependency conflicts

These inconsistencies can lead to installation issues if not addressed properly.

## Installation

To install all dependencies including the Deriv API:

```bash
pip install -e .
```

This will install the project in development mode with all required dependencies.

Alternatively, to install the Deriv API package directly:

```bash
pip install git+https://github.com/deriv-com/python-deriv-api.git#egg=python-deriv-api
```

## Verifying Dependencies

To verify that all required dependencies are installed correctly:

```bash
python scripts/check_dependencies.py
```

This script will check for all critical dependencies and provide installation instructions for any that are missing.

## Managing Dependencies

When adding new dependencies:

1. Update `setup.py` with the new dependency
2. Run `pip install -e .` to install the new dependencies

For external packages hosted on GitHub or other repositories:
1. Add them to the `dependency_links` section in `setup.py`
2. Ensure the egg fragment correctly matches the package's metadata name

## Testing

The `run_tests.py` script now properly handles dependency testing and will skip the `python-deriv-api` directory during static analysis.
