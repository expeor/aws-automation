"""
cli/ui/search.py - 도구 검색 엔진

100+ 서비스 대응을 위한 퍼지 검색 엔진
"""

import re
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz

# Fuzzy 검색 상수
FUZZY_MIN_SCORE = 80  # 최소 유사도 (%)
FUZZY_SCORE_BASE = 0.4  # fuzzy 기본 점수
FUZZY_SCORE_MAX = 0.7  # fuzzy 최대 점수
ALIAS_MATCH_SCORE = 0.80  # 별칭 매칭 점수


@dataclass
class SearchResult:
    """검색 결과 항목"""

    tool_name: str
    tool_name_en: str
    tool_module: str
    category: str  # 폴더명 (CLI 명령어)
    category_display: str  # UI 표시용 이름
    category_desc: str
    description: str
    description_en: str
    permission: str
    score: float  # 매칭 점수 (0-1)
    match_type: str  # exact, prefix, contains, fuzzy

    def get_name(self, lang: str = "ko") -> str:
        """언어에 따른 도구 이름 반환"""
        if lang == "en":
            return self.tool_name_en or self.tool_name
        return self.tool_name

    def get_description(self, lang: str = "ko") -> str:
        """언어에 따른 설명 반환"""
        if lang == "en":
            return self.description_en or self.description
        return self.description


# 한글 초성 매핑
CHOSUNG_LIST = [
    "ㄱ",
    "ㄲ",
    "ㄴ",
    "ㄷ",
    "ㄸ",
    "ㄹ",
    "ㅁ",
    "ㅂ",
    "ㅃ",
    "ㅅ",
    "ㅆ",
    "ㅇ",
    "ㅈ",
    "ㅉ",
    "ㅊ",
    "ㅋ",
    "ㅌ",
    "ㅍ",
    "ㅎ",
]


def get_chosung(text: str) -> str:
    """한글 문자열에서 초성 추출

    Args:
        text: 입력 문자열

    Returns:
        초성 문자열 (한글 아닌 문자는 그대로)
    """
    result = []
    for char in text:
        if "가" <= char <= "힣":
            # 한글 유니코드 계산
            code = ord(char) - ord("가")
            chosung_idx = code // (21 * 28)
            result.append(CHOSUNG_LIST[chosung_idx])
        else:
            result.append(char)
    return "".join(result)


def normalize_text(text: str) -> str:
    """검색용 텍스트 정규화

    - 소문자 변환
    - 특수문자 제거
    - 공백 정규화
    """
    text = text.lower()
    text = re.sub(r"[_\-\.]", " ", text)  # 구분자 → 공백
    text = re.sub(r"\s+", " ", text)  # 다중 공백 제거
    return text.strip()


class ToolSearchEngine:
    """도구 검색 엔진

    특징:
    - 점수 기반 매칭 (정확도순 정렬)
    - 한글 초성 검색 지원
    - 카테고리/도구명/설명 통합 검색
    """

    def __init__(self):
        self._index: list[dict[str, Any]] = []
        self._chosung_index: dict[str, list[int]] = {}  # 초성 → 인덱스 리스트
        self._alias_to_category: dict[str, str] = {}  # 별칭 → 카테고리명
        self._category_names: set[str] = set()  # 카테고리명 집합
        self._built = False

    def build_index(self, categories: list[dict[str, Any]]) -> None:
        """검색 인덱스 구축

        Args:
            categories: discover_categories() 결과
        """
        self._index.clear()
        self._chosung_index.clear()
        self._alias_to_category.clear()
        self._category_names.clear()

        # 우선순위 정렬: report > 기타 (중복 제거 시 report가 우선)
        def category_priority(cat: dict) -> tuple:
            name = cat.get("name", "")
            source = cat.get("_source", "")
            # reports 폴더 또는 report 카테고리 우선
            if source == "reports" or name == "report":
                return (0, name)
            return (1, name)

        sorted_categories = sorted(categories, key=category_priority)

        # 중복 도구명 제거를 위한 set
        seen_tool_names: set[str] = set()

        for cat in sorted_categories:
            cat_name = cat.get("name", "")
            cat_display = cat.get("display_name", cat_name)  # UI 표시용
            cat_desc = cat.get("description", cat_name)

            # 카테고리명 저장
            self._category_names.add(cat_name)
            self._category_names.add(normalize_text(cat_name))

            # 별칭 인덱스 구축
            aliases = cat.get("aliases", [])
            sub_services = cat.get("sub_services", [])
            all_aliases = aliases + sub_services

            for alias in all_aliases:
                norm_alias = normalize_text(alias)
                self._alias_to_category[norm_alias] = cat_name
                # 별칭도 카테고리명으로 취급
                self._category_names.add(norm_alias)

            for tool in cat.get("tools", []):
                tool_name = tool.get("name", "")
                tool_name_en = tool.get("name_en", "")

                # 중복 도구명 제거 (우선순위: report > analyzer)
                if tool_name in seen_tool_names:
                    continue
                seen_tool_names.add(tool_name)

                # ref 필드가 있으면 module 대신 사용 (reports/__init__.py 등에서 ref만 정의한 경우)
                tool_module = tool.get("module") or tool.get("ref", "")
                tool_desc = tool.get("description", "")
                tool_desc_en = tool.get("description_en", "")
                permission = tool.get("permission", "read")

                # 별칭 및 sub_services 정규화
                norm_aliases = [normalize_text(a) for a in all_aliases]

                # 인덱스 항목 생성
                idx = len(self._index)
                entry = {
                    "idx": idx,
                    "category": cat_name,
                    "category_display": cat_display,
                    "category_desc": cat_desc,
                    "tool_name": tool_name,
                    "tool_name_en": tool_name_en,
                    "tool_module": tool_module,
                    "description": tool_desc,
                    "description_en": tool_desc_en,
                    "permission": permission,
                    # 검색용 정규화 텍스트
                    "norm_name": normalize_text(tool_name),
                    "norm_name_en": normalize_text(tool_name_en),
                    "norm_desc": normalize_text(tool_desc),
                    "norm_desc_en": normalize_text(tool_desc_en),
                    "norm_cat": normalize_text(cat_name),
                    "norm_cat_desc": normalize_text(cat_desc),
                    # 별칭 (정규화)
                    "norm_aliases": norm_aliases,
                    # 초성
                    "chosung_name": get_chosung(tool_name),
                    "chosung_cat": get_chosung(cat_name),
                }

                self._index.append(entry)

                # 초성 인덱스 구축 (chosung_* 필드는 항상 str)
                chosung_name = str(entry["chosung_name"])
                chosung_cat = str(entry["chosung_cat"])
                for chosung in [chosung_name, chosung_cat]:
                    if chosung not in self._chosung_index:
                        self._chosung_index[chosung] = []
                    self._chosung_index[chosung].append(idx)

        self._built = True

    def search(
        self,
        query: str,
        limit: int = 15,
        category_filter: str | None = None,
    ) -> list[SearchResult]:
        """검색 실행

        Args:
            query: 검색 쿼리 (카테고리 필터 문법 지원: "ec2:미사용")
            limit: 최대 결과 수
            category_filter: 특정 카테고리만 검색 (선택)

        Returns:
            검색 결과 리스트 (점수 내림차순)
        """
        if not query or not query.strip():
            return []

        if not self._built:
            return []

        query = query.strip()

        # 카테고리 필터 문법 파싱 (ec2:미사용)
        parsed_filter, search_query = self._parse_query(query)
        if parsed_filter:
            category_filter = parsed_filter

        norm_query = normalize_text(search_query)
        chosung_query = get_chosung(search_query)

        results: list[tuple[float, str, dict]] = []  # (score, match_type, entry)

        for entry in self._index:
            # 카테고리 필터
            if category_filter and entry["category"] != category_filter:
                continue

            score, match_type = self._calculate_score(norm_query, chosung_query, entry)

            if score > 0:
                results.append((score, match_type, entry))

        # 점수 내림차순 정렬
        results.sort(key=lambda x: x[0], reverse=True)

        # SearchResult 변환
        return [
            SearchResult(
                tool_name=entry["tool_name"],
                tool_name_en=entry["tool_name_en"],
                tool_module=entry["tool_module"],
                category=entry["category"],
                category_display=entry["category_display"],
                category_desc=entry["category_desc"],
                description=entry["description"],
                description_en=entry["description_en"],
                permission=entry["permission"],
                score=score,
                match_type=match_type,
            )
            for score, match_type, entry in results[:limit]
        ]

    def _parse_query(self, query: str) -> tuple[str | None, str]:
        """카테고리 필터 문법 파싱

        Args:
            query: 검색 쿼리 (예: "ec2:미사용", "lb:unused")

        Returns:
            (카테고리명 또는 None, 검색어)
        """
        if ":" not in query:
            return None, query

        parts = query.split(":", 1)
        if len(parts) != 2:
            return None, query

        filter_part = parts[0].strip()
        search_part = parts[1].strip()

        # 필터 부분이 비어있으면 검색어만 사용
        if not filter_part:
            return None, search_part if search_part else query

        # 카테고리명 또는 별칭으로 변환
        resolved = self._resolve_category_filter(filter_part)
        if resolved:
            return resolved, search_part if search_part else ""

        # 필터가 유효하지 않으면 원본 쿼리 반환
        return None, query

    def _resolve_category_filter(self, name: str) -> str | None:
        """별칭을 카테고리명으로 변환

        Args:
            name: 카테고리명 또는 별칭

        Returns:
            실제 카테고리명 또는 None
        """
        norm_name = normalize_text(name)

        # 직접 카테고리명 매칭
        for entry in self._index:
            if entry["norm_cat"] == norm_name:
                return str(entry["category"])

        # 별칭 매칭
        if norm_name in self._alias_to_category:
            return self._alias_to_category[norm_name]

        return None

    def _calculate_score(
        self,
        norm_query: str,
        chosung_query: str,
        entry: dict,
    ) -> tuple[float, str]:
        """매칭 점수 계산

        우선순위:
        1. 도구명 정확히 일치 (1.0)
        2. 도구명 시작 (0.95)
        3. 도구명 포함 (0.85)
        4. 별칭 매칭 (0.80)
        5. 카테고리명 일치/포함 (0.75)
        6. Fuzzy 매칭 (0.4~0.7)
        7. 설명 포함 (0.6)
        8. 초성 매칭 (0.5)
        9. 부분 매칭 (0.3)
        """
        name = entry["norm_name"]
        name_en = entry.get("norm_name_en", "")
        cat = entry["norm_cat"]
        cat_desc = entry["norm_cat_desc"]
        desc = entry["norm_desc"]
        desc_en = entry.get("norm_desc_en", "")
        aliases = entry.get("norm_aliases", [])
        chosung_name = entry["chosung_name"]
        chosung_cat = entry["chosung_cat"]

        # 1. 도구명 정확히 일치 (한글/영어)
        if norm_query in (name, name_en):
            return 1.0, "exact"

        # 2. 도구명 시작 (한글/영어)
        if name.startswith(norm_query) or (name_en and name_en.startswith(norm_query)):
            return 0.95, "prefix"

        # 3. 도구명 포함 (한글/영어)
        if norm_query in name or (name_en and norm_query in name_en):
            return 0.85, "contains"

        # 4. 별칭 매칭
        for alias in aliases:
            if norm_query == alias or norm_query in alias or alias in norm_query:
                return ALIAS_MATCH_SCORE, "alias"

        # 5. 카테고리명 일치/포함
        if norm_query == cat or norm_query in cat:
            return 0.75, "category"
        if norm_query in cat_desc:
            return 0.7, "category_desc"

        # 6. Fuzzy 매칭 (도구명, 카테고리명, 별칭)
        fuzzy_score = self._calculate_fuzzy_score(norm_query, name)
        if fuzzy_score > 0:
            return fuzzy_score, "fuzzy"

        fuzzy_cat_score = self._calculate_fuzzy_score(norm_query, cat)
        if fuzzy_cat_score > 0:
            return fuzzy_cat_score * 0.9, "fuzzy_cat"  # 카테고리 fuzzy는 약간 낮게

        # 7. 설명 포함 (한글/영어)
        if norm_query in desc or (desc_en and norm_query in desc_en):
            return 0.6, "description"

        # 8. 초성 매칭 (한글 쿼리인 경우)
        if self._is_chosung_only(chosung_query):
            if chosung_query in chosung_name:
                return 0.5, "chosung"
            if chosung_query in chosung_cat:
                return 0.45, "chosung_cat"

        # 9. 단어별 부분 매칭 (한글/영어)
        query_words = norm_query.split()
        if len(query_words) > 1:
            match_count = sum(1 for w in query_words if w in name or w in desc or w in name_en or w in desc_en)
            if match_count > 0:
                ratio = match_count / len(query_words)
                return 0.3 * ratio, "partial"

        return 0, ""

    def _calculate_fuzzy_score(self, query: str, target: str) -> float:
        """Fuzzy 유사도 점수 계산

        rapidfuzz를 사용하여 유사도 계산 후 점수 범위(0.4~0.7)로 변환

        Args:
            query: 검색 쿼리 (정규화됨)
            target: 대상 텍스트 (정규화됨)

        Returns:
            매칭 점수 (0 또는 0.4~0.7)
        """
        if not query or not target:
            return 0

        # 짧은 쿼리는 fuzzy 검색 효과가 낮음
        if len(query) < 3:
            return 0

        # rapidfuzz로 유사도 계산 (0-100)
        ratio = fuzz.ratio(query, target)

        # 최소 유사도 미달
        if ratio < FUZZY_MIN_SCORE:
            return 0

        # 유사도를 점수 범위로 변환 (80~100 → 0.4~0.7)
        normalized = (ratio - FUZZY_MIN_SCORE) / (100 - FUZZY_MIN_SCORE)
        return FUZZY_SCORE_BASE + (FUZZY_SCORE_MAX - FUZZY_SCORE_BASE) * normalized

    def _is_chosung_only(self, text: str) -> bool:
        """초성만으로 구성되어 있는지 확인"""
        return all(not (char not in CHOSUNG_LIST and not char.isspace()) for char in text)

    def get_suggestions(self, prefix: str, limit: int = 5) -> list[str]:
        """자동완성 제안

        Args:
            prefix: 입력 접두사
            limit: 최대 제안 수

        Returns:
            제안 도구명 리스트
        """
        if not prefix or not self._built:
            return []

        norm_prefix = normalize_text(prefix)
        suggestions = []

        for entry in self._index:
            if entry["norm_name"].startswith(norm_prefix):
                suggestions.append(entry["tool_name"])
                if len(suggestions) >= limit:
                    break

        return suggestions

    def get_categories(self) -> list[str]:
        """인덱싱된 카테고리 목록"""
        categories = set()
        for entry in self._index:
            categories.add(entry["category"])
        return sorted(categories)

    def get_tool_count(self) -> int:
        """인덱싱된 도구 수"""
        return len(self._index)


# 전역 검색 엔진 인스턴스 (싱글톤)
_search_engine: ToolSearchEngine | None = None


def get_search_engine() -> ToolSearchEngine:
    """검색 엔진 싱글톤 인스턴스 반환"""
    global _search_engine
    if _search_engine is None:
        _search_engine = ToolSearchEngine()
    return _search_engine


def init_search_engine(categories: list[dict[str, Any]]) -> ToolSearchEngine:
    """검색 엔진 초기화 및 인덱스 구축

    Args:
        categories: discover_categories() 결과

    Returns:
        초기화된 검색 엔진
    """
    engine = get_search_engine()
    engine.build_index(categories)
    return engine
