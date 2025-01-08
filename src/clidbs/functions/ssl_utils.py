"""SSL utilities for CLIDB."""

_ssl_manager = None

def get_ssl_manager():
    """Lazy load the SSL manager after Docker checks."""
    global _ssl_manager
    if _ssl_manager is None:
        from ..ssl import ssl_manager
        _ssl_manager = ssl_manager
    return _ssl_manager 