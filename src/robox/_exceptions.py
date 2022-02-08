class RoboxError(Exception):
    ...


class MultipleFieldsReturned(RoboxError):
    ...


class InvalidValue(RoboxError):
    ...


class ForbiddenByRobots(RoboxError):
    ...


class RetryError(RoboxError):
    ...
