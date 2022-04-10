from __future__ import annotations

try:
    import zipp
except ImportError:
    import zipfile as zipp  # noqa: F401

try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol  # noqa: F401
