#!/usr/bin/env bash
# Dumps the unrecoverable set -- see docs/deployment.md's backup-planning
# entry for the full reasoning -- and encrypts it in place. Six tables, not
# five: query_responses.corpus_version_id carries a real FK to
# corpus_versions with every row populated (checked against the live DB,
# not assumed) -- without corpus_versions in the same dump, a restore either
# fails the FK check outright or leaves every historical answer's snapshot
# reference dangling. corpus_versions is cheap (one row, ~32kB today) and is
# corpus-adjacent metadata, not corpus content -- doesn't change what's
# "rebuildable from the PDFs" vs. "backed up here," it just keeps the
# restored data internally consistent.
#
# The corpus itself (acts/section_versions/offence_attributes/
# judicial_status) is deliberately excluded -- rebuildable from the tracked
# source PDFs + scripts/ingest_*, see docs/deployment.md.
#
# Requires in the environment:
#   DATABASE_URL_DIRECT      -- unpooled Neon connection string (pg_dump
#                                should never go through the pgbouncer pool)
#   BACKUP_AGE_PUBLIC_KEY    -- an age recipient ("age1..."), generated via
#                                `age-keygen`. NOT sensitive -- this script
#                                only ever encrypts, never decrypts, so it
#                                never needs (and must never be given) the
#                                matching private key.
#
# Optional:
#   PG_DUMP_BIN              -- force a specific pg_dump binary, skipping
#                                auto-resolution below. Only for exceptional
#                                cases; normally left unset so this script
#                                resolves the right one itself.
#
# Writes one file to $OUT_DIR (default ./backups):
#   backup-<UTC timestamp>.dump.age
# and prints its path on stdout (the one line of output that matters --
# everything else on stdout/stderr is pg_dump/age's own progress noise).
#
# Usage: DATABASE_URL_DIRECT=... BACKUP_AGE_PUBLIC_KEY=... ./backup_dump.sh
set -euo pipefail

: "${DATABASE_URL_DIRECT:?DATABASE_URL_DIRECT must be set}"
: "${BACKUP_AGE_PUBLIC_KEY:?BACKUP_AGE_PUBLIC_KEY must be set}"

# FIXED 2026-09-12, in three parts -- see docs/evaluation.md for the full
# arc: two pg_dump-version mismatches against Neon (unversioned apt
# package, then Debian's own pg_wrapper still resolving plain `pg_dump` on
# PATH to the wrong installed major regardless), then a THIRD, identical
# failure in a different workflow entirely (nightly-eval.yml, against the
# eval Postgres service container, a different server version again) --
# because the fix lived here alone instead of somewhere every pg_dump/
# pg_restore call site shares. scripts/lib/pg_bin.sh is that shared place
# now; this line is the only thing left here.
source "$(dirname "${BASH_SOURCE[0]}")/lib/pg_bin.sh"
PG_DUMP_BIN="${PG_DUMP_BIN:-$(resolve_pg_bin "$DATABASE_URL_DIRECT" pg_dump)}"

OUT_DIR="${OUT_DIR:-./backups}"
mkdir -p "$OUT_DIR"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RAW="$OUT_DIR/backup-$STAMP.dump"
ENC="$RAW.age"

# Found live, not by review: under `set -e`, a plain trailing `rm -f "$RAW"`
# only ever runs if `age` succeeds -- if it fails for ANY reason (not found,
# wrong key, disk full), the raw unencrypted dump is orphaned on disk with
# no further cleanup. `trap ... EXIT` runs on every exit path, success or
# failure, so the raw dump never survives this script either way.
trap 'rm -f "$RAW"' EXIT

"$PG_DUMP_BIN" "$DATABASE_URL_DIRECT" \
  -Fc \
  -t users -t legal_queries -t query_responses -t complaints -t audit_logs -t corpus_versions \
  -f "$RAW" \
  >&2

age -r "$BACKUP_AGE_PUBLIC_KEY" -o "$ENC" "$RAW"

printf '%s\n' "$ENC"
