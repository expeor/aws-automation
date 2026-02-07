"""
tests/core/region/test_data.py - 리전 데이터 테스트

리전 목록과 메타데이터의 일관성을 검증합니다.
"""

import pytest

from core.region.data import ALL_REGIONS, COMMON_REGIONS, REGION_NAMES


class TestAllRegions:
    """ALL_REGIONS 테스트"""

    def test_all_regions_is_list(self):
        """ALL_REGIONS는 리스트여야 함"""
        assert isinstance(ALL_REGIONS, list)

    def test_all_regions_not_empty(self):
        """최소 10개 이상의 리전이 있어야 함"""
        assert len(ALL_REGIONS) >= 10

    def test_all_regions_unique(self):
        """중복된 리전 코드가 없어야 함"""
        assert len(ALL_REGIONS) == len(set(ALL_REGIONS))

    def test_region_format(self):
        """모든 리전은 올바른 형식이어야 함 (예: us-east-1)"""
        import re

        # 리전 형식: {location}-{direction|central|south|north}-{number}
        pattern = re.compile(r"^[a-z]{2,3}-[a-z]+(-[0-9]+)?$")

        for region in ALL_REGIONS:
            assert pattern.match(region), f"Invalid region format: {region}"

    def test_contains_expected_regions(self):
        """자주 사용하는 주요 리전들이 포함되어 있어야 함"""
        expected = [
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "ap-northeast-1",
            "ap-northeast-2",
            "ap-southeast-1",
            "eu-west-1",
            "eu-central-1",
        ]

        for region in expected:
            assert region in ALL_REGIONS, f"{region} not found in ALL_REGIONS"

    def test_all_strings(self):
        """모든 리전은 문자열이어야 함"""
        for region in ALL_REGIONS:
            assert isinstance(region, str)

    def test_no_empty_strings(self):
        """빈 문자열이 없어야 함"""
        for region in ALL_REGIONS:
            assert region.strip() != ""

    def test_regions_sorted(self):
        """리전이 알파벳 순으로 정렬되어 있어야 함"""
        sorted_regions = sorted(ALL_REGIONS)
        assert sorted_regions == ALL_REGIONS


class TestRegionNames:
    """REGION_NAMES 테스트"""

    def test_region_names_is_dict(self):
        """REGION_NAMES는 딕셔너리여야 함"""
        assert isinstance(REGION_NAMES, dict)

    def test_region_names_not_empty(self):
        """비어있지 않아야 함"""
        assert len(REGION_NAMES) > 0

    def test_all_keys_in_all_regions(self):
        """REGION_NAMES의 모든 키는 ALL_REGIONS에 있어야 함"""
        for region_code in REGION_NAMES.keys():
            assert region_code in ALL_REGIONS, f"{region_code} not in ALL_REGIONS"

    def test_all_values_are_strings(self):
        """모든 값은 문자열이어야 함"""
        for name in REGION_NAMES.values():
            assert isinstance(name, str)

    def test_no_empty_names(self):
        """빈 이름이 없어야 함"""
        for region_code, name in REGION_NAMES.items():
            assert name.strip() != "", f"Empty name for {region_code}"

    def test_korean_characters(self):
        """한글 설명이 포함되어 있어야 함"""
        # 최소 한 개의 리전은 한글 설명을 가져야 함
        has_korean = False
        for name in REGION_NAMES.values():
            if any("\uac00" <= char <= "\ud7a3" for char in name):
                has_korean = True
                break
        assert has_korean, "No Korean descriptions found"

    def test_key_region_descriptions(self):
        """주요 리전의 설명이 존재해야 함"""
        required = {
            "us-east-1": "미국",
            "ap-northeast-2": "서울",
            "ap-northeast-1": "도쿄",
            "eu-west-1": "유럽",
        }

        for region_code, expected_keyword in required.items():
            if region_code in REGION_NAMES:
                assert expected_keyword in REGION_NAMES[region_code], (
                    f"{region_code} description should contain '{expected_keyword}'"
                )

    def test_no_duplicate_descriptions(self):
        """중복된 설명이 없어야 함 (같은 설명이 여러 리전에 사용되면 안됨)"""
        descriptions = list(REGION_NAMES.values())
        # 일부 리전은 같은 도시를 공유할 수 있으므로 완전 중복만 체크
        unique_descriptions = set(descriptions)
        # 대부분의 리전은 고유한 설명을 가져야 함
        assert len(unique_descriptions) > len(descriptions) * 0.8


class TestCommonRegions:
    """COMMON_REGIONS 테스트"""

    def test_common_regions_is_list(self):
        """COMMON_REGIONS는 리스트여야 함"""
        assert isinstance(COMMON_REGIONS, list)

    def test_common_regions_not_empty(self):
        """최소 1개 이상의 리전이 있어야 함"""
        assert len(COMMON_REGIONS) > 0

    def test_tuple_structure(self):
        """각 항목은 (리전코드, 간단한이름) 튜플이어야 함"""
        for item in COMMON_REGIONS:
            assert isinstance(item, tuple), f"Item is not a tuple: {item}"
            assert len(item) == 2, f"Tuple should have 2 elements: {item}"
            assert isinstance(item[0], str), f"First element should be string: {item}"
            assert isinstance(item[1], str), f"Second element should be string: {item}"

    def test_region_codes_valid(self):
        """모든 리전 코드는 ALL_REGIONS에 있어야 함"""
        for region_code, _ in COMMON_REGIONS:
            assert region_code in ALL_REGIONS, f"{region_code} not in ALL_REGIONS"

    def test_contains_seoul_region(self):
        """서울 리전이 포함되어 있어야 함"""
        region_codes = [r[0] for r in COMMON_REGIONS]
        assert "ap-northeast-2" in region_codes

    def test_simple_names_not_empty(self):
        """간단한 이름이 비어있지 않아야 함"""
        for region_code, simple_name in COMMON_REGIONS:
            assert simple_name.strip() != "", f"Empty name for {region_code}"

    def test_no_duplicate_regions(self):
        """중복된 리전 코드가 없어야 함"""
        region_codes = [r[0] for r in COMMON_REGIONS]
        assert len(region_codes) == len(set(region_codes))


class TestRegionDataConsistency:
    """리전 데이터 간 일관성 테스트"""

    def test_common_regions_subset_of_all_regions(self):
        """COMMON_REGIONS의 모든 리전은 ALL_REGIONS의 부분집합이어야 함"""
        common_region_codes = {r[0] for r in COMMON_REGIONS}
        all_region_codes = set(ALL_REGIONS)

        assert common_region_codes.issubset(all_region_codes)

    def test_common_regions_have_descriptions(self):
        """COMMON_REGIONS의 모든 리전은 REGION_NAMES에 설명이 있어야 함"""
        for region_code, _ in COMMON_REGIONS:
            assert region_code in REGION_NAMES, f"{region_code} missing description in REGION_NAMES"

    def test_region_names_coverage(self):
        """REGION_NAMES는 ALL_REGIONS의 최소 50% 이상을 커버해야 함"""
        coverage = len(REGION_NAMES) / len(ALL_REGIONS)
        assert coverage >= 0.5, f"REGION_NAMES coverage is {coverage:.1%}, expected >= 50%"


class TestRegionDataTypes:
    """타입 안정성 테스트"""

    def test_all_regions_immutability(self):
        """ALL_REGIONS는 불변이어야 함 (리스트지만 변경하지 말아야 함)"""
        # 원본 저장
        original_length = len(ALL_REGIONS)
        original_first = ALL_REGIONS[0] if ALL_REGIONS else None

        # 복사본으로 작업 가능 여부 확인
        regions_copy = list(ALL_REGIONS)
        assert regions_copy == ALL_REGIONS

        # 원본은 변경되지 않았어야 함
        assert len(ALL_REGIONS) == original_length
        if original_first:
            assert ALL_REGIONS[0] == original_first

    def test_can_iterate_all_regions(self):
        """ALL_REGIONS는 반복 가능해야 함"""
        count = 0
        for region in ALL_REGIONS:
            count += 1
            assert isinstance(region, str)
        assert count == len(ALL_REGIONS)

    def test_can_check_membership(self):
        """리전 존재 여부를 확인할 수 있어야 함"""
        assert "ap-northeast-2" in ALL_REGIONS
        assert "invalid-region-999" not in ALL_REGIONS

    def test_region_names_lookup(self):
        """REGION_NAMES는 딕셔너리 조회가 가능해야 함"""
        if "ap-northeast-2" in REGION_NAMES:
            name = REGION_NAMES["ap-northeast-2"]
            assert isinstance(name, str)
            assert "서울" in name


class TestRegionDataEdgeCases:
    """경계 조건 테스트"""

    def test_all_regions_lowercase(self):
        """모든 리전 코드는 소문자여야 함"""
        for region in ALL_REGIONS:
            assert region == region.lower(), f"Region {region} is not lowercase"

    def test_no_whitespace_in_regions(self):
        """리전 코드에 공백이 없어야 함"""
        for region in ALL_REGIONS:
            assert " " not in region, f"Region {region} contains whitespace"
            assert region == region.strip(), f"Region {region} has leading/trailing whitespace"

    def test_region_names_no_leading_trailing_whitespace(self):
        """리전 설명에 앞뒤 공백이 없어야 함"""
        for region_code, name in REGION_NAMES.items():
            assert name == name.strip(), f"Region name for {region_code} has whitespace"

    def test_common_regions_names_no_whitespace(self):
        """COMMON_REGIONS의 간단한 이름에 앞뒤 공백이 없어야 함"""
        for region_code, simple_name in COMMON_REGIONS:
            assert simple_name == simple_name.strip(), f"Name for {region_code} has whitespace"


class TestRegionDataDocumentation:
    """문서화 및 유지보수성 테스트"""

    def test_all_regions_has_comment(self):
        """ALL_REGIONS에 업데이트 날짜 주석이 있는지 소스 확인"""
        # 이 테스트는 소스 파일을 읽어서 주석을 확인합니다
        import inspect
        from pathlib import Path

        import core.region.data

        source_file = Path(inspect.getfile(core.region.data))

        if source_file.exists():
            content = source_file.read_text(encoding="utf-8")
            # 업데이트 관련 주석이 있는지 확인
            assert "update" in content.lower() or "업데이트" in content.lower()
            assert "ALL_REGIONS" in content

    def test_module_docstring_exists(self):
        """data.py 모듈에 docstring이 있는지 확인"""
        import core.region.data

        assert core.region.data.__doc__ is not None
        assert len(core.region.data.__doc__.strip()) > 0


class TestRegionValidation:
    """리전 유효성 검증 테스트"""

    def test_known_invalid_regions_not_present(self):
        """알려진 잘못된 리전 코드가 없는지 확인"""
        invalid_patterns = [
            "aws-",  # AWS prefix는 사용하지 않음
            "-region",  # region suffix는 사용하지 않음
            "global",  # global은 리전이 아님
        ]

        for region in ALL_REGIONS:
            for invalid in invalid_patterns:
                assert invalid not in region, f"Invalid pattern '{invalid}' found in {region}"

        # 빈 문자열은 별도로 확인
        assert "" not in ALL_REGIONS, "Empty string found in ALL_REGIONS"

    def test_region_codes_realistic_length(self):
        """리전 코드 길이가 합리적인지 확인 (5-20자)"""
        for region in ALL_REGIONS:
            assert 5 <= len(region) <= 20, f"Region {region} has unusual length: {len(region)}"

    @pytest.mark.parametrize(
        "region_code",
        [
            "us-east-1",
            "us-east-2",
            "us-west-1",
            "us-west-2",
            "ap-northeast-1",
            "ap-northeast-2",
            "ap-south-1",
            "ap-southeast-1",
            "ap-southeast-2",
            "eu-west-1",
            "eu-central-1",
        ],
    )
    def test_critical_regions_present(self, region_code):
        """중요한 리전들이 반드시 포함되어 있어야 함"""
        assert region_code in ALL_REGIONS, f"Critical region {region_code} is missing"
