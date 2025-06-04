# Developer Guide

## Setting Up for Development
- Clone the repo and set up the environment as in `INSTALL.md`.
- Use a virtual environment for all development.

## Testing
- Add tests for new features and bug fixes.
- Use `pytest` or the built-in test framework.
- Run tests before submitting a pull request.

## Debugging
- Use logging (`local_llm.log`, `server_errors.log`) for debugging.
- Use breakpoints and IDE tools as needed.

## Building the Desktop App
- To build a Windows executable:
  ```sh
  python main.py build_exe
  ```
- The output will be in the `dist/` directory.

## Code Style
- Follow PEP8 and see `CONTRIBUTING.md` for details. 