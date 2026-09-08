# medical-risk-xai api package
import sys

# Compatibility fix: passlib 1.7.4 expects bcrypt.__about__.__version__
try:
    import bcrypt
    if not hasattr(bcrypt, "__about__"):
        class _About:
            __version__ = getattr(bcrypt, "__version__", "4.0.1")
        bcrypt.__about__ = _About()
except ImportError:
    pass
