"""functions/reports/scheduled/schedule.py - 다음 실행 예정일 계산.

TaskCycle(일간/주간/월간/분기/반기/연간)에 따라 다음 권장 실행일을 계산합니다.
분기/반기/연간은 각각 1/4/7/10월, 1/7월, 1월 첫째 주 월요일을 기준으로 합니다.
"""

from datetime import date, datetime, timedelta

from .types import TaskCycle


def get_week_of_month(target_date: date) -> int:
    """월의 몇 번째 주인지 계산

    Args:
        target_date: 대상 날짜

    Returns:
        주차 (1~5)
    """
    first_day = target_date.replace(day=1)
    dom = target_date.day
    adjusted_dom = dom + first_day.weekday()
    return (adjusted_dom - 1) // 7 + 1


def get_next_monday(from_date: date) -> date:
    """다음 월요일 계산 (오늘이 월요일이면 오늘 반환)

    Args:
        from_date: 기준 날짜

    Returns:
        다음 월요일 (또는 오늘이 월요일이면 오늘)
    """
    weekday = from_date.weekday()
    if weekday == 0:  # 월요일
        return from_date
    days_until_monday = 7 - weekday
    return from_date + timedelta(days=days_until_monday)


def get_next_month_first(from_date: date) -> date:
    """다음 달 1일 계산

    Args:
        from_date: 기준 날짜

    Returns:
        다음 달 1일
    """
    if from_date.month == 12:
        return date(from_date.year + 1, 1, 1)
    return date(from_date.year, from_date.month + 1, 1)


def get_next_quarter_first(from_date: date) -> date:
    """다음 분기 첫째날 계산 (1, 4, 7, 10월 1일)

    Args:
        from_date: 기준 날짜

    Returns:
        다음 분기 첫째날
    """
    current_quarter = (from_date.month - 1) // 3 + 1
    if current_quarter == 4:
        return date(from_date.year + 1, 1, 1)
    next_quarter_month = current_quarter * 3 + 1
    return date(from_date.year, next_quarter_month, 1)


def get_next_biannual_first(from_date: date) -> date:
    """다음 반기 첫째날 계산 (1, 7월 1일)

    Args:
        from_date: 기준 날짜

    Returns:
        다음 반기 첫째날
    """
    if from_date.month <= 6:
        return date(from_date.year, 7, 1)
    return date(from_date.year + 1, 1, 1)


def get_next_year_first(from_date: date) -> date:
    """다음 연도 첫째날 계산

    Args:
        from_date: 기준 날짜

    Returns:
        다음 연도 1월 1일
    """
    return date(from_date.year + 1, 1, 1)


def get_next_run_date(cycle: TaskCycle, last_run: datetime | None = None) -> date:
    """주기별 다음 권장 실행일 계산

    Args:
        cycle: 작업 주기
        last_run: 마지막 실행 시간 (None이면 미실행으로 간주)

    Returns:
        다음 권장 실행일
    """
    today = date.today()

    # 마지막 실행 기록이 없으면 오늘 반환 (즉시 실행 권장)
    if last_run is None:
        return today

    last_date = last_run.date() if isinstance(last_run, datetime) else last_run

    if cycle == TaskCycle.DAILY:
        # 일간: 매일 실행
        next_date = last_date + timedelta(days=1)
        return max(next_date, today)

    elif cycle == TaskCycle.WEEKLY:
        # 주간: 다음 월요일
        next_monday = get_next_monday(last_date + timedelta(days=1))
        return max(next_monday, get_next_monday(today))

    elif cycle == TaskCycle.MONTHLY:
        # 월간: 다음 달 1일
        next_month = get_next_month_first(last_date)
        return max(next_month, today)

    elif cycle == TaskCycle.QUARTERLY:
        # 분기: 다음 분기 1일
        next_quarter = get_next_quarter_first(last_date)
        return max(next_quarter, today)

    elif cycle == TaskCycle.BIANNUAL:
        # 반기: 다음 반기 1일
        next_biannual = get_next_biannual_first(last_date)
        return max(next_biannual, today)

    elif cycle == TaskCycle.ANNUAL:
        # 연간: 다음 연도 1월 1일
        next_year = get_next_year_first(last_date)
        return max(next_year, today)

    # 알 수 없는 주기는 오늘 반환
    return today


def format_next_run_date(next_run: date, lang: str = "ko") -> str:
    """다음 실행일을 포맷팅

    Args:
        next_run: 다음 실행일
        lang: 언어 ("ko" 또는 "en")

    Returns:
        포맷된 문자열 (예: "02-03", "다음: 02-03")
    """
    return next_run.strftime("%m-%d")


def is_due(cycle: TaskCycle, last_run: datetime | None = None) -> bool:
    """실행이 필요한지 확인

    Args:
        cycle: 작업 주기
        last_run: 마지막 실행 시간

    Returns:
        True면 실행 필요
    """
    next_run = get_next_run_date(cycle, last_run)
    return next_run <= date.today()


def get_days_until_next_run(cycle: TaskCycle, last_run: datetime | None = None) -> int:
    """다음 실행까지 남은 일수

    Args:
        cycle: 작업 주기
        last_run: 마지막 실행 시간

    Returns:
        남은 일수 (0이면 오늘 실행 필요, 음수면 과거)
    """
    next_run = get_next_run_date(cycle, last_run)
    return (next_run - date.today()).days
