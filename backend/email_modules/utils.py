import unicodedata
import sys

def clean_str(s):
    """Convert any bytes/str to safe, printable UTF-8."""
    if s is None:
        return ""
    if isinstance(s, bytes):
        s = s.decode("utf-8", errors="replace")
    # Normalize weird spaces, accents, etc.
    s = unicodedata.normalize("NFKC", s).replace("\xa0", " ")
    return s

def setup_utf8_encoding():
    """Ensure stdout/stderr are UTF-8"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
