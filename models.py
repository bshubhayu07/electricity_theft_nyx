"""Compatibility module for models saved by older project versions.

The bundled joblib artifact was created when ``TheftDetectionEnsemble`` lived
in a top-level ``models`` module. Re-exporting it keeps that artifact loadable
after the backend was converted to the ``src`` package.
"""

from src.models import TheftDetectionEnsemble

__all__ = ["TheftDetectionEnsemble"]
