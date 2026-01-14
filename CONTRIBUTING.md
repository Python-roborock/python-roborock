# Contributing to python-roborock

Thank you for your interest in contributing to `python-roborock`! We welcome contributions from the community.

## Getting Started

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/your-username/python-roborock.git
    cd python-roborock
    ```
3.  **Set up your environment**. This project typically tries to stay on the most recent python versions (e.g. latest 2 or 3 versions). We use `uv` for dependency management:
    ```bash
    # Create virtual environment and install dependencies
    uv venv
    uv sync
    ```
4.  **Activate the virtual environment**. This is required for running `pre-commit` hooks and `pytest`:
    ```bash
    source .venv/bin/activate
    ```

5.  **Install pre-commit hooks**. This ensures your code meets our quality standards. Once installed, these hooks run automatically on staged files when you commit:
    ```bash
    pre-commit install
    ```

## Development Workflow

### Code Style

We use several tools to enforce code quality and consistency. These are configured via `pre-commit` and generally run automatically.

*   **Ruff**: Used for linting and formatting.
*   **Mypy**: Used for static type checking.
*   **Codespell**: Checks for common misspellings.

You can verify your changes manually before committing (checks all files):

```bash
# Run all pre-commit hooks
pre-commit run --all-files
```

### Testing

We use `pytest` for testing. Please ensure all tests pass and add new tests for your changes.

```bash
# Run tests
pytest
```

## Pull Requests

1.  **Create a branch** for your changes.
2.  **Make your changes**. Keep your changes focused and atomic.
3.  **Commit your changes**.
    *   **Important**: We use [Conventional Commits](https://www.conventionalcommits.org/). Please format your commit messages accordingly (e.g., `feat: add new vacuum model`, `fix: handle connection timeout`). This is required for our automated release process.
    *   Allowed types: `chore`, `docs`, `feat`, `fix`, `refactor`.
4.  **Push to your fork** and submit a **Pull Request**.

## Adding New Devices or Features

If you are adding support for a new device or feature, please follow these steps:

1.  **Update Device Info**: Use the CLI to discover and fetch device features.
    ```bash
    roborock get-device-info
    ```
    Arguments and output will be printed to the console. **Manually copy the YAML output** from this command into the `device_info.yaml` file.

2.  **Add Test Data**:
    *   **Home API Data**: Capture device information from Home API responses and save as `tests/testdata/home_data_<device>.json`. This helps test device discovery and initialization.
    *   **Protocol/Feature Data**: Capture actual device responses or protocol data. You can often see these messages in the DEBUG logs when interacting with the device. Create JSON files in `tests/protocols/testdata/` that reflect these responses. This ensures protocol parsing works correctly against real-world data.

## Code of Conduct

Please be respectful and considerate in your interactions.
