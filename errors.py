from sqlalchemy.exc import SQLAlchemyError

class APIError(Exception):
    """base error"""
    pass


class AccessError(APIError):
    """base access error"""
    pass


class InitializationError(AccessError):
    """initialize error"""
    pass


class AuthorizationError(AccessError):
    """authorize error"""
    pass


class ParameterError(APIError):
    """not requered parameter"""
    pass


class APIBaseExc(APIError):
    pass

class DatabaseError(SQLAlchemyError):
    pass