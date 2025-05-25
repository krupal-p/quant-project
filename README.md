# Quant Project

A project demonstrating quantitative analytics, data engineering, and software development skills.

---

## Getting Started with `uv`

### Installation

#### On macOS/Linux

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Or via pip

```sh
pip install uv
```

---

## Creating a New Project

```sh
# Create a new project with a virtual environment
uv init my-project
cd my-project

# Or initialize in an existing directory
uv init
```

This creates a `pyproject.toml` file and sets up the project structure.

---

## Managing Virtual Environments

```sh
# Create a virtual environment (if not already created)
uv venv
```

**Activate the virtual environment:**

- **On Unix/macOS:**
  ```sh
  source .venv/bin/activate
  ```
- **On Windows:**
  ```sh
  .venv\Scripts\activate
  ```

Or run commands directly in the venv without activation:

```sh
uv run python script.py
```

---

## Adding Packages

```sh
# Add a package (installs and adds to pyproject.toml)
uv add requests

# Add a specific version
uv add "django>=4.0,<5.0"

# Add development dependencies
uv add --dev pytest black flake8

# Add from a specific index
uv add --index-url https://pypi.org/simple/ some-package

# Add from git repository
uv add git+https://github.com/user/repo.git

# Add local package in editable mode
uv add -e ./local-package
```

---

## Removing Packages

```sh
# Remove a package
uv remove requests

# Remove multiple packages
uv remove requests urllib3 certifi

# Remove development dependencies
uv remove --dev pytest
```

---

## Installing Dependencies

```sh
# Install all dependencies from pyproject.toml
uv sync

# Install only production dependencies (skip dev dependencies)
uv sync --no-dev

# Install from requirements.txt (if migrating from pip)
uv pip install -r requirements.txt
```

---

## Upgrading Packages

```sh
# Upgrade a specific package to latest version
uv add "requests@latest"

# Or use the lock command to upgrade
uv lock --upgrade-package requests

# Upgrade all packages to their latest compatible versions
uv lock --upgrade

# Then sync to apply the upgrades
uv sync
```

---

## Working with Lock Files

```sh
# Generate/update the lock file (uv.lock)
uv lock

# Sync installed packages with the lock file
uv sync

# Export lock file to requirements.txt format
uv export --format requirements-txt > requirements.txt
```

---

## Running Commands

```sh
# Run Python scripts in the project environment
uv run python script.py

# Run installed command-line tools
uv run pytest
uv run black .
uv run mypy src/

# Run with specific Python version
uv run --python 3.11 python script.py
```

---

## Viewing Package Information

```sh
# List installed packages
uv pip list

# Show package information
uv pip show requests

# Check for outdated packages
uv pip list --outdated

# Show dependency tree
uv tree
```

---

## Working with Different Python Versions

```sh
# Create venv with specific Python version
uv venv --python 3.11

# Add package for specific Python version
uv add --python 3.11 some-package
```

---

## Project Setup

### Installation

```sh
uv pip install -e '.[dev]'
uv pip install -e .
uv pip compile -p 3.12 pyproject.toml -o requirements.txt
uv pip sync requirements.txt && uv pip install -e '.[dev]'
```

### Upgrade all packages

```sh
uv pip compile -p 3.12 pyproject.toml -o requirements.txt --upgrade
```

### Upgrade a specific package

```sh
uv pip compile -p 3.12 pyproject.toml -o requirements.txt --upgrade-package pandas
```

---

## Run Streamlit

```sh
cd src/app/ui && streamlit run streamlit_app.py
```

---

## Run SQL Server in Docker

```sh
docker compose up -d
docker compose down
```
