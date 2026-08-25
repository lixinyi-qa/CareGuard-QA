$ErrorActionPreference = "Stop"
python -m pytest tests -m "not ui and not mysql" --cov=app --cov-report=term-missing --cov-report=html
