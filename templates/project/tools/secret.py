# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Glue: ``import secret`` gives the core's secret tool (tools/secret.py of the core).

``core.install()`` registers the core's module under the name ``secret``; importing
this file triggers that.  It holds no logic of its own.
"""

import core

core.install()
