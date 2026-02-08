"""
plugins/transfer/__init__.py - AWS Transfer Family 플러그인

SFTP/FTPS/FTP 서버 관리 및 분석
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
