"""Helper for restore_drill.sh's own last step -- not meant to be run
standalone. Compares row counts AND a content hash (not just counts --
counts alone can't tell a byte-for-byte-correct restore from one that
silently restored the right number of DIFFERENT rows) for every table in
the backed-up set, between the real source and the freshly restored target.
Exits non-zero and prints exactly what mismatched if anything does.

Usage: python _restore_drill_verify.py <source_url> <target_url>
"""
from __future__ import annotations

import sys

import asyncpg

# One content-hash expression per table -- deliberately excludes id/
# created_at/updated_at (a restore assigns identical values for these from
# the dump, so including them isn't wrong, but the columns actually worth
# proving are the ones a subtly-broken dump/restore step could silently
# corrupt: real column data, not just row identity).
TABLES: dict[str, str] = {
    "users": "email || hashed_password || coalesce(phone,'') || coalesce(state,'')",
    "legal_queries": "original_query || coalesce(session_id,'') || coalesce(ip_address,'')",
    "query_responses": "conversational_summary || structured_data::text || coalesce(corpus_version_id::text,'')",
    "complaints": "complainant_name || complainant_address || incident_description || accused_details",
    "audit_logs": "action || coalesce(ip_hash,'') || coalesce(request_id,'')",
    "corpus_versions": "coalesce(label,'') || coalesce(checksum,'')",
}


async def _connect(url: str) -> asyncpg.Connection:
    try:
        return await asyncpg.connect(url, ssl="require", statement_cache_size=0)
    except (ConnectionError, OSError):
        return await asyncpg.connect(url)


async def _snapshot(conn: asyncpg.Connection, table: str, expr: str) -> tuple[int, str | None]:
    count = await conn.fetchval(f"SELECT count(*) FROM {table}")
    digest = await conn.fetchval(
        f"SELECT md5(string_agg({expr}, ',' ORDER BY id)) FROM {table}"
    )
    return count, digest


async def main(source_url: str, target_url: str) -> int:
    src = await _connect(source_url)
    tgt = await _connect(target_url)
    failures: list[str] = []
    try:
        for table, expr in TABLES.items():
            s_count, s_hash = await _snapshot(src, table, expr)
            t_count, t_hash = await _snapshot(tgt, table, expr)
            ok = s_count == t_count and s_hash == t_hash
            print(f"  {table}: source={s_count} rows target={t_count} rows "
                  f"{'MATCH' if ok else 'MISMATCH'}")
            if not ok:
                failures.append(
                    f"{table}: counts {s_count}/{t_count}, hashes {s_hash}/{t_hash}"
                )
    finally:
        await src.close()
        await tgt.close()

    if failures:
        print(f"\nFAILED: {len(failures)} table(s) did not match")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nALL TABLES MATCH -- row counts and content hashes identical")
    return 0


if __name__ == "__main__":
    import asyncio

    sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2])))
