DATE_END_EXCLUSIVE_EXPR = (
    "CASE WHEN CHAR_LENGTH(:date_end) <= 10 "
    "THEN DATE_ADD(:date_end, INTERVAL 1 DAY) "
    "ELSE DATE_ADD(:date_end, INTERVAL 1 SECOND) END"
)

UNIT_NAME_STRIP_TOKENS = ("义乌", "交警")


def date_end_bound_expr(date_end: str | None = None) -> str:
    """时间上界表达式。

    前端已传完整 DATETIME 且作为开区间上界时，直接用 :date_end；
    仅日期（<=10 字符）时仍按「含当天」扩到次日。
    """
    text = str(date_end or "").strip()
    if len(text) > 10:
        return ":date_end"
    return DATE_END_EXCLUSIVE_EXPR


def normalize_unit_name_display(text: str) -> str:
    result = (text or "").strip()
    for token in UNIT_NAME_STRIP_TOKENS:
        result = result.replace(token, "")
    return result.strip()
