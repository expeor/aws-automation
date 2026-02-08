"""
aa_cli/aa/cli/__main__.py - Python 모듈 실행 엔트리포인트

python -m aa_cli.aa.cli.app 실행 시 진입점
"""

from .app import cli

if __name__ == "__main__":
    cli()
