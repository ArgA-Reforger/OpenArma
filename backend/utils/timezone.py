import zoneinfo

from datetime import datetime
from datetime import timezone as datetime_timezone

from backend.core.conf import settings


class TimeZone:
    def __init__(self) -> None:
        """Initialize the timezone converter"""
        self.tz_info = zoneinfo.ZoneInfo(settings.DATETIME_TIMEZONE)

    def now(self) -> datetime:
        """Get the current time in the configured timezone"""
        return datetime.now(self.tz_info)

    def from_datetime(self, t: datetime) -> datetime:
        """
        Convert a datetime object to the current timezone

        :param t: datetime object to convert
        :return:
        """
        return t.astimezone(self.tz_info)

    def from_str(self, t_str: str, format_str: str = settings.DATETIME_FORMAT) -> datetime:
        """
        Convert a time string to a datetime object in the current timezone

        :param t_str: time string
        :param format_str: time format string, defaults to settings.DATETIME_FORMAT
        :return:
        """
        return datetime.strptime(t_str, format_str).replace(tzinfo=self.tz_info)

    @staticmethod
    def to_str(t: datetime, format_str: str = settings.DATETIME_FORMAT) -> str:
        """
        Convert a datetime object to a time string in the given format

        :param t: datetime object
        :param format_str: time format string, defaults to settings.DATETIME_FORMAT
        :return:
        """
        return t.strftime(format_str)

    @staticmethod
    def to_utc(t: datetime | int) -> datetime:
        """
        Convert a datetime object or timestamp to UTC

        :param t: datetime object or timestamp to convert
        :return:
        """
        if isinstance(t, datetime):
            return t.astimezone(datetime_timezone.utc)
        return datetime.fromtimestamp(t, tz=datetime_timezone.utc)


timezone: TimeZone = TimeZone()
