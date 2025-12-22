"""Compatibility shim.

The implementation lives in `app.utils.prompt_dumper`.
"""

from .utils.prompt_dumper import PromptDumper, configure_prompt_dumper, get_prompt_dumper

__all__ = ["PromptDumper", "configure_prompt_dumper", "get_prompt_dumper"]
