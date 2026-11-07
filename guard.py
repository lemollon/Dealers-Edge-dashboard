"""
Repo-level gates that hold in any client, any clone, and at the merge point.

Stdlib only and importable (`import guard`). Called by scripts/check.sh, which
CI runs via `make check`, so these rules do not depend on a Claude Code session.

Each gate mirrors a failure that already cost real time:
  - ThetaData v2 is refused (it reports its blind spots as empty data; it
    silently erased all of 2025 from a study on 2026-10-30). Use thetadata_v3.
  - ORATS / Polygon / yfinance are not sanctioned backtest sources.
  - A marks-based number is "found in history", never a result.
  - Every backtest queries the Render mirror / alphagex_backtest first.
"""
from __future__ import annotations
import importlib.util
import inspect
import os
import re
from pathlib import Path


class GateViolation(Exception):
    """A repo gate was violated. Fix the cause; do not weaken the gate."""


# Port 25510 is the RETIRED v2 terminal; 25503 is checked too so a stray v2
# path on the v3 port cannot slip through. ThetaTerminal.jar is the v2 jar --
# ThetaTerminalv3.jar is the sanctioned one and is not matched.
_V2_PORTS = ("25510", "25503")
_V2_JAR = re.compile(r"ThetaTerminal(?!v3)", re.IGNORECASE)
_BANNED_MODULES = ("orats", "polygon", "yfinance")


def _caller_source(depth: int = 2) -> tuple[str | None, str]:
    """Path and source text of the module that called a guard function."""
    frame = inspect.stack()[depth]
    path = frame.filename
    if not path or path.startswith("<") or not Path(path).is_file():
        return None, ""
    if Path(path).resolve() == Path(__file__).resolve():
        return None, ""
    try:
        return path, Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return path, ""


def _hits_v2(text: str) -> str | None:
    for port in _V2_PORTS:
        if re.search(rf"(?<!\d){port}(?!\d)", text):
            return f"ThetaData v2 port {port}"
    if _V2_JAR.search(text):
        return "ThetaTerminal (v2 jar)"
    return None


def assert_env() -> None:
    """Raise GateViolation if the environment or the calling module reaches a
    banned data source."""
    for key, value in os.environ.items():
        hit = _hits_v2(str(value))
        if hit:
            raise GateViolation(
                f"environment variable {key} points at {hit}. ThetaData is v3 "
                f"only: use `import thetadata_v3 as td`.")

    path, source = _caller_source()
    if not source:
        return
    hit = _hits_v2(source)
    if hit:
        raise GateViolation(
            f"{path} references {hit}. ThetaData is v3 only: use "
            f"`import thetadata_v3 as td`.")
    for mod in _BANNED_MODULES:
        if importlib.util.find_spec(mod) is None:
            continue
        if re.search(rf"\b{mod}\b", source, re.IGNORECASE):
            raise GateViolation(
                f"{path} references '{mod}', which is installed but is not a "
                f"sanctioned data source. Use the local warehouse / ThetaData v3.")


def assert_fill_convention(result: dict) -> None:
    """Raise unless the result dict states how its fills were scored."""
    convention = result.get("fill_convention") if isinstance(result, dict) else None
    if not convention or not str(convention).strip():
        raise GateViolation(
            "result carries no non-empty 'fill_convention'. A marks-based "
            "number is \"found in history\", never a result and never a $/day "
            "figure. State the fill convention (e.g. NBBO at entry/exit, sell "
            "at bid / buy at ask; multi-day stock = next-session close).")


def assert_mirror_first(queried: bool) -> None:
    """Raise if a backtest runs before the Render mirror / alphagex_backtest
    was queried."""
    if not queried:
        raise GateViolation(
            "backtest started without querying the Render mirror / "
            "alphagex_backtest first. Query it, then pass queried=True.")
