import threading
from typing import Any, Optional

from psycopg2.pool import ThreadedConnectionPool

from settings import settings

_pool: Optional[ThreadedConnectionPool] = None
_pool_lock = threading.Lock()


class PooledConnection:
    def __init__(self, connection: Any, pool: ThreadedConnectionPool):
        self._connection = connection
        self._pool = pool
        self._returned = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    def close(self) -> None:
        if not self._returned:
            self._returned = True
            self._pool.putconn(self._connection)

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return self._connection.__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadedConnectionPool(0, 10, settings.DATABASE_URL)
    return _pool


def get_connection() -> PooledConnection:
    pool = _get_pool()
    return PooledConnection(pool.getconn(), pool)


def close_all_connections() -> None:
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.closeall()
            _pool = None
