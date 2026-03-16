from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mm")
except PackageNotFoundError:
    try:
        from mm._version import __version__  # type: ignore[no-redef]
    except ImportError:
        __version__ = "0.0.0-dev"
