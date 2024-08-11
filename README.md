# quant-project

Quant project demonstrating quantitative analytics, data engineering and software development skills

## Installation

uv pip install -e '.[dev]'

uv pip install -e .

uv pip compile -p 3.11 pyproject.toml -o requirements.txt

## Run Streamlit

cd src/qp/ui && streamlit run streamlit_app.py

## Run Postgres

docker compose up -d

docker compose down
