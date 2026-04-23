import datetime as dt
from typing import Optional
from zoneinfo import ZoneInfo

from pipelines.utils.logger import log


UTC_TZ = ZoneInfo("UTC")
SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


def now(utc: bool = False) -> dt.datetime:
    """
    Returns datetime.now() in UTC or BRT.

    Args:
        utc: When `True`, uses UTC. By default, uses America/Sao_Paulo.
    """
    if utc:
        return dt.datetime.now(tz=UTC_TZ)
    return dt.datetime.now(tz=SAO_PAULO_TZ)


def from_relative_date(
    relative_date: Optional[str] = None,
) -> Optional[dt.date | dt.datetime]:
    """
    Converts a relative date into a date object.

    Supports the formats:
        `D-N`: current date minus `N` days
        `M-N`: first day of the current month minus `N` months
        `Y-N`: first day of the current year minus `N` years

    If the value is not a relative date, it tries to convert it
    to `datetime` via `datetime.fromisoformat()`.
    """
    if relative_date is None:
        log("Relative date is None, returning None", level="info")
        return None

    current_datetime = now()
    current_date = current_datetime.date()

    if relative_date.startswith(("D-", "M-", "Y-")):
        quantity = int(relative_date.split("-", maxsplit=1)[1])

        if relative_date.startswith("D-"):
            result = current_date - dt.timedelta(days=quantity)
        elif relative_date.startswith("M-"):
            month_index = current_date.month - quantity - 1
            year = current_date.year + (month_index // 12)
            month = (month_index % 12) + 1
            result = dt.date(year, month, 1)
        else:
            result = dt.date(current_date.year - quantity, 1, 1)
    else:
        log(
            "The input dated is not a relative date, converting to datetime",
            level="info",
        )
        result = dt.datetime.fromisoformat(relative_date)

    log(f"Relative date is {relative_date}, returning {result}", level="info")
    return result
