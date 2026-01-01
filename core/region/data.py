"""
internal/region/data.py - AWS 리전 데이터 (중앙 관리)

리전 목록 업데이트:
    core/region/update_regions.py 실행 후 출력 복사
"""

# 전체 AWS 리전 목록 (2026-01-01 기준)
# 업데이트: core/region/update_regions.py 실행
ALL_REGIONS = [
    "af-south-1",
    "ap-east-1",
    "ap-east-2",
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-northeast-3",
    "ap-south-1",
    "ap-south-2",
    "ap-southeast-1",
    "ap-southeast-2",
    "ap-southeast-3",
    "ap-southeast-4",
    "ap-southeast-5",
    "ap-southeast-6",
    "ap-southeast-7",
    "ca-central-1",
    "ca-west-1",
    "eu-central-1",
    "eu-central-2",
    "eu-north-1",
    "eu-south-1",
    "eu-south-2",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "il-central-1",
    "me-central-1",
    "me-south-1",
    "mx-central-1",
    "sa-east-1",
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
]

# 리전 설명 (한국어)
REGION_NAMES = {
    "us-east-1": "미국 동부 (버지니아)",
    "us-east-2": "미국 동부 (오하이오)",
    "us-west-1": "미국 서부 (캘리포니아)",
    "us-west-2": "미국 서부 (오레곤)",
    "af-south-1": "아프리카 (케이프타운)",
    "ap-east-1": "아시아 태평양 (홍콩)",
    "ap-east-2": "아시아 태평양 (홍콩 야간 데이터센터)",
    "ap-south-1": "아시아 태평양 (뭄바이)",
    "ap-south-2": "아시아 태평양 (하이데라바드)",
    "ap-northeast-1": "아시아 태평양 (도쿄)",
    "ap-northeast-2": "아시아 태평양 (서울)",
    "ap-northeast-3": "아시아 태평양 (오사카)",
    "ap-southeast-1": "아시아 태평양 (싱가포르)",
    "ap-southeast-2": "아시아 태평양 (시드니)",
    "ap-southeast-3": "아시아 태평양 (자카르타)",
    "ap-southeast-4": "아시아 태평양 (멜버른)",
    "ap-southeast-5": "아시아 태평양 (방콕)",
    "ap-southeast-6": "아시아 태평양 (더 팔롭)",
    "ap-southeast-7": "아시아 태평양 (방콕 야간 데이터센터)",
    "ca-central-1": "캐나다 (중부)",
    "ca-west-1": "캐나다 서부 (캘거리)",
    "eu-central-1": "유럽 (프랑크푸르트)",
    "eu-central-2": "유럽 (취리히)",
    "eu-west-1": "유럽 (아일랜드)",
    "eu-west-2": "유럽 (런던)",
    "eu-west-3": "유럽 (파리)",
    "eu-south-1": "유럽 (밀라노)",
    "eu-south-2": "유럽 (스페인)",
    "eu-north-1": "유럽 (스톡홀름)",
    "il-central-1": "이스라엘 (텔아비브)",
    "me-south-1": "중동 (바레인)",
    "me-central-1": "중동 (UAE)",
    "mx-central-1": "멕시코 중부 (쿠에르나바카)",
    "sa-east-1": "남아메리카 (상파울루)",
}

# 자주 사용하는 리전
COMMON_REGIONS = [
    ("ap-northeast-2", "서울"),
    ("us-east-1", "버지니아"),
    ("ap-northeast-1", "도쿄"),
    ("ap-southeast-1", "싱가포르"),
]
