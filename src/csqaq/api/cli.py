# src/csqaq/api/cli.py
"""Typer CLI for CSQAQ. Local-mode entry point."""
from __future__ import annotations

import asyncio

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from csqaq.config import Settings
from csqaq.main import App, run_item_query, setup_logging

app = typer.Typer(name="csqaq", help="CS2 饰品投资分析系统")
console = Console()


def _load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        console.print(f"[red]配置错误:[/red] {e}")
        console.print("请检查 .env 文件或环境变量，参考 .env.example")
        raise typer.Exit(1)


@app.command()
def chat(query: str | None = typer.Argument(None, help="查询内容，如 'AK红线能入吗'")):
    """查询饰品分析和投资建议。不带参数进入交互模式。"""
    setup_logging()
    settings = _load_settings()

    if query:
        # Single query mode
        result = asyncio.run(_single_query(settings, query))
        console.print(Panel(result, title="CSQAQ 分析结果", border_style="blue"))
    else:
        # Interactive mode
        asyncio.run(_interactive_mode(settings))


async def _single_query(settings: Settings, query: str) -> str:
    application = App(settings)
    await application.init()
    try:
        return await run_item_query(application, query)
    finally:
        await application.close()


async def _interactive_mode(settings: Settings) -> None:
    application = App(settings)
    await application.init()
    console.print("[bold blue]CSQAQ 饰品分析系统[/bold blue] — 输入问题，输入 quit 退出\n")
    try:
        while True:
            query = console.input("[bold green]> [/bold green]")
            if query.strip().lower() in ("quit", "exit", "q"):
                break
            if not query.strip():
                continue
            with console.status("分析中..."):
                result = await run_item_query(application, query.strip())
            console.print(Panel(result, title="分析结果", border_style="blue"))
            console.print()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        await application.close()
        console.print("\n[dim]再见！[/dim]")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """CSQAQ — CS2 饰品投资分析系统"""
    if ctx.invoked_subcommand is None:
        chat()
