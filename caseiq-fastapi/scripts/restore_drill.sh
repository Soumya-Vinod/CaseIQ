#!/usr/bin/env bash
# Restore drill, Tier 1: proves the actual chain this project's backups
# depend on -- pg_dump -> age encrypt -> age decrypt -> pg_restore -- round-
# trips real data losslessly, against a throwaway target database. Re-run
# this after any change to backup_dump.sh, the tracked schema, or the age
# keypair -- not a one-off. See docs/deployment.md's backup-planning entry
# for what this is and isn't proving (Tier 1: the backup mechanism itself,
# against a disposable local/branch DB with no pgvector dependency needed
# for the 6 backed-up tables. Tier 2, separate and not this script: booting
# the real app against a fully rebuilt DB -- corpus re-ingestion included --
# needs a Postgres with pgvector, e.g. a real Neon branch).
#
# Requires:
#   DATABASE_URL_DIRECT     -- source DB to dump FROM (the real one, or a
#                               Neon branch)
#   RESTORE_TARGET_URL      -- a throwaway, EMPTY Postgres to restore INTO.
#                               This script creates the schema fresh via
#                               `alembic upgrade head` and does not check
#                               whether it's clobbering something real --
#                               NEVER point this at the same database as
#                               DATABASE_URL_DIRECT, or at anything you'd
#                               mind losing.
#   RESTORE_TARGET_NEEDS_SSL -- "true" or "false". Neon (or any managed PG)
#                               needs "true"; a local/Docker Postgres with no
#                               TLS listener needs "false". No safe default --
#                               required explicitly.
#   AGE_IDENTITY_FILE       -- path to an age private-key file matching
#                               BACKUP_AGE_PUBLIC_KEY below. For a real
#                               drill, the production private key (never
#                               committed, never handed to CI -- only this
#                               script, run by a person, ever decrypts). For
#                               a mechanism-only test, a throwaway keypair
#                               (`age-keygen`) is fine.
#   BACKUP_AGE_PUBLIC_KEY   -- passed through to backup_dump.sh. Not needed
#                               (and not read) when EXISTING_ENC_PATH is set
#                               -- nothing gets freshly encrypted in that mode.
#   PG_DUMP_BIN (optional)  -- if exported before running this, it reaches
#                               backup_dump.sh's fresh-dump path unchanged
#                               (ordinary shell inheritance, not special-
#                               cased here). Irrelevant when EXISTING_ENC_PATH
#                               is set -- no dump gets taken in that mode.
#                               Plain `pg_dump` is correct on a normal
#                               machine; only needed if PATH resolution
#                               can't be trusted -- see backup_dump.sh.
#
#   EXISTING_ENC_PATH       -- OPTIONAL. Path to an already-encrypted
#                               .dump.age file -- e.g. one just pulled down
#                               from the real caseiq-backups repo -- to
#                               restore from INSTEAD of dumping a fresh one.
#                               This is the only mode that actually proves
#                               the file that left this machine (via the
#                               real GH Actions workflow, pushed to a repo
#                               only you can read) is the one that restores
#                               -- a drill that only ever restores from a
#                               dump generated and consumed on the same
#                               machine, in the same run, hasn't proven that.
#                               DATABASE_URL_DIRECT is still required in
#                               this mode -- step 5 still compares the
#                               restored data against the live source, which
#                               means: if real writes happened between when
#                               that backup was taken and now, a mismatch is
#                               data drift, not a broken restore -- check the
#                               dump's timestamp against recent activity
#                               before treating a mismatch here as a bug.
#
# Usage (fresh dump, mechanism test):
#   DATABASE_URL_DIRECT=... RESTORE_TARGET_URL=... RESTORE_TARGET_NEEDS_SSL=false \
#     AGE_IDENTITY_FILE=... BACKUP_AGE_PUBLIC_KEY=... ./scripts/restore_drill.sh
#
# Usage (real downloaded backup, the drill that actually proves the chain):
#   DATABASE_URL_DIRECT=... RESTORE_TARGET_URL=... RESTORE_TARGET_NEEDS_SSL=false \
#     AGE_IDENTITY_FILE=... EXISTING_ENC_PATH=/path/to/pulled/backup-*.dump.age \
#     ./scripts/restore_drill.sh
set -euo pipefail

: "${DATABASE_URL_DIRECT:?}"
: "${RESTORE_TARGET_URL:?}"
: "${RESTORE_TARGET_NEEDS_SSL:?must be 'true' or 'false', no default}"
: "${AGE_IDENTITY_FILE:?}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT   # WORK holds a decrypted dump with real PII -- always scrubbed on exit

if [ -n "${EXISTING_ENC_PATH:-}" ]; then
  echo "== 1/5: using an existing encrypted file, not dumping a fresh one =="
  ENC_PATH="$EXISTING_ENC_PATH"
  echo "   -> $ENC_PATH"
else
  : "${BACKUP_AGE_PUBLIC_KEY:?}"
  echo "== 1/5: dump + encrypt the real source =="
  ENC_PATH="$(OUT_DIR="$WORK" DATABASE_URL_DIRECT="$DATABASE_URL_DIRECT" \
    BACKUP_AGE_PUBLIC_KEY="$BACKUP_AGE_PUBLIC_KEY" "$HERE/backup_dump.sh")"
  echo "   -> $ENC_PATH"
fi

echo "== 2/5: decrypt =="
DEC_PATH="$WORK/decrypted.dump"
age -d -i "$AGE_IDENTITY_FILE" -o "$DEC_PATH" "$ENC_PATH"

echo "== 3/5: build a fresh schema at the target (alembic upgrade head) =="
# Same override trick as the app's own config: DATABASE_URL_RAW unset (as
# empty, not merely absent -- see app/core/config.py, .env still has a real
# value that would otherwise leak through) means no forced-SSL connect_args,
# for a plain local/Docker target; RESTORE_TARGET_NEEDS_SSL=true keeps it
# for a real managed-Postgres target like a Neon branch.
if [ "$RESTORE_TARGET_NEEDS_SSL" = "true" ]; then
  ( cd "$HERE/.." && DATABASE_URL_RAW="$RESTORE_TARGET_URL" DATABASE_URL_DIRECT="$RESTORE_TARGET_URL" \
    python -m alembic upgrade head )
else
  ( cd "$HERE/.." && DATABASE_URL_RAW="" DATABASE_URL_DIRECT="$RESTORE_TARGET_URL" \
    python -m alembic upgrade head )
fi

echo "== 4/5: restore data only (schema already exists from step 3) =="
pg_restore --data-only --disable-triggers --no-owner --no-privileges \
  -d "$RESTORE_TARGET_URL" "$DEC_PATH"

echo "== 5/5: verify =="
python "$HERE/_restore_drill_verify.py" "$DATABASE_URL_DIRECT" "$RESTORE_TARGET_URL"
