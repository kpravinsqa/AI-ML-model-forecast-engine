"""Every query in sql/validation returns offending rows: 0 rows = PASS."""
from pathlib import Path

import pytest

QUERIES = sorted((Path(__file__).resolve().parent.parent / "sql" / "validation").glob("*.sql"))


@pytest.mark.values
@pytest.mark.parametrize("sql_file", QUERIES, ids=[p.stem for p in QUERIES])
def test_validation_query_returns_no_rows(q, sql_file):
    rows = q(sql_file.read_text())
    assert rows == [], f"{sql_file.name}: {len(rows)} offending row(s), e.g. {rows[:3]}"
