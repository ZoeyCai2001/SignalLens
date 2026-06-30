import re
from datetime import timedelta


def parse_polling_interval(value: str | None) -> timedelta | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    aliases = {
        "hourly": timedelta(hours=1),
        "daily": timedelta(days=1),
        "weekly": timedelta(days=7),
    }
    if normalized in aliases:
        return aliases[normalized]

    match = re.search(
        r"(?:every\s+)?(?P<count>\d+(?:\.\d+)?)\s*(?P<unit>minute|minutes|min|hour|hours|day|days|week|weeks)",
        normalized,
    )
    if match is None:
        return None

    count = float(match.group("count"))
    unit = match.group("unit")
    if unit in {"minute", "minutes", "min"}:
        return timedelta(minutes=count)
    if unit in {"hour", "hours"}:
        return timedelta(hours=count)
    if unit in {"day", "days"}:
        return timedelta(days=count)
    if unit in {"week", "weeks"}:
        return timedelta(weeks=count)
    return None
