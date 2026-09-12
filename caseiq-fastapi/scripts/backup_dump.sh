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
#   PG_DUMP_BIN              -- path/name of the pg_dump binary to use.
#                                Defaults to plain `pg_dump` (correct on a
#                                normal machine). Override with an absolute
#                                path where PATH resolution can't be trusted
#                                to give the version you actually installed
#                                -- see the version-assertion comment below
#                                for why that's not hypothetical.
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

# FIXED 2026-09-12, found live in the actual GitHub Actions run this exists
# for, not locally: a fix verified on this machine (pg_dump 18 installed
# here) that didn't hold in the environment it was actually written for.
# Two follow-on guesses at why ALSO didn't hold until a debug step actually
# printed what was on the runner -- see docs/evaluation.md for the full
# arc; the short version is postgresql-client-16 and -18 end up installed
# side by side, and Debian's pg_wrapper resolves plain `pg_dump` on PATH to
# 16 regardless. PG_DUMP_BIN exists because of that: defaults to plain
# `pg_dump` (correct on this machine, and anywhere PATH isn't wrapper-
# managed), and the workflow overrides it to an absolute path so it isn't
# subject to the wrapper's own resolution at all -- not fighting the
# wrapper, going around it.
PG_DUMP_BIN="${PG_DUMP_BIN:-pg_dump}"

# This assertion is what makes a pg_dump/server drift loud instead of an
# eventual pg_dump error message that happens to be legible on ONE side of
# the mismatch (pg_dump refuses a NEWER server; it does not reliably refuse
# an OLDER one, which can silently succeed while assuming server-side
# behaviour that isn't there). Same principle as
# assert_embedding_config_matches_corpus: two independently-changeable
# things -- whichever pg_dump PG_DUMP_BIN actually resolves to, and Neon's
# actual server version -- must be checked to agree, not assumed to, in
# either direction. Runs before anything else in this script, every time.
PG_DUMP_MAJOR="$("$PG_DUMP_BIN" --version | grep -oE '[0-9]+' | head -1)"
SERVER_VERSION_NUM="$(psql "$DATABASE_URL_DIRECT" -tAc 'SHOW server_version_num;' | tr -d '[:space:]')"
SERVER_MAJOR="$((SERVER_VERSION_NUM / 10000))"
if [ "$PG_DUMP_MAJOR" != "$SERVER_MAJOR" ]; then
  echo "FATAL: pg_dump ($PG_DUMP_BIN) major version ($PG_DUMP_MAJOR) does not" \
       "match the server's major version ($SERVER_MAJOR) -- refusing to dump." \
       "Install/point PG_DUMP_BIN at a pg_dump matching the server, don't just retry." >&2
  exit 1
fi

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
