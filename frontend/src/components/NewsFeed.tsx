import { useEffect, useState } from "react";
import { fetchNews, type NewsFeedResult, type NewsItem } from "../api";
import { useTheme } from "../hooks/useTheme";

const COLUMNS: { category: NewsItem["category"]; icon: string; title: string }[] = [
  { category: "breakthrough", icon: "🔬", title: "Research Breakthroughs" },
  { category: "drug_discovery", icon: "💊", title: "New Drug Discoveries" },
  { category: "announcement", icon: "🏛️", title: "Government & Health Authority Announcements" },
];

function formatDate(date: string | null): string | null {
  if (!date) return null;
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return date;
  return parsed.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function NewsCard({ item }: { item: NewsItem }) {
  const date = formatDate(item.date);
  return (
    <article className="news-card">
      <a href={item.url} target="_blank" rel="noreferrer" className="news-card-title">
        {item.title}
      </a>
      <p className="news-card-meta">
        {item.source}
        {date ? ` · ${date}` : ""}
      </p>
      {item.summary && <p className="news-card-summary">{item.summary}</p>}
    </article>
  );
}

export function NewsFeed() {
  const [data, setData] = useState<NewsFeedResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { theme, toggleTheme } = useTheme();

  function load() {
    setLoading(true);
    setError(null);
    fetchNews()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  return (
    <div className="news-feed">
      <div className="news-feed-header">
        <div>
          <h2>Latest Medical News</h2>
          <p className="panel-description">Research breakthroughs, drug discoveries, and health-authority announcements.</p>
        </div>
        <div className="news-feed-actions">
          <button type="button" className="news-refresh" onClick={load} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <button type="button" className="news-refresh theme-toggle" onClick={toggleTheme}>
            {theme === "dark" ? "☀️ Light mode" : "🌙 Dark mode"}
          </button>
        </div>
      </div>

      {error && <p className="panel-error">{error}</p>}

      <div className="news-columns">
        {COLUMNS.map(({ category, icon, title }) => {
          const items = data?.[category] ?? [];
          const columnError = data?.errors?.[category];
          return (
            <section className="news-column" key={category}>
              <h3>
                <span aria-hidden="true">{icon}</span> {title}
              </h3>
              {loading && !data && <p className="panel-hint">Loading…</p>}
              {columnError && <p className="panel-hint">This source is temporarily unavailable.</p>}
              {!loading && items.length === 0 && !columnError && (
                <p className="panel-empty">Nothing new right now.</p>
              )}
              <div className="news-column-items">
                {items.map((item, i) => (
                  <NewsCard item={item} key={`${item.url}-${i}`} />
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
