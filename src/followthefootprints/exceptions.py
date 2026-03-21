"""Custom exceptions for the FollowTheFootPrints analyser."""


class UnknownIntervalException(Exception):
    """Raised when an unsupported yfinance interval string is provided."""


class IntervalRunNotPossibleException(Exception):
    """Raised when a valid interval cannot be used in the current run context."""
