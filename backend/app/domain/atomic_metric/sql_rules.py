DATE_END_EXCLUSIVE_EXPR = (
    "CASE WHEN CHAR_LENGTH(:date_end) <= 10 "
    "THEN DATE_ADD(:date_end, INTERVAL 1 DAY) "
    "ELSE DATE_ADD(:date_end, INTERVAL 1 SECOND) END"
)

UNIT_NAME_STRIP_TOKENS = ("义乌", "交警")


def normalize_unit_name_display(text: str) -> str:
    result = (text or "").strip()
    for token in UNIT_NAME_STRIP_TOKENS:
        result = result.replace(token, "")
    return result.strip()
