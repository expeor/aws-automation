"""
functions/analyzers/transfer - AWS Transfer Family 서버 분석 도구

Transfer Family(SFTP/FTPS/FTP) 서버의 사용 현황을 분석하고
유휴/미사용 서버를 탐지합니다.

도구 목록:
    - unused: 유휴/미사용 Transfer Family 서버 탐지
"""

CATEGORY = {
    "name": "transfer",
    "display_name": "Transfer Family",
    "description": "AWS Transfer Family 서버 분석",
    "description_en": "AWS Transfer Family server analysis",
    "aliases": ["sftp", "ftp", "ftps"],
}

TOOLS = [
    {
        "name": "미사용 서버",
        "name_en": "Unused Servers",
        "description": "유휴/미사용 Transfer Family 서버 탐지",
        "description_en": "Detect idle/unused Transfer Family servers",
        "permission": "read",
        "module": "unused",
        "area": "unused",
    },
]
