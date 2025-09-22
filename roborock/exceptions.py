"""Roborock exceptions."""

from __future__ import annotations


class RoborockException(Exception):
    """Class for Roborock exceptions."""


class RoborockTimeout(RoborockException):
    """Class for Roborock timeout exceptions."""


class RoborockConnectionException(RoborockException):
    """Class for Roborock connection exceptions."""


class RoborockBackoffException(RoborockException):
    """Class for Roborock exceptions when many retries were made."""


class VacuumError(RoborockException):
    """Class for vacuum errors."""


class CommandVacuumError(RoborockException):
    """Class for command vacuum errors."""

    def __init__(self, command: str | None, vacuum_error: VacuumError):
        self.message = f"{command or 'unknown'}: {str(vacuum_error)}"
        super().__init__(self.message)


class UnknownMethodError(RoborockException):
    """Class for an invalid method being sent."""


class RoborockAccountDoesNotExist(RoborockException):
    """Class for Roborock account does not exist exceptions."""


class RoborockUrlException(RoborockException):
    """Class for being unable to get the URL for the Roborock account."""


class RoborockInvalidCode(RoborockException):
    """Class for Roborock invalid code exceptions."""


class RoborockInvalidEmail(RoborockException):
    """Class for Roborock invalid formatted email exceptions."""


class RoborockInvalidUserAgreement(RoborockException):
    """Class for Roborock invalid user agreement exceptions."""


class RoborockNoUserAgreement(RoborockException):
    """Class for Roborock no user agreement exceptions."""


class RoborockInvalidCredentials(RoborockException):
    """Class for Roborock credentials have expired or changed."""


class RoborockTooFrequentCodeRequests(RoborockException):
    """Class for Roborock too frequent code requests exceptions."""


class RoborockMissingParameters(RoborockException):
    """Class for Roborock missing parameters exceptions."""


class RoborockTooManyRequest(RoborockException):
    """Class for Roborock too many request exceptions."""


class RoborockRateLimit(RoborockException):
    """Class for our rate limits exceptions."""


class RoborockNoResponseFromBaseURL(RoborockException):
    """We could not find an url that had a record of the given account."""
