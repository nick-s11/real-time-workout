"""Configuration constants for database connectivity.

`DATABASE_URL` may be overridden in production via environment variables.
"""

DATABASE_URL = "sqlite:///database.db"
DATABASE_OPTIONS = {"echo": False}
