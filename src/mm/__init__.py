try:
    from mm._version import __version__
except ImportError:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("mm")
    except PackageNotFoundError:
        __version__ = "0.0.0-dev"
