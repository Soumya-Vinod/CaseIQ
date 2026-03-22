FROM postgres:17-alpine

RUN apk add --no-cache \
    build-base \
    postgresql-dev

COPY pgvector_src /pgvector

RUN cd /pgvector \
    && sed -i 's/with_llvm = yes/with_llvm = no/' /usr/local/lib/postgresql/pgxs/src/Makefile.global \
    && make USE_PGXS=1 PG_CONFIG=/usr/local/bin/pg_config \
    && make USE_PGXS=1 PG_CONFIG=/usr/local/bin/pg_config install \
    && cd / \
    && rm -rf /pgvector
