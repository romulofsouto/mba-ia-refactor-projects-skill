from datetime import datetime, timezone


def utc_now():
    """UTC atual como datetime naive, o formato já gravado nas colunas DateTime do SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
