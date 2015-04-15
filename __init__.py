try:
    from models import ClassGetter, session
    from client import Rest, Soap
except ImportError:
    from .models import ClassGetter, session
    from .client import Rest, Soap
