# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""kikolib - small standard-library-only secret-store library (keystore + factory).

Rule: modules here import only the Python standard library and other kikolib
modules. OS facilities are reached through ctypes or subprocess. Each pluggable
part has an interface plus a factory (see factory.py) that picks an implementation.
"""

__all__ = [
    "factory",
    "keystore",
]

__version__ = "0.1.0"
