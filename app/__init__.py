"""Petstore API application."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("petstore-api")
except PackageNotFoundError:
    __version__ = "0.0.0"
