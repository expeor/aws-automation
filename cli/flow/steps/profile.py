# internal/flow/steps/profile.py
"""
프로파일 선택 Step

AWS 인증 프로파일을 선택하고 Provider를 생성.
2단계 선택: 인증 타입 → 프로파일
"""


from rich.console import Console

from ..context import ExecutionContext, ProviderKind

console = Console()

# 인증 타입 정의 (표시 순서대로)
AUTH_TYPE_INFO = {
    ProviderKind.SSO_SESSION: {
        "name": "SSO 세션",
        "description": "멀티 계정, 동적 역할",
        "badge": " (권장)",
    },
    ProviderKind.SSO_PROFILE: {
        "name": "SSO 프로파일",
        "description": "단일 계정, 고정 역할",
        "badge": "",
    },
    ProviderKind.STATIC_CREDENTIALS: {
        "name": "IAM Access Key",
        "description": "정적 자격 증명",
        "badge": "",
    },
}


class ProfileStep:
    """프로파일 선택 Step

    2단계 선택 방식:
    1. 인증 타입 선택 (SSO 세션, IAM Access Key 등)
    2. 해당 타입의 프로파일 선택 (1개면 자동 선택)
    """

    def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        """프로파일 선택 실행

        Args:
            ctx: 실행 컨텍스트

        Returns:
            업데이트된 컨텍스트
        """
        # 사용 가능한 프로파일 수집
        profiles = self._collect_profiles()

        if not profiles:
            console.print("[red]! 사용 가능한 AWS 프로파일이 없습니다.[/red]")
            console.print(
                "[yellow]* 'aws configure' 또는 " "'aws configure sso'를 실행해주세요.[/yellow]"
            )
            raise RuntimeError("프로파일 없음")

        # 프로파일이 1개면 자동 선택
        if len(profiles) == 1:
            selected = profiles[0]
            console.print()
            console.print(f"[dim]프로파일:[/dim] {selected['name']} ({selected['type']})")
            return self._handle_selected_profile(ctx, selected)

        # 타입별로 그룹핑
        profiles_by_type = self._group_by_type(profiles)

        # 사용 가능한 타입이 1개면 타입 선택 생략 (그룹이 없을 때만)
        from core.tools.history import ProfileGroupsManager

        group_manager = ProfileGroupsManager()
        saved_groups = group_manager.get_all()

        available_types = [k for k, v in profiles_by_type.items() if v]
        selected_type: ProviderKind | str
        if len(available_types) == 1 and not saved_groups:
            selected_type = available_types[0]
            type_info = AUTH_TYPE_INFO.get(selected_type, {})
            name = type_info.get("name", selected_type)
            console.print()
            console.print(f"[dim]인증:[/dim] {name}")
        else:
            # 1단계: 인증 타입 선택 (또는 그룹 선택)
            selected_type = self._select_auth_type(profiles_by_type)

        # 그룹 선택인 경우
        if isinstance(selected_type, str) and selected_type.startswith("group:"):
            group_name = selected_type[6:]  # "group:" 제거
            return self._handle_group_selection(ctx, group_name, profiles)

        # 2단계: 프로파일 선택
        # At this point selected_type is guaranteed to be ProviderKind (not "group:*" string)
        assert isinstance(selected_type, ProviderKind)
        type_profiles = profiles_by_type[selected_type]
        selected = self._select_profile_in_type(type_profiles, selected_type)

        # 다중 선택인 경우 (list 반환)
        if isinstance(selected, list):
            return self._handle_multi_profile_flow(ctx, selected)

        return self._handle_selected_profile(ctx, selected)

    def _group_by_type(self, profiles: list) -> dict[ProviderKind, list[dict]]:
        """프로파일을 타입별로 그룹핑"""
        grouped: dict[ProviderKind, list[dict]] = {
            ProviderKind.SSO_SESSION: [],
            ProviderKind.SSO_PROFILE: [],
            ProviderKind.STATIC_CREDENTIALS: [],
        }
        for p in profiles:
            kind = p.get("kind")
            if kind in grouped:
                grouped[kind].append(p)
        return grouped

    def _select_auth_type(
        self, profiles_by_type: dict[ProviderKind, list[dict]]
    ) -> ProviderKind | str:
        """인증 타입 선택 (1단계)

        Returns:
            ProviderKind: 선택된 인증 타입
            str: 프로파일 그룹 이름 (그룹 선택 시 "group:그룹명" 형태)
        """
        from cli.ui.console import print_box_end, print_box_line, print_box_start
        from core.tools.history import ProfileGroupsManager

        # 저장된 프로파일 그룹 확인
        group_manager = ProfileGroupsManager()
        saved_groups = group_manager.get_all()

        # 표시 순서 (AUTH_TYPE_INFO 키 순서)
        type_order = list(AUTH_TYPE_INFO.keys())
        available_types = []

        for kind in type_order:
            type_profiles = profiles_by_type.get(kind, [])
            if type_profiles:
                available_types.append((kind, type_profiles))

        print_box_start("인증 방식 선택")

        menu_idx = 1

        # 저장된 그룹이 있으면 맨 위에 표시
        if saved_groups:
            print_box_line(
                f" {menu_idx}) [cyan]★ 저장된 프로파일 그룹[/cyan] [dim]({len(saved_groups)}개)[/dim]"
            )
            menu_idx += 1
            print_box_line(" ────────────────────────")

        # 선택지 표시
        for kind, type_profiles in available_types:
            info = AUTH_TYPE_INFO[kind]
            count = len(type_profiles)
            print_box_line(
                f" {menu_idx}) {info['name']}{info['badge']} [dim]({count}개)[/dim]"
            )
            menu_idx += 1

        print_box_end()

        total_options = (1 if saved_groups else 0) + len(available_types)

        # 번호 입력
        while True:
            choice = console.input("> ").strip()

            if not choice:
                continue

            try:
                idx = int(choice)
                if not 1 <= idx <= total_options:
                    console.print(f"[dim]1-{total_options} 범위[/dim]")
                    continue

                # 그룹 선택
                if saved_groups and idx == 1:
                    selected_group = self._select_profile_group(saved_groups)
                    if selected_group:
                        return f"group:{selected_group.name}"
                    # 그룹 선택 취소 시 다시 표시
                    return self._select_auth_type(profiles_by_type)

                # 인증 타입 선택
                type_idx = idx - (1 if saved_groups else 0) - 1
                selected_kind, _ = available_types[type_idx]
                info = AUTH_TYPE_INFO[selected_kind]
                console.print(f"[dim]인증:[/dim] {info['name']}")
                return selected_kind

            except ValueError:
                console.print("[dim]숫자 입력[/dim]")

    def _select_profile_group(self, groups):
        """프로파일 그룹 선택"""
        from cli.ui.console import print_box_end, print_box_line, print_box_start

        kind_labels = {"sso_profile": "SSO", "static": "Key"}

        print_box_start("프로파일 그룹 선택")

        for idx, g in enumerate(groups, 1):
            kind_label = kind_labels.get(g.kind, g.kind)
            profiles_preview = ", ".join(g.profiles[:2])
            if len(g.profiles) > 2:
                profiles_preview += f" 외 {len(g.profiles) - 2}개"
            print_box_line(
                f" {idx}) [{kind_label}] {g.name} [dim]({profiles_preview})[/dim]"
            )

        print_box_line("")
        print_box_line(" [dim]0) 뒤로[/dim]")
        print_box_end()

        while True:
            choice = console.input("> ").strip()

            if not choice:
                continue

            if choice == "0":
                return None

            try:
                idx = int(choice)
                if 1 <= idx <= len(groups):
                    selected = groups[idx - 1]
                    console.print(f"[dim]그룹:[/dim] {selected.name}")
                    return selected
                console.print(f"[dim]0-{len(groups)} 범위[/dim]")
            except ValueError:
                console.print("[dim]숫자 입력[/dim]")

    def _select_profile_in_type(
        self, profiles: list[dict], kind: ProviderKind
    ) -> dict | list[dict]:
        """특정 타입 내에서 프로파일 선택 (2단계)

        Returns:
            dict: 단일 선택 시
            List[dict]: 다중 선택 시 (STATIC_CREDENTIALS only)
        """
        from cli.ui.console import print_box_end, print_box_line, print_box_start

        # 프로파일이 1개면 자동 선택
        if len(profiles) == 1:
            selected = profiles[0]
            console.print()
            console.print(f"[dim]프로파일:[/dim] {selected['name']}")
            return selected

        # 이름순 정렬
        sorted_profiles = sorted(profiles, key=lambda x: x["name"].lower())

        info = AUTH_TYPE_INFO.get(kind, {})
        name = info.get("name", "프로파일")

        # STATIC_CREDENTIALS, SSO_PROFILE은 다중 선택 옵션 제공
        supports_multi = kind in (
            ProviderKind.STATIC_CREDENTIALS,
            ProviderKind.SSO_PROFILE,
        )
        if supports_multi and len(sorted_profiles) > 1:
            console.print()
            console.print("[dim]1) 단일 선택  2) 다중 선택[/dim]")

            while True:
                mode = console.input("> ").strip()
                if mode == "1":
                    break
                elif mode == "2":
                    return self._select_multi_profiles(sorted_profiles)
                elif mode:
                    console.print("[dim]1 또는 2 입력[/dim]")

        # 대규모 프로파일 지원 (20개 이상이면 검색/페이지네이션)
        if len(sorted_profiles) > 20:
            return self._select_single_profile_large(sorted_profiles)

        print_box_start(f"{name} 선택 ({len(sorted_profiles)}개)")

        # 2열 레이아웃
        half = (len(sorted_profiles) + 1) // 2
        for i in range(half):
            left_idx = i + 1
            left = sorted_profiles[i]
            left_str = f"{left_idx:>2}) {left['name'][:24]:<24}"

            if i + half < len(sorted_profiles):
                right_idx = i + half + 1
                right = sorted_profiles[i + half]
                right_str = f"{right_idx:>2}) {right['name'][:24]}"
                print_box_line(f" {left_str}  {right_str}")
            else:
                print_box_line(f" {left_str}")

        print_box_end()

        # 번호 입력
        while True:
            choice = console.input("> ").strip()

            if not choice:
                continue

            try:
                idx = int(choice)
                if 1 <= idx <= len(sorted_profiles):
                    selected = sorted_profiles[idx - 1]
                    console.print(f"[dim]프로파일:[/dim] {selected['name']}")
                    return dict(selected)
                console.print(f"[dim]1-{len(sorted_profiles)} 범위[/dim]")
            except ValueError:
                console.print("[dim]숫자 입력[/dim]")

    def _select_single_profile_large(self, profiles: list[dict]) -> dict:
        """대규모 프로파일에서 단일 선택 (검색/페이지네이션 지원)"""
        from cli.ui.console import print_box_end, print_box_line, print_box_start

        PAGE_SIZE = 20
        search_filter = ""
        current_page = 0

        def get_filtered() -> list[tuple]:
            if not search_filter:
                return list(enumerate(profiles))
            return [
                (i, p)
                for i, p in enumerate(profiles)
                if search_filter.lower() in p["name"].lower()
            ]

        def display():
            nonlocal current_page
            filtered = get_filtered()
            total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
            current_page = min(current_page, total_pages - 1)

            start_idx = current_page * PAGE_SIZE
            end_idx = min(start_idx + PAGE_SIZE, len(filtered))
            page_items = filtered[start_idx:end_idx]

            title = f"프로파일 ({len(profiles)}개)"
            if search_filter:
                title += f" - 검색: {search_filter} ({len(filtered)}개)"

            print_box_start(title)

            # 2열 레이아웃
            half = (len(page_items) + 1) // 2
            for i in range(half):
                left_display_idx = start_idx + i + 1
                left = page_items[i][1]
                left_str = f"{left_display_idx:>3}) {left['name'][:22]:<22}"

                if i + half < len(page_items):
                    right_display_idx = start_idx + i + half + 1
                    right = page_items[i + half][1]
                    right_str = f"{right_display_idx:>3}) {right['name'][:22]}"
                    print_box_line(f" {left_str}  {right_str}")
                else:
                    print_box_line(f" {left_str}")

            print_box_line()
            nav = ""
            if total_pages > 1:
                nav = f"p{current_page + 1}/{total_pages} </>: 이동 | "
            print_box_line(f"[dim]{nav}/검색 | c: 해제[/dim]")
            print_box_end()

        display()

        while True:
            choice = console.input("> ").strip()

            if not choice:
                continue

            # 페이지 이동
            if choice in ["<", "p"]:
                if current_page > 0:
                    current_page -= 1
                display()
                continue

            if choice == ">":
                filtered = get_filtered()
                total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
                if current_page < total_pages - 1:
                    current_page += 1
                display()
                continue

            # 검색 필터
            if choice.startswith("/"):
                search_filter = choice[1:].strip()
                current_page = 0
                display()
                continue

            # 필터 해제
            if choice.lower() == "c":
                search_filter = ""
                current_page = 0
                display()
                continue

            # 번호 선택
            try:
                idx = int(choice)
                filtered = get_filtered()
                if 1 <= idx <= len(filtered):
                    orig_idx, _ = filtered[idx - 1]
                    selected = profiles[orig_idx]
                    console.print(f"[dim]프로파일:[/dim] {selected['name']}")
                    return dict(selected)
                console.print(f"[dim]1-{len(filtered)} 범위[/dim]")
            except ValueError:
                console.print("[dim]숫자 또는 /검색어[/dim]")

    def _select_multi_profiles(self, profiles: list[dict]) -> list[dict]:
        """다중 프로파일 선택 (STATIC_CREDENTIALS용)"""
        import fnmatch

        from cli.ui.console import print_box_end, print_box_line, print_box_start

        PAGE_SIZE = 20
        selected_indices: set[int] = set()
        search_filter = ""
        current_page = 0

        def get_filtered_profiles() -> list[tuple]:
            if not search_filter:
                return list(enumerate(profiles))
            return [
                (i, p)
                for i, p in enumerate(profiles)
                if search_filter.lower() in p["name"].lower()
            ]

        def display_profiles():
            nonlocal current_page
            filtered = get_filtered_profiles()
            total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
            current_page = min(current_page, total_pages - 1)

            start_idx = current_page * PAGE_SIZE
            end_idx = min(start_idx + PAGE_SIZE, len(filtered))
            page_items = filtered[start_idx:end_idx]

            title = f"다중 선택 ({len(profiles)}개)"
            if search_filter:
                title += f" - {search_filter} ({len(filtered)}개)"

            print_box_start(title)

            # 2열 레이아웃
            half = (len(page_items) + 1) // 2
            for i in range(half):
                left_display_idx = start_idx + i + 1
                orig_idx_l, left = page_items[i]
                left_check = "v" if orig_idx_l in selected_indices else " "
                left_str = f"{left_display_idx:>2}){left_check}{left['name'][:20]:<20}"

                if i + half < len(page_items):
                    right_display_idx = start_idx + i + half + 1
                    orig_idx_r, right = page_items[i + half]
                    right_check = "v" if orig_idx_r in selected_indices else " "
                    right_str = (
                        f"{right_display_idx:>2}){right_check}{right['name'][:20]}"
                    )
                    print_box_line(f" {left_str}  {right_str}")
                else:
                    print_box_line(f" {left_str}")

            print_box_line()
            nav = f"p{current_page + 1}/{total_pages} " if total_pages > 1 else ""
            print_box_line(f"[dim]{nav}a: 전체 | d: 완료 ({len(selected_indices)}개)[/dim]")
            print_box_end()

        display_profiles()

        while True:
            choice = console.input("> ").strip()

            if not choice:
                continue

            choice_lower = choice.lower()

            if choice_lower == "d":
                if not selected_indices:
                    console.print("[dim]최소 1개 선택[/dim]")
                    continue
                break

            if choice_lower == "a":
                filtered = get_filtered_profiles()
                if len(selected_indices) == len(filtered):
                    selected_indices.clear()
                else:
                    for orig_idx, _ in filtered:
                        selected_indices.add(orig_idx)
                display_profiles()
                continue

            if choice_lower == "c":
                search_filter = ""
                current_page = 0
                display_profiles()
                continue

            if choice in ["<", "p"]:
                if current_page > 0:
                    current_page -= 1
                display_profiles()
                continue

            if choice == ">":
                filtered = get_filtered_profiles()
                total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
                if current_page < total_pages - 1:
                    current_page += 1
                display_profiles()
                continue

            if choice.startswith("/"):
                search_filter = choice[1:].strip()
                current_page = 0
                display_profiles()
                continue

            if "*" in choice or "?" in choice:
                pattern = choice.lower()
                filtered = get_filtered_profiles()
                for orig_idx, p in filtered:
                    if fnmatch.fnmatch(p["name"].lower(), pattern):
                        selected_indices.add(orig_idx)
                display_profiles()
                continue

            if "-" in choice and not choice.startswith("-"):
                try:
                    filtered = get_filtered_profiles()
                    parts = choice.split("-")
                    if len(parts) == 2:
                        start, end = int(parts[0]), int(parts[1])
                        if start <= end:
                            for display_idx in range(start, end + 1):
                                if 1 <= display_idx <= len(filtered):
                                    orig_idx, _ = filtered[display_idx - 1]
                                    selected_indices.add(orig_idx)
                            display_profiles()
                            continue
                except ValueError:
                    pass

            try:
                filtered = get_filtered_profiles()
                nums = [int(n) for n in choice.replace(",", " ").split()]
                for num in nums:
                    if 1 <= num <= len(filtered):
                        orig_idx, _ = filtered[num - 1]
                        if orig_idx in selected_indices:
                            selected_indices.discard(orig_idx)
                        else:
                            selected_indices.add(orig_idx)
                display_profiles()
            except ValueError:
                console.print("[dim]숫자, 범위, 패턴 입력[/dim]")

        selected = [profiles[i] for i in sorted(selected_indices)]
        console.print(f"[dim]{len(selected)}개 선택됨[/dim]")
        return selected

    def _get_profile_description(self, profile: dict) -> str:
        """프로파일 유형별 설명 반환"""
        kind = profile["kind"]
        if kind == ProviderKind.SSO_SESSION:
            return "멀티 계정, 동적 역할 선택"
        elif kind == ProviderKind.SSO_PROFILE:
            if profile.get("is_legacy"):
                return "단일 계정 (구버전 설정)"
            return "단일 계정, 고정 역할"
        elif kind == ProviderKind.STATIC_CREDENTIALS:
            return "IAM Access Key"
        return ""

    def _handle_selected_profile(
        self, ctx: ExecutionContext, selected: dict
    ) -> ExecutionContext:
        """선택된 프로파일에 따라 적절한 Flow 처리"""
        kind = selected["kind"]

        if kind == ProviderKind.SSO_SESSION:
            return self._handle_sso_session_flow(ctx, [selected])
        elif kind == ProviderKind.SSO_PROFILE:
            return self._handle_sso_profile_flow(ctx, [selected])
        else:  # STATIC_CREDENTIALS
            return self._handle_static_single_flow(ctx, selected)

    def _handle_static_single_flow(
        self, ctx: ExecutionContext, selected: dict
    ) -> ExecutionContext:
        """Static 단일 프로파일 처리"""
        ctx.provider_kind = selected["kind"]
        ctx.profile_name = selected["name"]
        ctx.profiles = [selected["name"]]
        return ctx

    def _handle_group_selection(
        self, ctx: ExecutionContext, group_name: str, all_profiles: list
    ) -> ExecutionContext:
        """프로파일 그룹 선택 처리

        그룹에 저장된 프로파일 이름으로 실제 프로파일 정보를 찾아서
        멀티 프로파일 플로우로 진입합니다.
        """
        from core.tools.history import ProfileGroupsManager

        manager = ProfileGroupsManager()
        group = manager.get_by_name(group_name)

        if not group:
            console.print(f"[red]그룹을 찾을 수 없습니다: {group_name}[/red]")
            raise RuntimeError("그룹 없음")

        # 그룹에 저장된 프로파일 이름으로 실제 프로파일 정보 찾기
        profile_names = set(group.profiles)
        matched_profiles = []

        for p in all_profiles:
            if p["name"] in profile_names:
                matched_profiles.append(p)

        if not matched_profiles:
            console.print(f"[red]그룹 '{group_name}'의 프로파일을 찾을 수 없습니다.[/red]")
            console.print("[dim]프로파일이 삭제되었거나 이름이 변경되었을 수 있습니다.[/dim]")
            raise RuntimeError("프로파일 없음")

        # 찾지 못한 프로파일 경고
        found_names = {p["name"] for p in matched_profiles}
        missing = profile_names - found_names
        if missing:
            console.print(f"[yellow]일부 프로파일을 찾을 수 없음: {', '.join(missing)}[/yellow]")

        console.print(f"[dim]그룹 '{group_name}': {len(matched_profiles)}개 프로파일[/dim]")

        # 멀티 프로파일 플로우로 진입
        return self._handle_multi_profile_flow(ctx, matched_profiles)

    def _handle_multi_profile_flow(
        self, ctx: ExecutionContext, selected_profiles: list[dict]
    ) -> ExecutionContext:
        """다중 프로파일 처리 (Static, SSO Profile)"""
        ctx.provider_kind = selected_profiles[0]["kind"]
        ctx.profile_name = selected_profiles[0]["name"]
        ctx.profiles = [p["name"] for p in selected_profiles]

        console.print(f"[dim]{len(ctx.profiles)}개 프로파일 순차 실행[/dim]")
        return ctx

    def _handle_sso_session_flow(
        self, ctx: ExecutionContext, profiles: list
    ) -> ExecutionContext:
        """SSO Session 인증 Flow 처리 (멀티 계정)

        SSO Session은 동적으로 계정/역할을 선택할 수 있음.
        """
        selected = profiles[0]  # 테이블에서 이미 선택됨

        # Provider 생성
        ctx.profile_name = selected["name"]
        ctx.provider_kind = selected["kind"]
        ctx.provider = self._create_provider(selected)

        # 인증 수행
        self._authenticate(ctx)

        # 계정 목록 로드 (SSO Session은 멀티 계정)
        ctx.accounts = self._load_accounts(ctx)

        return ctx

    def _handle_sso_profile_flow(
        self, ctx: ExecutionContext, profiles: list
    ) -> ExecutionContext:
        """SSO Profile 인증 Flow 처리 (단일 계정)

        SSO Profile은 계정/역할이 고정되어 있음 (sso_account_id, sso_role_name).
        계정/역할 선택 없이 바로 리전 선택으로 진행.
        """
        selected = profiles[0]  # 테이블에서 이미 선택됨

        # Provider 생성
        ctx.profile_name = selected["name"]
        ctx.provider_kind = selected["kind"]
        ctx.provider = self._create_provider(selected)

        # 인증 수행
        self._authenticate(ctx)

        return ctx

    def _collect_profiles(self) -> list:
        """사용 가능한 프로파일 수집"""
        profiles = []

        try:
            from core.auth import (
                detect_provider_type,
                list_profiles,
                list_sso_sessions,
                load_config,
            )
            from core.auth.types import ProviderType

            # 설정 로드
            config_data = load_config()

            # SSO 세션
            for session_name in list_sso_sessions():
                profiles.append(
                    {
                        "name": session_name,
                        "type": "SSO 세션",
                        "kind": ProviderKind.SSO_SESSION,
                        "config": {"session_name": session_name},
                        "is_legacy": False,
                    }
                )

            # 일반 프로파일
            for profile_name in list_profiles():
                # AWSProfile 객체를 가져와서 detect_provider_type에 전달
                profile_config = config_data.profiles.get(profile_name)
                if not profile_config:
                    continue

                provider_type = detect_provider_type(profile_config)

                if provider_type == ProviderType.SSO_PROFILE:
                    has_sso_session = profile_config.sso_session
                    has_start_url = profile_config.sso_start_url
                    is_legacy = not has_sso_session and has_start_url
                    profiles.append(
                        {
                            "name": profile_name,
                            "type": "SSO 프로파일",
                            "kind": ProviderKind.SSO_PROFILE,
                            "config": {"profile_name": profile_name},
                            "is_legacy": is_legacy,
                        }
                    )
                elif provider_type == ProviderType.STATIC_CREDENTIALS:
                    profiles.append(
                        {
                            "name": profile_name,
                            "type": "Access Key",
                            "kind": ProviderKind.STATIC_CREDENTIALS,
                            "config": {"profile_name": profile_name},
                            "is_legacy": False,
                        }
                    )
                # 그 외 타입(AssumeRole 등)은 지원하지 않음 - skip
        except ImportError:
            console.print("[yellow]* internal.auth 모듈 로드 실패[/yellow]")

        return profiles

    def _create_provider(self, profile: dict):
        """선택된 프로파일에 맞는 Provider 생성"""
        from core.auth import (
            SSOProfileConfig,
            SSOProfileProvider,
            SSOSessionConfig,
            SSOSessionProvider,
            StaticCredentialsConfig,
            StaticCredentialsProvider,
            load_config,
        )

        kind = profile["kind"]
        config_data = load_config()

        if kind == ProviderKind.SSO_SESSION:
            session_name = profile["name"]
            session_config = config_data.sessions.get(session_name)
            if not session_config:
                raise ValueError(f"SSO 세션 설정을 찾을 수 없음: {session_name}")

            return SSOSessionProvider(
                SSOSessionConfig(
                    session_name=session_name,
                    start_url=session_config.start_url,
                    region=session_config.region,
                )
            )

        elif kind == ProviderKind.SSO_PROFILE:
            profile_name = profile["name"]
            profile_config = config_data.profiles.get(profile_name)
            if not profile_config:
                raise ValueError(f"프로파일 설정을 찾을 수 없음: {profile_name}")

            # SSO 세션 정보 가져오기
            sso_session_name = profile_config.sso_session
            if sso_session_name:
                # sso_session이 있는 경우 세션에서 start_url, region 가져오기
                session_config = config_data.sessions.get(sso_session_name)
                if session_config:
                    start_url = session_config.start_url
                    sso_region = session_config.region
                else:
                    start_url = profile_config.sso_start_url or ""
                    sso_region = profile_config.sso_region or "ap-northeast-2"
            else:
                # Legacy SSO: 프로파일에 직접 설정된 경우
                sso_session_name = profile_name  # 세션 이름 대신 프로파일 이름 사용
                start_url = profile_config.sso_start_url or ""
                sso_region = profile_config.sso_region or "ap-northeast-2"

            return SSOProfileProvider(
                SSOProfileConfig(
                    profile_name=profile_name,
                    sso_session=sso_session_name,
                    account_id=profile_config.sso_account_id or "",
                    role_name=profile_config.sso_role_name or "",
                    region=profile_config.region or "ap-northeast-2",
                    start_url=start_url,
                    sso_region=sso_region or "ap-northeast-2",
                )
            )

        elif kind == ProviderKind.STATIC_CREDENTIALS:
            profile_name = profile["name"]
            return StaticCredentialsProvider(
                StaticCredentialsConfig(profile_name=profile_name)
            )

        else:
            raise ValueError(f"지원하지 않는 Provider 종류: {kind}")

    def _authenticate(self, ctx: ExecutionContext) -> None:
        """인증 수행"""
        console.print("[dim]인증 중...[/dim]")

        if ctx.provider is None:
            raise RuntimeError("Provider가 설정되지 않음")

        try:
            ctx.provider.authenticate()
            console.print("[dim]인증 완료[/dim]")
        except Exception as e:
            console.print(f"[red]인증 실패: {e}[/red]")
            raise

    def _load_accounts(self, ctx: ExecutionContext) -> list:
        """멀티계정 목록 로드"""
        console.print("[dim]계정 로드 중...[/dim]")

        if ctx.provider is None:
            raise RuntimeError("Provider가 설정되지 않음")

        try:
            accounts_data = ctx.provider.list_accounts()
            accounts = (
                list(accounts_data.values())
                if isinstance(accounts_data, dict)
                else accounts_data
            )
            console.print(f"[dim]{len(accounts)}개 계정[/dim]")
            return accounts
        except Exception as e:
            console.print(f"[yellow]계정 로드 실패: {e}[/yellow]")
            return []
