from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo


class SierraDateTime(datetime):
    """A thin wrapper around datetime that ensures Sierra API-compatible formatting."""

    def __new__(cls, *args, **kwargs):
        """Ensure that the datetime is always timezone-aware (defaults to UTC) and microseconds are removed."""
        instance = super().__new__(cls, *args, **kwargs)
        return instance.replace(microsecond=0).astimezone(timezone.utc)

    def __str__(self):
        """Return the Sierra API-compliant timestamp format."""
        return self.isoformat()

    def isoformat(self, sep="T", timespec="seconds"):
        """Override isoformat to always produce UTC format with 'Z'."""
        return super().isoformat(sep=sep, timespec=timespec).replace("+00:00", "Z")

    @classmethod
    def now(cls):
        """Return the current time in SierraDateTime format."""
        return cls.from_datetime(datetime.now(timezone.utc))

    @classmethod
    def from_datetime(cls, dt: datetime):
        """Convert a given datetime object to SierraDateTime, ensuring it's in UTC."""
        return super().__new__(cls, dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, tzinfo=timezone.utc)

    @classmethod
    def from_iso(cls, iso_string: str):
        """Convert a Sierra API timestamp (ISO format) into a SierraDateTime object."""
        return cls.from_datetime(datetime.fromisoformat(iso_string.replace("Z", "+00:00")))

    @classmethod
    def from_string(cls, dt_string: str, tz: str = None):
        """
        Convert a datetime string into a SierraDateTime object.

        Supports:
        - Explicit timezone offsets (e.g., '2012-09-06 10:11:00.000 -0400')
        - Named timezones (e.g., 'America/Los_Angeles' passed as `tz`)
        - Flexible formats (handles timestamps with/without milliseconds)

        :param dt_string: Datetime string to parse.
        :param tz: Optional timezone name (e.g., 'America/New_York'). Defaults to UTC.
        :return: SierraDateTime object.
        """
        # List of possible datetime formats
        formats = [
            "%Y-%m-%d %H:%M:%S.%f %z",  # Full format with milliseconds and offset
            "%Y-%m-%d %H:%M:%S %z",  # No milliseconds, with offset
            "%Y-%m-%d %H:%M:%S.%f",  # Milliseconds, no offset
            "%Y-%m-%d %H:%M:%S",  # No milliseconds, no offset
        ]

        parsed_dt = None

        if tz:
            # Case 1: Named timezone (America/New_York)
            local_tz = ZoneInfo(tz)
            for fmt in formats[2:]:  # Only try formats without explicit offsets
                try:
                    naive_dt = datetime.strptime(dt_string, fmt)  # Parse without a timezone
                    parsed_dt = naive_dt.replace(tzinfo=local_tz)  # Attach given timezone
                    break  # Stop if parsing succeeds
                except ValueError:
                    continue
        else:
            # Case 2: Explicit UTC offset
            for fmt in formats:
                try:
                    parsed_dt = datetime.strptime(dt_string, fmt)
                    break  # Stop if parsing succeeds
                except ValueError:
                    continue

        if parsed_dt is None:
            raise ValueError(f"Could not parse the datetime string: {dt_string}")

        # Convert to UTC and return as SierraDateTime
        return cls.from_datetime(parsed_dt.astimezone(timezone.utc))



class SierraDate(date):
    """A thin wrapper around date that ensures Sierra API-compatible formatting (YYYY-MM-DD)."""

    def __new__(cls, *args, **kwargs):
        """Ensure that the date object is created properly."""
        return super().__new__(cls, *args, **kwargs)

    def __str__(self):
        """Return the date in the Sierra API-compatible format (YYYY-MM-DD)."""
        return self.isoformat()

    @classmethod
    def today(cls):
        """Return the current date in SierraDate format."""
        return cls.from_date(date.today())

    @classmethod
    def from_date(cls, dt: date):
        """Convert a given date object to SierraDate."""
        return cls(dt.year, dt.month, dt.day)

    @classmethod
    def from_iso(cls, iso_string: str):
        """Convert a Sierra API date (ISO format) into a SierraDate object."""
        return cls.from_date(date.fromisoformat(iso_string))
