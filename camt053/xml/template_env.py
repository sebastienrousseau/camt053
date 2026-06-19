# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared, cached Jinja2 environment for XML rendering.

Building a Jinja2 :class:`~jinja2.Environment` (and compiling a template) is
relatively expensive, so repeating it on every ``generate`` / ``serialize``
call wastes work when the template directory never changes. This module
memoises one :class:`~jinja2.Environment` per template directory and one
compiled :class:`~jinja2.Template` per ``(directory, name)`` pair via
``functools.lru_cache``.

Thread-safety
-------------
The cached environment and templates are read-only once compiled: rendering a
template with :meth:`~jinja2.Template.render` builds a fresh, isolated context
per call and never mutates shared state, so concurrent ``render`` calls do not
leak data between documents. ``lru_cache`` itself is protected by the GIL for
the cache-lookup fast path.
"""

from __future__ import annotations

from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, Template

__all__ = ["get_template"]


@lru_cache(maxsize=8)
def _get_environment(template_dir: str) -> Environment:
    """Return a cached autoescaping environment for a template directory."""
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=True,
    )


@lru_cache(maxsize=16)
def get_template(template_dir: str, template_name: str) -> Template:
    """Return a cached, compiled template from a template directory.

    Args:
        template_dir: The directory the template file lives in.
        template_name: The template file name (e.g. ``"template.xml"``).

    Returns:
        The compiled :class:`~jinja2.Template`, reused across calls.
    """
    return _get_environment(template_dir).get_template(template_name)
