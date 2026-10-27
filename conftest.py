import sqlite3

import pytest

from engine.gam_engine import run
from engine.seed import build


@pytest.fixture(scope="session")
def engine_db(tmp_path_factory):
    path = build(tmp_path_factory.mktemp("db") / "forecast.db")
    run_id = run(path)
    return path, run_id


@pytest.fixture(scope="session")
def run_id(engine_db):
    return engine_db[1]


@pytest.fixture(scope="session")
def q(engine_db):
    con = sqlite3.connect(engine_db[0])
    con.row_factory = sqlite3.Row

    class Query:
        def __call__(self, sql, params=()):
            return [dict(r) for r in con.execute(sql, params).fetchall()]

        def one(self, sql, params=()):
            return con.execute(sql, params).fetchone()[0]

    yield Query()
    con.close()


@pytest.fixture
def fresh_db(tmp_path):
    """An isolated, freshly seeded database for tests that run the engine themselves."""
    return build(tmp_path / "forecast.db")
