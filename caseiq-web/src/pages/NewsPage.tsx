import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { NewsOut } from "../api/types";
import styles from "./NewsPage.module.css";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

// An explainer has no real source_url to link to (app/services/news.py never
// gives one a source_url) -- that absence is the signal, not is_featured,
// which is only true today because explainers happen to set it, not because
// the field means "explainer".
function isExplainer(article: NewsOut): boolean {
  return !article.source_url;
}

export function NewsPage() {
  const [articles, setArticles] = useState<NewsOut[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const { data, error: apiError } = await api.GET("/api/v1/awareness/news", {
          params: { query: { limit: 30 } },
        });
        if (apiError) {
          setError("Something went wrong reaching the backend. Please try again.");
          return;
        }
        setArticles(data ?? []);
      } catch {
        setError("Could not reach the server. Check your connection and try again.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <p className={styles.eyebrow}>Legal awareness</p>
        <h1 className={styles.title}>News</h1>
        <p className={styles.subtitle}>
          Real articles from real sources, with a link to the original — never generated. A few
          evergreen explainers fill in when no article exists yet; those are marked and never
          link out.
        </p>
      </header>
      <div className={styles.rule} aria-hidden="true" />

      {loading && <p className={styles.loading}>Loading…</p>}
      {error && <div className={styles.errorBox}>{error}</div>}

      {!loading && !error && articles && articles.length === 0 && (
        <div className={styles.empty}>
          <p className={styles.emptyTitle}>No news yet</p>
          <p className={styles.emptyBody}>
            Nothing has been fetched into this corpus yet — this isn't a loading problem, there's
            simply nothing here.
          </p>
        </div>
      )}

      {!loading && !error && articles && articles.length > 0 && (
        <ul className={styles.list}>
          {articles.map((a) => {
            const explainer = isExplainer(a);
            return (
              <li key={a.id}>
                <article className={styles.card}>
                  <div className={styles.metaRow}>
                    <span className={styles.source}>{a.source}</span>
                    {explainer && <span className={styles.explainerTag}>CaseIQ Explainer</span>}
                    <span className={styles.date}>{formatDate(a.published_at)}</span>
                  </div>
                  <h3 className={styles.cardTitle}>{a.title}</h3>
                  <p className={styles.summary}>{a.summary}</p>
                  {!explainer && a.source_url && (
                    <a
                      className={styles.readMore}
                      href={a.source_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Read at {a.source} ↗
                    </a>
                  )}
                </article>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
