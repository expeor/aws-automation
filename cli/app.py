"""
cli/app.py - 메인 CLI 엔트리포인트

Click 기반의 CLI 애플리케이션 진입점입니다.
플러그인 discovery 시스템을 통해 카테고리를 자동 등록합니다.

주요 기능:
    - 대화형 메인 메뉴 (서브명령 없이 실행 시)
    - 카테고리별 명령어 자동 등록 (discovery 기반)
    - 카테고리 별칭(aliases) 지원
    - 버전 정보 표시

명령어 구조:
    aa                      # 대화형 메인 메뉴
    aa --version            # 버전 표시
    aa <category>           # 카테고리별 도구 실행
    aa <category> --help    # 카테고리 도움말

    예시:
    aa ec2                  # EC2 관련 도구 실행
    aa ebs                  # EBS 관련 도구 실행
    aa s3                   # S3 관련 도구 실행

아키텍처:
    1. get_version(): core.config에서 버전 정보 로드
    2. cli(): Click 그룹 - 메인 엔트리포인트
    3. _register_category_commands(): discovery 기반 카테고리 자동 등록
       - discover_categories()로 플러그인 검색
       - 각 카테고리를 Click 명령어로 등록
       - 별칭(aliases)도 hidden 명령어로 등록

Usage:
    # 명령줄에서 직접 실행
    $ aa
    $ aa ec2
    $ aa --version

    # 모듈로 실행
    $ python -m cli.app
"""

import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (plugins 모듈 임포트를 위함)
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import click

# Keep lightweight, centralized logging config
# WARNING 레벨로 설정하여 INFO 로그가 도구 출력에 섞이지 않도록 함
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_version() -> str:
    """버전 문자열 반환

    version.txt 파일에서 버전을 읽어옴
    core.config.get_version()으로 대체됨
    """
    from core.config import get_version as config_get_version

    return config_get_version()


VERSION = get_version()


def _build_help_text() -> str:
    """help 텍스트 생성"""
    lines = [
        "AA - AWS Automation CLI",
        "",
        "AWS 리소스 분석, 비용 최적화, 보안 점검, 보고서 생성 등",
        "AWS 운영 업무를 자동화하는 CLI 도구입니다.",
        "",
        "\b",  # Click 줄바꿈 유지 마커
        "[기본 사용법]",
        "  aa              대화형 메뉴 (검색/탐색/즐겨찾기)",
        "  aa <서비스>     특정 서비스 도구 실행",
        "",
        "\b",
        "[주요 서비스 명령어]",
        "  aa ec2          EC2 인스턴스 분석",
        "  aa ebs          EBS 볼륨 분석 (미사용, 암호화 등)",
        "  aa s3           S3 버킷 분석 (퍼블릭, 암호화 등)",
        "  aa rds          RDS 데이터베이스 분석",
        "  aa iam          IAM 사용자/역할/액세스키 분석",
        "  aa vpc          VPC 네트워크 분석",
        "  aa report       정기 보고서 생성",
        "",
        "\b",
        "[예시]",
        "  aa ec2 --help   EC2 카테고리 도움말 표시",
        "  aa              -> 대화형 메뉴 진입",
        "                  -> 키워드 검색 (예: '미사용', 'rds')",
        "                  -> 번호로 도구 선택 후 실행",
    ]

    return "\n".join(lines)


@click.group(invoke_without_command=True)
@click.version_option(VERSION, prog_name="aa")
@click.pass_context
def cli(ctx):
    """AA - AWS Automation CLI"""
    if ctx.invoked_subcommand is None:
        # 서브 명령어 없이 실행된 경우 새로운 메인 메뉴 표시
        from cli.ui.main_menu import show_main_menu

        show_main_menu()


# help 텍스트 동적 설정
cli.help = _build_help_text()


def _register_category_commands():
    """discovery 기반 카테고리 명령어 자동 등록 (별칭 포함)

    AWS 서비스 카테고리(ec2, ebs 등)와 분석 카테고리(report 등) 모두 등록
    """
    try:
        from core.tools.discovery import discover_categories

        # AWS 서비스 카테고리 포함하여 모든 플러그인 로드
        categories = discover_categories(include_aws_services=True)
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Discovery 모듈 로드 실패: {e}")
        return
    except (OSError, ValueError) as e:
        logging.getLogger(__name__).warning(f"카테고리 검색 실패: {e}")
        return

    for cat in categories:
        name = cat.get("name", "")
        desc = cat.get("description", "")
        tools = cat.get("tools", [])
        aliases = cat.get("aliases", [])

        # 도구 목록으로 help 텍스트 생성 (\b로 줄바꿈 유지)
        tool_lines = [desc, "", "\b", "도구 목록:"]
        for tool in tools:
            perm = tool.get("permission", "read")
            perm_marker = " [!]" if perm in ("write", "delete") else ""
            tool_lines.append(f"  - {tool.get('name', '')}{perm_marker}")
        help_text = "\n".join(tool_lines)

        # 클로저로 카테고리명 캡처
        def make_cmd(category_name):
            @click.pass_context
            def cmd(ctx):
                from cli.flow import create_flow_runner

                runner = create_flow_runner()
                runner.run(category_name)

            return cmd

        # 메인 명령어 등록
        cmd_func = make_cmd(name)
        cmd_func.__doc__ = help_text
        cli.command(name=name)(cmd_func)

        # 별칭(aliases) 등록
        for alias in aliases:
            alias_cmd = make_cmd(name)  # 원본 카테고리명으로 실행
            alias_cmd.__doc__ = f"{desc} (→ {name})"
            cli.command(name=alias, hidden=True)(alias_cmd)


# 카테고리 명령어 자동 등록
_register_category_commands()


if __name__ == "__main__":
    cli()
