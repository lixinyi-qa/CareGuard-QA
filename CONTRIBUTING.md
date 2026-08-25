# Contributing

CareGuard QA is maintained as a reproducible quality-engineering portfolio project.

1. Create a focused branch and keep changes small.
2. Add or update tests for behavioral changes.
3. Run `pytest tests -m "not ui and not mysql"` before opening a pull request.
4. Do not commit real personal data, credentials, generated databases, or large runtime reports.
5. For a defect report, include environment, preconditions, steps, actual result, expected result, severity, and regression coverage.

Changes that imply medical diagnosis, treatment advice, emergency dispatch, or sharing raw elderly check-in text with linked family accounts are out of scope.
