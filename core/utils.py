import os
import re
import sys


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


def validate_env():
    errors = []

    if os.environ.get("DEEPSEEK_AUTH_TOKEN"):
        if not os.environ.get("DEEPSEEK_AUTH_TOKEN"):
            errors.append("DeepSeek: missing auth token. Set DEEPSEEK_AUTH_TOKEN")

    if os.environ.get("GEMINI_COOKIE"):
        gc = os.environ.get("GEMINI_COOKIE") or ""
        if not parse_cookie(gc, "__Secure-1PSID"):
            errors.append("Gemini: missing __Secure-1PSID. Set GEMINI_COOKIE=\"__Secure-1PSID=...\"")
        # __Secure-1PSIDTS is optional

    if errors:
        msg = "\n".join(
            ["", "=" * 60, "  ENVIRONMENT VARIABLE ERRORS", "=" * 60]
            + [f"  \u2022 {e}" for e in errors]
            + ["=" * 60]
        )
        print(msg, file=sys.stderr)
        sys.exit(1)
