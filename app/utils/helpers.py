from datetime import datetime


def parse_datetime(datetime_str: str) -> datetime:
    # Truncate the fractional seconds to six digits
    truncated_str = datetime_str[:26] + "Z"
    # Parse the datetime string
    return datetime.strptime(truncated_str, "%Y-%m-%dT%H:%M:%S.%fZ")
