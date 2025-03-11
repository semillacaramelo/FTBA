
# Dependency Management

## Python-Deriv-API Library

This project uses the `python-deriv-api` library for interacting with the Deriv API. Previously, this library was included as a git submodule (directly cloned into the repository). 

We've now changed to a more maintainable approach:

1. The library is now specified as a dependency in `requirements.txt` and installed directly from the source repository
2. This eliminates the need to track the library code in our own repository
3. Updates can be managed by simply updating the dependency specification

## Installation

To install all dependencies including the Deriv API:

```bash
pip install -e .
```

This will install the project in development mode with all required dependencies.

## Managing Dependencies

When adding new dependencies:

1. Add them to `requirements.txt`
2. Update `setup.py` as needed
3. Run `pip install -e .` to install the new dependencies

## Testing

The `run_tests.py` script now properly handles dependency testing and will skip the `python-deriv-api` directory during static analysis.
