#!/bin/sh
# Repo gates, runnable outside any Claude session (CI runs this via `make check`).
# Exits non-zero on any violation, naming the file and line.
cd "$(dirname "$0")/.." || exit 1

PY=python3
"$PY" -c "" >/dev/null 2>&1 || PY=python
fail=0

# 1. guard.assert_env() -- environment must not point at a banned source.
if ! "$PY" -c "import guard; guard.assert_env()"; then
    echo "check.sh: FAIL: guard.assert_env() raised (see above)" >&2
    fail=1
fi

# 2. Banned data sources in tracked .py files. Only genuine data-source use matches
#    (imports, API hosts, tokens, terminal ports); a bare word in a comment does not.
#    Excluded by path: guard.py, config.py where it holds the v2 refusal block,
#    any tests/ directory, any .md file. Known debt is listed in .gates-allowlist
#    (one line per file: path : reason : registered) and warns instead of failing.
PAT='polygon\.io|^[[:space:]]*import[[:space:]].*\b(polygon|yfinance|orats)\b|^[[:space:]]*from[[:space:]]+(polygon|yfinance|orats)[[:space:]]+import|polygon-api-client|yahoo_fin|api\.orats|ORATS_TOKEN|orat_bulkzip|(127\.0\.0\.1|localhost):(25510|25503)'
EXCLUDE='^guard\.py$|(^|/)tests/|\.md$'
if [ -f config.py ] && grep -q 'ThetaV2Blocked' config.py; then
    EXCLUDE="$EXCLUDE|^config\.py\$"
fi

hits=$(git ls-files '*.py' | grep -Ev "$EXCLUDE" | xargs grep -lE -e "$PAT" 2>/dev/null)
allowed=""
n_allow=0
n_viol=0

if [ -f .gates-allowlist ]; then
    while IFS= read -r line || [ -n "$line" ]; do
        line=$(printf '%s' "$line" | tr -d '\r')
        case "$line" in ''|'#'*|' '*'#'*) continue ;; esac
        path=${line%% : *}
        rest=${line#* : }
        reason=${rest%% : *}
        [ -n "$path" ] || continue
        n_allow=$((n_allow + 1))
        allowed="$allowed
$path"
        if printf '%s\n' "$hits" | grep -qxF -- "$path"; then
            echo "check.sh: WARN: allowlisted banned source: $path ($reason)" >&2
        else
            echo "check.sh: FAIL: stale allowlist entry: $path" >&2
            n_viol=$((n_viol + 1))
        fi
    done < .gates-allowlist
fi

while IFS= read -r f; do
    [ -n "$f" ] || continue
    if printf '%s\n' "$allowed" | grep -qxF -- "$f"; then
        continue
    fi
    echo "check.sh: FAIL: banned data source in $f:" >&2
    grep -nE -e "$PAT" "$f" | sed 's/^/  /' >&2
    n_viol=$((n_viol + 1))
done <<EOF
$hits
EOF

echo "check.sh: $n_allow files allowlisted, $n_viol violations"
[ "$n_viol" -eq 0 ] || fail=1

# 3. Every tracked results/*.json must carry a fill_convention key.
missing=$(git ls-files | grep -E '(^|/)results/.*\.json$' | while IFS= read -r f; do
    "$PY" - "$f" <<'PYEOF'
import json, sys
p = sys.argv[1]
try:
    d = json.load(open(p, encoding="utf-8"))
except Exception as e:
    print(f"{p}:1: unreadable JSON ({e})")
    sys.exit(0)
if not isinstance(d, dict) or not str(d.get("fill_convention", "")).strip():
    print(f"{p}:1: no non-empty fill_convention key")
PYEOF
done)
if [ -n "$missing" ]; then
    echo "check.sh: FAIL: results JSON without fill_convention (a marks-based number is \"found in history\", never a result):" >&2
    echo "$missing" | sed 's/^/  /' >&2
    fail=1
fi

[ "$fail" -eq 0 ] && echo "check.sh: OK"
exit "$fail"
