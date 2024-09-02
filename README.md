# quant-project

Quant project demonstrating quantitative analytics, data engineering and software development skills

## Installation

uv pip install -e '.[dev]'

uv pip install -e .

uv pip compile -p 3.12 pyproject.toml -o requirements.txt

uv pip sync requirements.txt && uv pip install -e '.[dev]'

### Upgrade all packages

uv pip compile -p 3.12 pyproject.toml -o requirements.txt --upgrade

### Upgrade a specific package

uv pip compile -p 3.12 pyproject.toml -o requirements.txt --upgrade-package pandas

## Run Streamlit

cd src/app/ui && streamlit run streamlit_app.py

## Run SQL Server in Docker

docker compose up -d

docker compose down
