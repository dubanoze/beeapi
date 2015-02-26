try:
    from bill_classes import ClassGetter, session
    from client import Rest, Soap
except ImportError:
    from .bill_classes import ClassGetter, session
    from .client import Rest, Soap
