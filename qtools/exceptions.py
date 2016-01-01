class InvalidLookupUsage(Exception):
    pass


class InvalidFieldLookupCombo(InvalidLookupUsage):
    """
    This is not a valid field-type/lookup combination.

    Example:
        obj_matches_q(obj, Q(is_active__endswith='Bob'))
        # throw exception because using a string lookup on a boolean doesn't make sense
    """
    pass


class InvalidLookupValue(InvalidLookupUsage):
    pass


class NoOpFilterException(Exception):
    """The filter statement is equivalent to no filter at all"""
    pass
