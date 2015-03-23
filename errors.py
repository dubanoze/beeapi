class API_ERROR(Exception):
    """base error"""
    pass


class ACCESS_ERROR(API_ERROR):
    """base access error"""
    pass


class INIT_ERROR(ACCESS_ERROR):
    """initialize error"""
    pass


class AUTH_ERROR(ACCESS_ERROR):
    """authorize error"""
    pass


class PARAM_ERROR(API_ERROR):
    """not requered parameter"""
    pass


class API_BASE_ERROR(API_ERROR):
    pass