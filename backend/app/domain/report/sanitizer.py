from __future__ import annotations

import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment, Tag

_ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "caption", "code", "col", "colgroup", "dd", "del", "div", "dl", "dt",
    "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "li", "ol", "p", "pre", "s", "section",
    "span", "strong", "sub", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
}
_DROP_WITH_CONTENT = {"script", "style", "iframe", "object", "embed", "form", "input", "button", "textarea", "select", "option", "link", "meta", "base"}
_ALLOWED_ATTRS = {"class", "href", "title", "target", "rel", "colspan", "rowspan", "scope", "align", "style"}
_SAFE_SCHEMES = {"", "http", "https", "mailto", "tel"}
_MAX_CLASSES = 12
_MAX_CLASS_LENGTH = 64
_MAX_STYLE_LENGTH = 2000

_CSS_ENUMS = {
    "border-collapse": {"collapse", "separate"},
    "break-after": {"auto", "avoid", "page"},
    "break-before": {"auto", "avoid", "page"},
    "font-style": {"normal", "italic", "oblique"},
    "font-weight": {"normal", "bold", "bolder", "lighter", "100", "200", "300", "400", "500", "600", "700", "800", "900"},
    "table-layout": {"auto", "fixed"},
    "text-align": {"left", "center", "right", "justify", "start", "end"},
    "vertical-align": {"baseline", "middle", "top", "bottom", "super", "sub"},
}
_CSS_LENGTH_PROPERTIES = {
    "font-size", "margin-top", "margin-right", "margin-bottom", "margin-left", "text-indent", "width",
}
_CSS_BOX_PROPERTIES = {"padding"}
_CSS_COLOR_PROPERTIES = {"color", "background-color"}
_CSS_ALLOWED_PROPERTIES = set(_CSS_ENUMS) | _CSS_LENGTH_PROPERTIES | _CSS_BOX_PROPERTIES | _CSS_COLOR_PROPERTIES | {
    "background", "border", "font-family", "line-height", "text-decoration",
}
_LENGTH_RE = re.compile(r"^(?:0|(?:\d+(?:\.\d+)?|\.\d+)(?:px|pt|cm|mm|em|rem|%))$", re.IGNORECASE)
_NUMBER_RE = re.compile(r"^(?:\d+(?:\.\d+)?|\.\d+)$")
_COLOR_RE = re.compile(
    r"^(?:#[0-9a-f]{3}(?:[0-9a-f]{3})?|rgb\(\s*(?:\d{1,3}\s*,\s*){2}\d{1,3}\s*\)|"
    r"black|white|red|green|blue|gray|grey|yellow|transparent)$",
    re.IGNORECASE,
)
_FONT_FAMILY_RE = re.compile(r'^[\w\u4e00-\u9fff\s,\-\'".]+$', re.UNICODE)
_BORDER_RE = re.compile(
    r"^(?:0|(?:\d+(?:\.\d+)?)(?:px|pt|cm|mm))\s+(?:none|solid|dashed|dotted|double)\s+"
    r"(?:#[0-9a-f]{3}(?:[0-9a-f]{3})?|black|white|red|green|blue|gray|grey)$",
    re.IGNORECASE,
)


def sanitize_report_html(value: str) -> str:
    """Return report HTML constrained to a formatting-only HTML/CSS allowlist."""
    soup = BeautifulSoup(value or "", "html.parser")
    for comment in soup.find_all(string=lambda item: isinstance(item, Comment)):
        comment.extract()
    # Remove active-content subtrees before walking the remaining tags. A nested
    # decompose invalidates descendants, so guard names during the second pass.
    for tag in list(soup.find_all(_DROP_WITH_CONTENT)):
        if tag.name is not None:
            tag.decompose()
    for tag in list(soup.find_all(True)):
        name = str(tag.name or "").lower()
        if name not in _ALLOWED_TAGS:
            tag.unwrap()
            continue
        _sanitize_attributes(tag)
    root = soup.body or soup
    return "".join(str(child) for child in root.contents)


def parse_safe_styles(value: object) -> dict[str, str]:
    """Parse the same safe CSS subset accepted by ``sanitize_report_html``."""
    raw = str(value or "")[:_MAX_STYLE_LENGTH]
    result: dict[str, str] = {}
    for declaration in raw.split(";"):
        if ":" not in declaration:
            continue
        raw_name, raw_value = declaration.split(":", 1)
        name = raw_name.strip().lower()
        css_value = " ".join(raw_value.strip().split())
        if name in _CSS_ALLOWED_PROPERTIES and _safe_css_value(name, css_value):
            result[name] = css_value
    return result


def _sanitize_attributes(tag: Tag) -> None:
    clean: dict[str, object] = {}
    for raw_name, raw_value in list(tag.attrs.items()):
        name = str(raw_name).lower()
        if name.startswith("on") or name not in _ALLOWED_ATTRS:
            continue
        if name == "class":
            classes = raw_value if isinstance(raw_value, list) else str(raw_value).split()
            safe_classes = [item for item in classes[:_MAX_CLASSES] if item and len(item) <= _MAX_CLASS_LENGTH and item.replace("-", "").replace("_", "").isalnum()]
            if safe_classes:
                clean[name] = safe_classes
            continue
        text = " ".join(raw_value) if isinstance(raw_value, list) else str(raw_value)
        if name == "style":
            styles = parse_safe_styles(text)
            if styles:
                clean[name] = ";".join(f"{key}:{value}" for key, value in styles.items())
            continue
        if name == "href" and not _safe_url(text):
            continue
        if name == "target" and text not in {"_blank", "_self"}:
            continue
        clean[name] = text[:500]
    if clean.get("target") == "_blank":
        clean["rel"] = "noopener noreferrer"
    tag.attrs = clean


def _safe_css_value(name: str, value: str) -> bool:
    lowered = value.lower()
    if not value or any(token in lowered for token in ("url(", "expression", "javascript:", "vbscript:", "data:", "@import", "var(")):
        return False
    if "\\" in value or "{" in value or "}" in value or "<" in value or ">" in value:
        return False
    if name in _CSS_ENUMS:
        return lowered in _CSS_ENUMS[name]
    if name in _CSS_LENGTH_PROPERTIES:
        return bool(_LENGTH_RE.fullmatch(value)) or (name == "font-size" and lowered in {"smaller", "larger"})
    if name == "line-height":
        return bool(_NUMBER_RE.fullmatch(value) or _LENGTH_RE.fullmatch(value))
    if name in _CSS_BOX_PROPERTIES:
        parts = value.split()
        return 1 <= len(parts) <= 4 and all(_LENGTH_RE.fullmatch(part) for part in parts)
    if name in _CSS_COLOR_PROPERTIES:
        return _safe_color(value)
    if name == "background":
        return lowered == "transparent" or _safe_color(value)
    if name == "font-family":
        return len(value) <= 200 and bool(_FONT_FAMILY_RE.fullmatch(value))
    if name == "text-decoration":
        parts = lowered.split()
        return bool(parts) and set(parts) <= {"none", "underline", "line-through"}
    if name == "border":
        return bool(_BORDER_RE.fullmatch(value))
    return False


def _safe_color(value: str) -> bool:
    if not _COLOR_RE.fullmatch(value):
        return False
    if value.lower().startswith("rgb("):
        numbers = [int(part.strip()) for part in value[4:-1].split(",")]
        return len(numbers) == 3 and all(0 <= number <= 255 for number in numbers)
    return True


def _safe_url(value: str) -> bool:
    compact = "".join(value.split()).lower()
    if compact.startswith(("javascript:", "vbscript:", "data:text/html")):
        return False
    return urlsplit(value.strip()).scheme.lower() in _SAFE_SCHEMES
