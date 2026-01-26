#!/usr/bin/env python
"""
AWS 리전 목록 업데이트 스크립트

사용법:
    python core/region/update_regions.py [--dry-run]

필요 권한:
    - AWS 자격증명 (어떤 계정이든 상관없음)
    - ec2:DescribeRegions

동작:
    - AWS API에서 최신 리전 목록 조회
    - core/region/data.py의 ALL_REGIONS 자동 업데이트
    - --dry-run: 변경 내용만 출력 (파일 수정 안함)
"""

import re
import sys
from datetime import datetime
from pathlib import Path

import boto3

# data.py 경로
DATA_FILE = Path(__file__).parent / "data.py"


def get_all_regions() -> list[str]:
    """EC2 API에서 모든 리전 목록 가져오기"""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    response = ec2.describe_regions(AllRegions=True)

    # Convert TypedDict region entries to strings
    regions = sorted([str(dict(r).get("RegionName", "")) for r in response.get("Regions", [])])
    return regions


def read_current_regions() -> list[str]:
    """data.py에서 현재 리전 목록 읽기"""
    content = DATA_FILE.read_text(encoding="utf-8")

    # ALL_REGIONS 배열 추출
    match = re.search(r"ALL_REGIONS\s*=\s*\[(.*?)\]", content, re.DOTALL)
    if not match:
        return []

    # 리전 문자열 추출
    regions = re.findall(r'"([a-z]{2}-[a-z]+-\d+)"', match.group(1))
    return regions


def update_data_file(regions: list[str]) -> None:
    """data.py의 ALL_REGIONS 업데이트"""
    content = DATA_FILE.read_text(encoding="utf-8")

    # 새 ALL_REGIONS 문자열 생성
    today = datetime.now().strftime("%Y-%m-%d")
    regions_str = ",\n".join(f'    "{r}"' for r in regions)
    new_block = f"""# 전체 AWS 리전 목록 ({today} 기준)
# 업데이트: core/region/update_regions.py 실행
ALL_REGIONS = [
{regions_str},
]"""

    # 기존 블록 교체
    pattern = r"# 전체 AWS 리전 목록.*?ALL_REGIONS\s*=\s*\[.*?\]"
    new_content = re.sub(pattern, new_block, content, flags=re.DOTALL)

    DATA_FILE.write_text(new_content, encoding="utf-8")


def main():
    dry_run = "--dry-run" in sys.argv

    print(f"# AWS 리전 목록 업데이트 ({datetime.now().strftime('%Y-%m-%d')})")
    print()

    # 현재 리전 조회
    current = read_current_regions()
    print(f"현재 등록된 리전: {len(current)}개")

    # AWS에서 최신 리전 조회
    try:
        latest = get_all_regions()
    except Exception as e:
        print(f"[ERROR] 리전 조회 실패: {e}")
        print("AWS 자격증명을 확인하세요.")
        return 1

    print(f"AWS 최신 리전: {len(latest)}개")
    print()

    # 변경 사항 확인
    added = set(latest) - set(current)
    removed = set(current) - set(latest)

    if not added and not removed:
        print("[OK] 변경 사항 없음")
        return 0

    if added:
        print(f"[+] 추가된 리전 ({len(added)}개):")
        for r in sorted(added):
            print(f"    - {r}")
        print()

    if removed:
        print(f"[-] 제거된 리전 ({len(removed)}개):")
        for r in sorted(removed):
            print(f"    - {r}")
        print()

    if dry_run:
        print("(--dry-run 모드: 파일 수정 안함)")
        return 0

    # 파일 업데이트
    update_data_file(latest)
    print(f"[OK] {DATA_FILE} 업데이트 완료")

    return 0


if __name__ == "__main__":
    exit(main())
