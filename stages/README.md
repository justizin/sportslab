# Stages

Each directory is one learning stage from `docs/curriculum.md`. Inside:

- `README.md`: the concept, what to read first, the task, and an acceptance check you can verify yourself.
- `exercise.py`: a marimo notebook with the setup done and the interesting parts left as stubs marked `TODO`.
- `solutions/solution.py`: a reference implementation. Open it after you have an answer, or when stuck for more than an hour.

Run a notebook with `uv run marimo edit stages/01_pythagorean/exercise.py`. Stage 0 is fully
worked, as the example of what a finished stage looks like.

| Stage | Concept | Project | Status |
|---|---|---|---|
| `00_data_stack` | pandas, DuckDB SQL, joins, plotting | standings from game logs; runs scored vs allowed since 1901 | worked example |
| `01_pythagorean` | distributions, residuals, fitting one parameter | Pythagorean exponent across five sports | exercise |
| `02_linear_regression` | least squares, coefficients, R², multicollinearity | Four Factors (WNBA/NBA); run expectancy (needs Chadwick) | exercise |
| `03` to `08` | see `docs/curriculum.md` | | not written yet |

Write a one-page note in `docs/notes/` when you finish a stage: what you expected, what you found,
what surprised you. Those notes are the portfolio.
