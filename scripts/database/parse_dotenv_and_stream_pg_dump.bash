#!/usr/bin/env bash
# Defines the extraction pipeline executed remotely via SSH standard input (bash -s)
# Requires Bash 3.2+

REMOTE_ENV_PATH="$1"
DUMP_FORMAT_FLAG="$2"
ENV_DB_KEY="$3"

# 0. Core Requirements Enforcement
if (( BASH_VERSINFO[0] < 3 || (BASH_VERSINFO[0] == 3 && BASH_VERSINFO[1] < 2) )); then
    echo "ERR:bash_version_unsupported: Requires 3.2+" >&2
    exit 1
fi

# 1. Remote Toolchain Preflight
for cmd in grep cut sed pg_dump; do
    command -v "$cmd" >/dev/null || { echo "ERR:missing_dependency_$cmd" >&2; exit 1; }
done

[ -f "$REMOTE_ENV_PATH" ] || { echo "ERR:env_not_found" >&2; exit 1; }

# 2. Credential Extraction
MATCH_COUNT=$(grep --count "^${ENV_DB_KEY}=" "$REMOTE_ENV_PATH")
if [ "$MATCH_COUNT" -eq 0 ]; then
    echo "ERR:${ENV_DB_KEY}_not_found" >&2
    exit 1
elif [ "$MATCH_COUNT" -gt 1 ]; then
    echo "ERR:${ENV_DB_KEY}_multiple_entries_found" >&2
    exit 1
fi

# Extract strictly single known key and strip quotes/whitespace
DB_URL=$(grep "^${ENV_DB_KEY}=" "$REMOTE_ENV_PATH" | cut --delimiter="=" --fields=2- | sed --expression='s/^[[:space:]]*//' --expression='s/[[:space:]]*$//' --expression='s/^["'\'']//' --expression='s/["'\'']$//')

if [ -z "$DB_URL" ]; then
    echo "ERR:database_url_empty" >&2
    exit 1
fi

if [[ ! "$DB_URL" =~ ^postgres(ql)?://[^[:space:]]+$ ]]; then
    echo "ERR:invalid_postgres_url_format" >&2
    exit 1
fi

# 2.5 Industrial URI Normalization (Resolving unencoded @ symbols in passwords)
# If a db password contains an '@' natively (e.g., in a lax .env file), pg_dump fractures hostname parsing.
if [[ "$DB_URL" =~ ^(postgres(ql)?://[^:]+:)(.*)(@[^@/]+(:[0-9]+)?/.*)$ ]]; then
    PREFIX="${BASH_REMATCH[1]}"
    PASS="${BASH_REMATCH[3]}"
    SUFFIX="${BASH_REMATCH[4]}"
    # URL encode all '@' symbols strictly within the isolated password boundary
    PASS="${PASS//@/%40}"
    DB_URL="${PREFIX}${PASS}${SUFFIX}"
fi

# 3. Streaming Execution
# Note: pg_dump uses stdout for the dump file by default when -f is not provided.
pg_dump --dbname="$DB_URL" $DUMP_FORMAT_FLAG --no-password
