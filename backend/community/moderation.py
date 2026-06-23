import re
import unicodedata


# MVP에서는 명확한 욕설·비속어만 차단한다. 공백·특수문자·숫자로 우회한 입력도 함께 검사한다.
RAW_BLOCKED_TERMS = (
    "씨발", "시발", "씹", "ㅅㅂ", "ㅆㅂ", "병신", "븅신", "ㅂㅅ", "개새끼", "개색기", "ㄱㅅㄲ",
    "좆", "존나", "ㅈㄴ", "ㅈ같", "지랄", "ㅈㄹ", "꺼져", "닥쳐", "등신", "호구", "빡대가리",
    "미친놈", "미친년", "쓰레기", "fuck", "shit", "bitch", "asshole",
)


def normalize_text(value):
    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = re.sub(r"[^\w\u1100-\u11ff\u3130-\u318f]+", "", normalized)
    return re.sub(r"\d+", "", normalized)


BLOCKED_TERMS = tuple(normalize_text(term) for term in RAW_BLOCKED_TERMS)


def contains_profanity(value):
    normalized = normalize_text(value)
    return any(term in normalized for term in BLOCKED_TERMS)


def validate_clean_text(value):
    cleaned = value.strip()
    if contains_profanity(cleaned):
        raise ValueError("욕설 또는 비속어가 포함되어 있어 등록할 수 없습니다.")
    return cleaned
