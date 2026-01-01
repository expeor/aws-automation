try:
    from cli.app import cli
except ModuleNotFoundError:
    # Fallback: ensure project root is on sys.path when invoked via console_script
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from cli.app import cli


def main():
    """Entry point for the aa CLI. Delegates to cli.app:cli."""
    cli()


if __name__ == "__main__":
    main()
