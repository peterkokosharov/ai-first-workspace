"""Shim so unittest discover finds tools/tests/secret.py.

The real module is tools/tests/secret.py; it loads tools/secret.py under the
distinct module name ``secret_tool`` to avoid a name collision with this file.
"""

from tools.tests.secret import *  # noqa: F401, F403
