#!/usr/bin/env bash
# Source this file, don't execute it. Provides resolve_pg_bin(), the ONE
# place this project decides which pg_dump/pg_restore binary to use for a
# given target connection.
#
# FIXED 2026-09-12+, third time -- see docs/evaluation.md, "A fix applied
# to the place it was found, not everywhere it belonged": scripts/
# backup_dump.sh got a pg_dump-version assertion after two real CI
# failures (Debian ships pg_dump 16 by default; Neon runs 18; installing
# 18 alongside 16 doesn't help because Debian's own pg_wrapper still
# resolves plain `pg_dump` on PATH to 16 regardless of what else is
# installed). A THIRD script (.github/workflows/nightly-eval.yml) hit the
# exact same failure shortly after, against a DIFFERENT server version
# (the eval Postgres service container, 17) -- because the fix lived in
# one script instead of a shared place. This file is that shared place.
# Every script in this repo that shells out to pg_dump or pg_restore
# must resolve the binary through this function -- never call pg_dump/
# pg_restore directly and never hardcode a version number anywhere.
#
# resolve_pg_bin <target_url> <bin_name>
#   <target_url>  -- a psql-connectable URL for the server this binary
#                     will actually be used against. Resolution is always
#                     done against the REAL target, never a hardcoded
#                     version -- this project now talks to at least two
#                     servers with two different major versions at once
#                     (Neon: 18: the local/CI eval Postgres: 17), and a
#                     fix that hardcodes either one is the same mistake
#                     with extra steps.
#   <bin_name>    -- "pg_dump" or "pg_restore" (or "psql", though psql's
#                     own wire protocol tolerates cross-version use far
#                     better than pg_dump's archive format does, so it's
#                     rarely the one that actually needs this).
#
# Prints the resolved binary's path on stdout. Returns non-zero (and
# prints a FATAL message to stderr, with both version numbers) if no
# matching binary can be found or verified -- callers should not catch
# this and retry; the fix is installing/pointing at the right binary, not
# trying again.
resolve_pg_bin() {
  local target_url="$1"
  local bin_name="$2"
  # Never echo the raw URL -- it carries credentials (a Neon connection
  # string, in this project's own real usage). Same discipline as
  # app.core.config.DATABASE_HOST_FOR_LOGGING: host/db only, in every
  # message below, not the value $1 was actually called with.
  local safe_target
  safe_target="$(printf '%s' "$target_url" | sed -E 's#//[^@/]*@#//<redacted>@#')"

  local server_version_num
  server_version_num="$(psql "$target_url" -tAc 'SHOW server_version_num;' 2>/dev/null | tr -d '[:space:]')"
  if [ -z "$server_version_num" ]; then
    echo "FATAL: could not determine the server version for $safe_target (is it reachable?)" >&2
    return 1
  fi
  local server_major=$((server_version_num / 10000))

  # Debian/Ubuntu (apt, including PGDG's own repo) installs versioned
  # copies side by side under /usr/lib/postgresql/<major>/bin/ -- and
  # Debian's own pg_wrapper on PATH does NOT reliably resolve to the
  # newest, or to any particular one, when multiple majors are installed
  # (confirmed live, not assumed: `which -a pg_dump`, `dpkg -l`, and each
  # binary's own --version, run directly on a real runner -- see
  # docs/evaluation.md). Look for the exact versioned path FIRST,
  # explicitly, rather than ever trust PATH on this family of systems.
  local versioned="/usr/lib/postgresql/${server_major}/bin/${bin_name}"
  if [ -x "$versioned" ]; then
    printf '%s\n' "$versioned"
    return 0
  fi

  # Not Debian-style (a dev machine, a different distro/image, or the
  # needed major simply isn't installed under that path): fall back to
  # PATH, but VERIFY before trusting it -- this is the actual check that
  # would have caught all three incidents at the point of use, rather
  # than at install time where it's easy to get subtly wrong.
  local plain_bin
  if ! plain_bin="$(command -v "$bin_name")"; then
    echo "FATAL: no '$bin_name' on PATH and no versioned copy at $versioned" \
         "(target $safe_target is Postgres $server_major)" >&2
    return 1
  fi
  local bin_major
  bin_major="$("$plain_bin" --version | grep -oE '[0-9]+' | head -1)"
  if [ "$bin_major" != "$server_major" ]; then
    echo "FATAL: $bin_name ($plain_bin) major version ($bin_major) does not match" \
         "the target server's major version ($server_major) for $safe_target --" \
         "refusing to use it. Install/point at a $bin_name matching the server," \
         "don't just retry." >&2
    return 1
  fi
  printf '%s\n' "$plain_bin"
}
