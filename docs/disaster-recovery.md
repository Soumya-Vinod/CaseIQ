# Disaster recovery — backups, restore drill, run log

Scoping and design reasoning live in `docs/deployment.md`'s backup-planning entry and
`docs/evaluation.md` (the pg_dump version-mismatch incident, in two parts). This file is the
operational reference: what's backed up, how to actually restore, and a log of when this was
actually run, not just designed — a plan that's never been executed is a claim, not a backup.

## What's backed up, and why exactly this set

`scripts/backup_dump.sh` dumps six tables: `users`, `legal_queries`, `query_responses`,
`complaints`, `audit_logs`, `corpus_versions`. The first five are the "unrecoverable set" —
identity, conversation history, complaint drafts (real unredacted PII), and forensic/audit
history, none of it rebuildable from anything else this project tracks. `corpus_versions` is
there for a narrower reason: `query_responses.corpus_version_id` carries a real FK to it, and
every row has it populated — without it, a restore either fails the FK check or leaves every
historical answer's snapshot reference dangling. It's ~32kB and doesn't change the
"rebuildable vs. backed up" framing, it just keeps restored data internally consistent.

**Deliberately NOT backed up**: the corpus itself (`acts`, `section_versions`,
`offence_attributes`, `judicial_status`, `amendments`) — rebuildable from the five source-act
PDFs (now tracked in `caseiq-fastapi/documents/`, see `docs/deployment.md`, "The repo is public")
plus `scripts/ingest_*`. One caveat worth keeping current: `documents/provenance.json`'s
re-download path (as opposed to the tracked local files) only ever worked for 3 of 5 acts (BNS,
IPC, CrPC had a recorded `source_url`; BNSS and BSA never did) — and as of the 2026-09-09 check,
2 of those 3 URLs (IPC, CrPC) were already returning live 404s. The tracked local PDFs are the
real recovery path for the corpus, not the URLs.

## Where backups live

Nightly (`.github/workflows/db-backup.yml`, 02:17 UTC) plus on-demand via `workflow_dispatch`.
Dumped, encrypted with `age` (recipient/public-key mode — the workflow only ever encrypts, never
holds a private key), and pushed to `Soumya-Vinod/caseiq-backups` — a separate, private repo, not
this one. Retention: last 30 dumps kept, older ones pruned in the same workflow run.

## Restoring for real (disaster scenario, not a drill)

1. Clone `caseiq-backups` locally: `git clone https://github.com/Soumya-Vinod/caseiq-backups.git`
2. Pick the dump to restore from (`dumps/backup-<timestamp>.dump.age`) — the most recent one
   unless the incident means you want an earlier point.
3. Decrypt with the production `age` private key (in your password manager, never anywhere else):
   `age -d -i key.txt -o backup.dump dumps/backup-<timestamp>.dump.age`
4. Stand up a target Postgres — a fresh Neon branch/project for a real recovery, or see
   `scripts/restore_drill.sh` for the local-Docker-container path used for drills.
5. **Migrate to the schema revision the dump was actually taken under, not blindly `head`** — found
   live, 2026-09-12: a dump taken before `0011_hash_legal_query_ip` (which renames
   `legal_queries.ip_address` -> `ip_hash`) failed to `pg_restore --data-only` into a schema already
   migrated past it — the dump's own `COPY` statement names the pre-rename column, which the new
   schema doesn't have. `pg_restore` continued past the one broken table (`errors ignored on
   restore: 1`) rather than aborting, so this fails quietly enough to miss if you're not checking
   per-table row counts after. Any column-renaming migration landing after a given dump was taken
   creates this same trap. If you don't know which revision the dump predates, restore into the
   schema at `head` MINUS whatever renames have landed since backups started, or safer: migrate to
   the dump's own approximate era first, restore, then run the remaining migrations forward on the
   now-populated data (renames on real rows are the correct, tested path — this is exactly how
   0011's own backfill was verified, see `docs/evaluation.md`).
6. `alembic upgrade head` (if not already there) against the target to build the rest of the schema.
7. `pg_restore --data-only --disable-triggers --no-owner --no-privileges -d <target-url> backup.dump`
8. Rebuild the corpus separately (`python -m scripts.ingest_sections --all`,
   `scripts/ingest_offence_attributes.py`, `scripts/ingest_bnss_offence_attributes.py`,
   `scripts/seed_judicial_status.py` — see `docs/deployment.md` for the full sequence) if the
   corpus was lost too, not just the backed-up tables.
9. Point the app at the target and verify — `/health`, a real `/legal/query` call.

`scripts/restore_drill.sh` automates steps 3, 6, and 7 (decrypt, `alembic upgrade head`, data-only
restore, plus the row-count/content-hash verification) — pass `EXISTING_ENC_PATH` to run it against
a real downloaded backup instead of a freshly-generated one; see the script's own header for the
full option list. It does NOT implement step 5's migrate-to-the-dump's-era judgment call — it
always goes straight to `head`, which is correct for a same-day dump and wrong for a dump that
predates a renaming migration. Check which case you're in before trusting it blindly on an old dump.

## Run log

### 2026-09-12 — first real end-to-end run, executed, not just designed

**Getting the workflow to actually pass took three attempts** (`docs/evaluation.md` has the full
arc): pg_dump 17 refusing a Postgres 18 server; the "fixed" `postgresql-client` install still
resolving to pg_dump 16 on the runner because the unversioned package name didn't force PGDG's
build; and only settled by a debug step that queried the runner directly, which found
`postgresql-client-16` and `-18` installed side by side with Debian's `pg_wrapper` resolving
plain `pg_dump` to 16 regardless. Fixed by calling `pg_dump` at an absolute path (`PG_DUMP_BIN`),
not through PATH at all.

**Once it passed**: `backup-20260912T061329Z.dump.age` landed in `caseiq-backups/dumps/` — the
only file there, so the 30-dump retention prune correctly did nothing (checked directly against
the cloned repo, not assumed: `ls dumps/*.dump.age` returns exactly one file, `git log` shows
exactly one commit).

**The user then independently verified the chain, separately from any script**: cloned
`caseiq-backups` locally, decrypted `backup-20260912T061329Z.dump.age` with their own production
`age` private key (from their password manager, never handed to this assistant or committed
anywhere), got a clean `backup.dump` with no error. This is the one link in the chain the
assistant cannot itself exercise — the production private key never leaves the user's own
custody — and it was the one actually run.

**Then `restore_drill.sh` ran against that same downloaded file**
(`EXISTING_ENC_PATH=D:\...\caseiq-backups\dumps\backup-20260912T061329Z.dump.age`) — not a freshly
generated dump that never left the machine, which would have proven only that the script works,
not that the real backup does. Restored into a disposable local Postgres 17 + pgvector container
(Docker, `caseiq-test-db`'s image, a separate throwaway database within it). Verified by row count
**and** content hash (not just counts — a restore that loads the right number of wrong rows would
pass a count-only check) for all 6 tables, against the live Neon source at drill time:

| Table | Rows | Match |
|---|---|---|
| `users` | 5 | row count + content hash identical |
| `legal_queries` | 69 | row count + content hash identical |
| `query_responses` | 69 | row count + content hash identical |
| `complaints` | 16 | row count + content hash identical |
| `audit_logs` | 974 | row count + content hash identical |
| `corpus_versions` | 1 | row count + content hash identical |

**What this run proved**: the actual chain — real `pg_dump` against production, real `age`
encryption with the real production keypair, a real push to the real private repo, a real
independent pull-and-decrypt by the human who holds the only private key, and a real restore of
that exact file — works, today, verified rather than assumed at every link.

**What this run did NOT cover (Tier 2, not yet run)**: booting the actual FastAPI app against a
fully rebuilt database — this backup's 6 tables restored *plus* the corpus re-ingested from the
tracked PDFs — and issuing a real `/legal/query` call against it. That needs a Postgres with
pgvector positioned as a stand-in for "the corpus is really gone too," not just "the unrecoverable
tables are gone." Pending either a Neon branch or a local pgvector rehearsal, scoped but not
scheduled as of this entry.

### 2026-09-12, same day — `legal_queries.ip_hash` verified against a real restored copy, not synthetic data

`alembic/versions/0011_hash_legal_query_ip.py` (rename) and `scripts/backfill_legal_query_ip_hash.py`
(hash the pre-existing rows, since unlike `0003_hash_audit_ip` this table already had real data)
were verified by actually restoring the day's real backup — the same `backup-20260912T061329Z.dump.age`
above — into a disposable local database, not by reasoning about the migration or testing against
synthetic rows.

**Found in the process**: restoring that dump directly into a schema already at `head` (past
0011) failed for `legal_queries` specifically — the dump's `COPY` statement names the pre-rename
`ip_address` column, which the post-rename schema doesn't have. `pg_restore` logged one ignored
error and moved on rather than aborting. Corrected by migrating to the schema revision the dump
actually predates (`0010_embedding_model_identity`), restoring there (column names match, all 69
rows load with their real raw IPs intact), then upgrading to `head` — the rename applies to
already-populated data, exactly the sequence production will go through. Written up as its own
step in "Restoring for real" above so the next person doesn't lose time to the same silent partial
failure.

**Backfill verified exactly, not just "ran without error"**: pre-backfill, the 4 distinct raw
values in this restored copy were `127.0.0.1`, `182.48.225.230`, `182.48.224.191`, `testclient`.
Post-backfill, the 4 distinct `ip_hash` values matched `app.core.security.hash_ip()` computed
independently on those same 4 inputs, one-to-one, exactly. Re-running the backfill afterward
(`--dry-run`) found 0 rows still needing hashing, confirming the idempotency check does what it
claims. Full suite re-run after the model/code changes: **132 passed, 0 failed**.

**Not yet run against production** — this migration and backfill are built and verified against a
real (restored, disposable) copy of the real data, but have not yet been applied to the live Neon
database. Hashing is one-way; running the backfill against production is not something to redo if
it turns out wrong. Held for explicit go-ahead rather than run as part of this verification pass.

### 2026-09-12, later the same day — the backup was used for real, not just drilled

Before running the `ip_hash` migration/backfill against production, a fresh on-demand backup was
triggered specifically so a same-minute recovery point existed for a one-way operation, rather than
relying on Neon's 6-hour PITR. It was needed within the hour: the first production backfill run
hashed all 69 rows with the wrong `SECRET_KEY` (a leftover local-testing override never cleared) —
see `docs/evaluation.md`'s "wrong-but-valid-looking write" entry for the full incident. The fresh
backup's raw IPs were restored locally and used to recompute and correct all 69 rows with the real
key. **This is the first time this project's backup existed to solve a real problem rather than
being drilled against a hypothetical one** — the exact reason "actually run it, not just design it"
was the standard held throughout this whole effort.
