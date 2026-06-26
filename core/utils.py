import re


def parse_cookie(cookie_str: str | None, name: str) -> str | None:
    if not cookie_str:
        return None
    m = re.search(rf"(?:^|;\s*){re.escape(name)}=([^;]+)", cookie_str)
    return m.group(1) if m else None


def extract_text(content: str | list | None) -> str:
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                t = part.get("text", "")
                if t:
                    texts.append(t)
        return " ".join(texts)
    return str(content)
