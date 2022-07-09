from .error_interpreter import explain_errors
from config import AuditorConfigMismatchesFound, AuditorConfigFilenamesConflict

if __name__ == "__main__":
    from rich.console import Console

    console = Console()
    console.print("\n[red] This is a test\n", justify="center")
    console.log(explain_errors(
        [AuditorConfigMismatchesFound(), AuditorConfigFilenamesConflict()]
    ))
