#!/usr/bin/env python
"""
AWS 리전 목록 업데이트 스크립트

사용법:
    python core/region/update_regions.py

필요 권한:
    - AWS 자격증명 (어떤 계정이든 상관없음)
    - ec2:DescribeRegions

출력:
    - 최신 리전 목록 출력
    - 복사하여 코드에 붙여넣기용
"""

from datetime import datetime

import boto3


def get_all_regions() -> list[str]:
    """EC2 API에서 모든 리전 목록 가져오기"""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    response = ec2.describe_regions(AllRegions=True)

    regions = sorted([r["RegionName"] for r in response["Regions"]])
    return regions


def main():
    print(f"# AWS 리전 목록 업데이트 ({datetime.now().strftime('%Y-%m-%d')})")
    print()

    try:
        regions = get_all_regions()
    except Exception as e:
        print(f"❌ 리전 조회 실패: {e}")
        print("AWS 자격증명을 확인하세요.")
        return 1

    print(f"✅ 총 {len(regions)}개 리전 발견")
    print()

    # Python 리스트 형식으로 출력
    print("# internal/region/selector.py - FALLBACK_REGIONS")
    print("# internal/flow/steps/region.py - AWS_REGIONS")
    print()
    print("REGIONS = [")
    for region in regions:
        print(f'    "{region}",')
    print("]")
    print()

    # 새로 추가된 리전 확인용
    print("# 리전 상세 목록:")
    for region in regions:
        print(f"  - {region}")

    return 0


if __name__ == "__main__":
    exit(main())
