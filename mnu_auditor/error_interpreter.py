"""
Module must explain all errors with which the user may encounter, and guide what to do
"""
from typing import Sequence, Dict, Type, Literal
from rich.console import RenderableType

from config import AuditorConfigFilenamesConflict, AuditorConfigMismatchesFound
from driver_init import MNUDriverBinaryNotFound, MNUDriverSessionNotCreated

no_explanation_msg = "Have not explanation yet. Contact developers for help"

explanation_table: Dict[Type[Exception], Dict] = {
    AuditorConfigFilenamesConflict: {
        "text": "Getting this error means that the same filename was used when creating multiple 'configs'. Run [green]'python config.py -c'[/] for additional info about conflicts"
    },
    AuditorConfigMismatchesFound: {
        "text": "Getting this error means that the 'configs' files are not correct or are completely missing. Run [green]'python config.py -p'[/] for additional info about mismatches"
    },

    MNUDriverBinaryNotFound: {
        "text": "This means that you do not have WebDriver downloaded. Do it manually or run [green]'python main.py --update-driver'[/]"
    },
    MNUDriverSessionNotCreated: {
        "text": "During creating session between [yellow]Browser[/] and [yellow]WebDriver[/] error occurred. This is most likely due to a version mismatch.\nManually download [yellow]WebDriver[/] for your [yellow]Google Chrome[/] version, or update [yellow]Google Chrome[/] to newest version AND execute [green]'python main.py --update-driver'[/]"
    },

}


def is_error_have_explanation(e: Exception) -> bool:
    return type(e) in explanation_table


def explain_errors(es: Sequence[Exception], mode: Literal["Table", "Tree"] = "Tree") -> RenderableType:

    result: RenderableType = "[red]Wrong `mode`"

    if mode == "Table":
        from rich.table import Table
        from rich.box import ROUNDED

        output_table = Table(title="[yellow]Captured 'Errors'", padding=1, show_header=False, box=ROUNDED)
        output_table.add_column(no_wrap=True, style="red")
        output_table.add_column(no_wrap=False)

        for e in es:
            output_table.add_row(str(type(e)), explanation_table[type(e)]["text"] if is_error_have_explanation(e) else no_explanation_msg)

        result = output_table

    elif mode == "Tree":
        from rich.tree import Tree
        from rich.panel import Panel

        root = Tree("[yellow]Captured 'Errors'", highlight=True, guide_style="red")
        for e in es:
            root.add(
                Panel.fit(
                    explanation_table[type(e)]["text"] if is_error_have_explanation(e) else no_explanation_msg,
                    style="white",
                    title=f"[red]{str(type(e))}",
                    title_align="center"
                )
            )

        result = root

    return result
