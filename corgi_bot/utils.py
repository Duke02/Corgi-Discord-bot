from pathlib import Path


def get_base_directory() -> Path:
    return Path(__file__).parent.parent.resolve()


def get_db_directory() -> Path:
    return get_base_directory() / "db"


def get_logs_directory() -> Path:
    return get_base_directory() / "logs"