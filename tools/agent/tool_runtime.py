"""OpenWrite agent 工具执行器工厂。"""

from __future__ import annotations

from pathlib import Path
from typing import Callable


def build_tool_executors(project_root: Path) -> dict[str, Callable[[dict], dict]]:
    """构建 CLI 可复用的工具执行器映射。"""
    from tools import cli as cli_module

    if hasattr(cli_module, "build_cli_tool_executors"):
        return cli_module.build_cli_tool_executors(project_root)

    raise AttributeError("tools.cli missing build_cli_tool_executors")
