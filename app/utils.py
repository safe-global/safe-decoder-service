from datetime import datetime


def datetime_to_str(value: datetime) -> str:
    """
    :param value: `datetime.datetime` value
    :return: ``ISO 8601`` date with ``Z`` format
    """
    return value.isoformat().replace("+00:00", "Z")
