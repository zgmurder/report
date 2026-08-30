from __future__ import annotations

from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Comment, Tag

_ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "caption", "code", "col", "colgroup", "dd", "del", "div", "dl", "dt",
    "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "li", "ol", "p", "pre", "s", "section",
    "span", "strong", "sub", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul",
}
_DROP_WITH_CONTENT = {"script", "style", "iframe", "object", "embed", "form", "input", "button", "textarea", "select", "option", "link", "meta", "base"}
_ALLOWED_ATTRS = {"class", "href", "title", "target", "rel", "colspan", "rowspan", "scope", "align"}
_SAFE_SCHEMES = {"", "http", "https", "mailto", "tel"}
_MAX_CLASSES = 12
_MAX_CLASS_LENGTH = 64


def sanitize_report_html(value: str) -> str:
    """Return report HTML constrained to a small formatting-only allowlist."""
    soup = BeautifulSoup(value or "", "html.parser")
    for comment in soup.find_all(string=lambda item: isinstance(item, Comment)):
        comment.extract()
    # Remove active-content subtrees before walking the remaining tags.  A nested
    # decompose invalidates descendants (their name becomes None), which used to
    # make the second pass fail with AttributeError and return HTTP 500.
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


def _sanitize_attributes(tag: Tag) -> None:
    clean: dict[str, object] = {}
    for raw_name, raw_value in list(tag.attrs.items()):
        name = str(raw_name).lower()
        if name.startswith("on") or name == "style" or name not in _ALLOWED_ATTRS:
            continue
        if name == "class":
            classes = raw_value if isinstance(raw_value, list) else str(raw_value).split()
            safe_classes = [item for item in classes[:_MAX_CLASSES] if item and len(item) <= _MAX_CLASS_LENGTH and item.replace("-", "").replace("_", "").isalnum()]
            if safe_classes:
                clean[name] = safe_classes
            continue
        text = " ".join(raw_value) if isinstance(raw_value, list) else str(raw_value)
        if name == "href" and not _safe_url(text):
            continue
        if name == "target" and text not in {"_blank", "_self"}:
            continue
        clean[name] = text[:500]
    if clean.get("target") == "_blank":
        clean["rel"] = "noopener noreferrer"
    tag.attrs = clean


def _safe_url(value: str) -> bool:
    compact = "".join(value.split()).lower()
    if compact.startswith(("javascript:", "vbscript:", "data:text/html")):
        return False
    return urlsplit(value.strip()).scheme.lower() in _SAFE_SCHEMES
