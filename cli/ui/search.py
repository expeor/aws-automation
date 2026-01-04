"""
cli/ui/search.py - 도구 검색 엔진

100+ 서비스 대응을 위한 퍼지 검색 엔진
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class SearchResult:
    """검색 결과 항목"""

    tool_name: str
    tool_module: str
    category: str  # 폴더명 (CLI 명령어)
    category_display: str  # UI 표시용 이름
    category_desc: str
    description: str
    permission: str
    score: float  # 매칭 점수 (0-1)
    match_type: str  # exact, prefix, contains, fuzzy


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
        self._built = False

    def build_index(self, categories: list[dict[str, Any]]) -> None:
        """검색 인덱스 구축

        Args:
            categories: discover_categories() 결과
        """
        self._index.clear()
        self._chosung_index.clear()

        for cat in categories:
            cat_name = cat.get("name", "")
            cat_display = cat.get("display_name", cat_name)  # UI 표시용
            cat_desc = cat.get("description", cat_name)

            for tool in cat.get("tools", []):
                tool_name = tool.get("name", "")
                tool_module = tool.get("module", "")
                tool_desc = tool.get("description", "")
                permission = tool.get("permission", "read")

                # 인덱스 항목 생성
                idx = len(self._index)
                entry = {
                    "idx": idx,
                    "category": cat_name,
                    "category_display": cat_display,
                    "category_desc": cat_desc,
                    "tool_name": tool_name,
                    "tool_module": tool_module,
                    "description": tool_desc,
                    "permission": permission,
                    # 검색용 정규화 텍스트
                    "norm_name": normalize_text(tool_name),
                    "norm_desc": normalize_text(tool_desc),
                    "norm_cat": normalize_text(cat_name),
                    "norm_cat_desc": normalize_text(cat_desc),
                    # 초성
                    "chosung_name": get_chosung(tool_name),
                    "chosung_cat": get_chosung(cat_name),
                }

                self._index.append(entry)

                # 초성 인덱스 구축
                for chosung in [entry["chosung_name"], entry["chosung_cat"]]:
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
            query: 검색 쿼리
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
        norm_query = normalize_text(query)
        chosung_query = get_chosung(query)

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
                tool_module=entry["tool_module"],
                category=entry["category"],
                category_display=entry["category_display"],
                category_desc=entry["category_desc"],
                description=entry["description"],
                permission=entry["permission"],
                score=score,
                match_type=match_type,
            )
            for score, match_type, entry in results[:limit]
        ]

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
        4. 카테고리명 일치/포함 (0.75)
        5. 설명 포함 (0.6)
        6. 초성 매칭 (0.5)
        7. 부분 매칭 (0.3)
        """
        name = entry["norm_name"]
        cat = entry["norm_cat"]
        cat_desc = entry["norm_cat_desc"]
        desc = entry["norm_desc"]
        chosung_name = entry["chosung_name"]
        chosung_cat = entry["chosung_cat"]

        # 1. 도구명 정확히 일치
        if norm_query == name:
            return 1.0, "exact"

        # 2. 도구명 시작
        if name.startswith(norm_query):
            return 0.95, "prefix"

        # 3. 도구명 포함
        if norm_query in name:
            return 0.85, "contains"

        # 4. 카테고리명 일치/포함
        if norm_query == cat or norm_query in cat:
            return 0.75, "category"
        if norm_query in cat_desc:
            return 0.7, "category_desc"

        # 5. 설명 포함
        if norm_query in desc:
            return 0.6, "description"

        # 6. 초성 매칭 (한글 쿼리인 경우)
        if self._is_chosung_only(chosung_query):
            if chosung_query in chosung_name:
                return 0.5, "chosung"
            if chosung_query in chosung_cat:
                return 0.45, "chosung_cat"

        # 7. 단어별 부분 매칭
        query_words = norm_query.split()
        if len(query_words) > 1:
            match_count = sum(1 for w in query_words if w in name or w in desc)
            if match_count > 0:
                ratio = match_count / len(query_words)
                return 0.3 * ratio, "partial"

        return 0, ""

    def _is_chosung_only(self, text: str) -> bool:
        """초성만으로 구성되어 있는지 확인"""
        return all(
            not (char not in CHOSUNG_LIST and not char.isspace()) for char in text
        )

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
