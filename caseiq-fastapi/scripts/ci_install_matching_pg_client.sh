#!/usr/bin/env bash
# CI-only: installs a postgresql-client package matching the ACTUAL major
# version of whatever server $1 points at, determined at runtime via psql
# -- never a hardcoded version number. psql's own simple query protocol
# tolerates cross-version use far better than pg_dump's archive format
# does, so the runner's already-installed default psql is fine for this
# one probe query regardless of which major it happens to be.
#
# Every workflow in this repo that needs pg_dump/pg_restore installs
# through this script -- see docs/evaluation.md, "a fix applied to the
# place it was found, not everywhere it belonged": this project talks to
# at least two servers with two different major versions already (Neon:
# 18, the nightly eval's Postgres service container: 17), and a workflow
# that hardcodes either one is the same mistake with extra steps. Once
# the matching package is installed, scripts/lib/pg_bin.sh's
# resolve_pg_bin() is what actually picks the right binary at use time --
# installing the right package alone isn't enough (Debian's own
# pg_wrapper doesn't reliably resolve plain `pg_dump` on PATH to the
# newest installed major when more than one is present, confirmed live).
#
# Usage (a GitHub Actions step):
#   run: caseiq-fastapi/scripts/ci_install_matching_pg_client.sh "${{ secrets.NEON_DATABASE_URL_DIRECT }}"
set -euo pipefail
: "${1:?usage: ci_install_matching_pg_client.sh <target_url>}"

SERVER_VERSION_NUM="$(psql "$1" -tAc 'SHOW server_version_num;' | tr -d '[:space:]')"
SERVER_MAJOR=$((SERVER_VERSION_NUM / 10000))
echo "target server is Postgres $SERVER_MAJOR -- installing postgresql-client-$SERVER_MAJOR"

sudo apt-get install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
sudo apt-get install -y "postgresql-client-$SERVER_MAJOR"
