import { useState, type FormEvent } from "react";
import {
  summarizePoints,
  webSearchRAG,
  type PointsSummaryResult,
  type WebSearchRAGResult,
} from "../api";
import { useAgentCall } from "../hooks/useAgentCall";

type Tab = "search" | "summarize";

export function GlobalRagWidget() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("search");

  const [query, setQuery] = useState("");
  const search = useAgentCall<WebSearchRAGResult>();

  const [topic, setTopic] = useState("");
  const [text, setText] = useState("");
  const summarize = useAgentCall<PointsSummaryResult>();

  function handleSearchSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    search.run(() => webSearchRAG(query.trim(), 5));
  }

  function handleSummarizeSubmit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    summarize.run(() => summarizePoints(text.trim(), topic.trim() || "supplied text"));
  }

  return (
    <div className="rag-widget">
      {open && (
        <div className="rag-widget-panel">
          <header className="rag-widget-header">
            <div className="rag-widget-tabs">
              <button
                type="button"
                className={tab === "search" ? "rag-tab rag-tab-active" : "rag-tab"}
                onClick={() => setTab("search")}
              >
                🌐 Web Search
              </button>
              <button
                type="button"
                className={tab === "summarize" ? "rag-tab rag-tab-active" : "rag-tab"}
                onClick={() => setTab("summarize")}
              >
                📝 Summarize
              </button>
            </div>
            <button type="button" className="rag-widget-close" onClick={() => setOpen(false)} aria-label="Close">
              ✕
            </button>
          </header>

          <div className="rag-widget-body">
            {tab === "search" ? (
              <>
                <p className="panel-hint">Ask a question — answered from live Wikipedia/DuckDuckGo search results.</p>
                <form onSubmit={handleSearchSubmit} className="panel-form rag-widget-form">
                  <label>
                    Question
                    <input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="e.g. how does metformin lower blood sugar"
                      required
                    />
                  </label>
                  <button type="submit" disabled={search.loading}>
                    {search.loading ? "Searching…" : "Search"}
                  </button>
                </form>
                {search.error && <p className="panel-error">{search.error}</p>}
                {search.result && (
                  <div className="panel-result">
                    {search.result.answer ? (
                      <>
                        {search.result.confidence && (
                          <p className="panel-badge-row">
                            <span className="panel-badge">confidence: {search.result.confidence}</span>
                          </p>
                        )}
                        <h4>Answer</h4>
                        <p>{search.result.answer}</p>
                        {search.result.key_points.length > 0 && (
                          <>
                            <h4>Key points</h4>
                            <ul>
                              {search.result.key_points.map((point, i) => (
                                <li key={i}>{point}</li>
                              ))}
                            </ul>
                          </>
                        )}
                        {search.result.sources.length > 0 && (
                          <>
                            <h4>Sources</h4>
                            <ul>
                              {search.result.sources.map((source) => (
                                <li key={source.url}>
                                  <a href={source.url} target="_blank" rel="noreferrer">
                                    {source.title}
                                  </a>{" "}
                                  <span className="panel-muted">({source.source})</span>
                                </li>
                              ))}
                            </ul>
                          </>
                        )}
                      </>
                    ) : (
                      <p className="panel-empty">No web search results found for that question — try rephrasing it.</p>
                    )}
                  </div>
                )}
              </>
            ) : (
              <>
                <p className="panel-hint">Paste any text — get back a bulleted summary, not prose.</p>
                <form onSubmit={handleSummarizeSubmit} className="panel-form rag-widget-form">
                  <label>
                    Topic (optional)
                    <input
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder="e.g. Metformin"
                    />
                  </label>
                  <label>
                    Text to summarize
                    <textarea
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      rows={6}
                      placeholder="Paste an article, abstract, or report excerpt…"
                      required
                    />
                  </label>
                  <button type="submit" disabled={summarize.loading}>
                    {summarize.loading ? "Summarizing…" : "Summarize"}
                  </button>
                </form>
                {summarize.error && <p className="panel-error">{summarize.error}</p>}
                {summarize.result && (
                  <div className="panel-result">
                    {summarize.result.points.length > 0 ? (
                      <>
                        {summarize.result.title && <h4>{summarize.result.title}</h4>}
                        <ul>
                          {summarize.result.points.map((point, i) => (
                            <li key={i}>{point}</li>
                          ))}
                        </ul>
                        {summarize.result.key_takeaway && (
                          <p className="panel-badge-row">
                            <span className="panel-badge">Key takeaway: {summarize.result.key_takeaway}</span>
                          </p>
                        )}
                      </>
                    ) : (
                      <p className="panel-empty">Nothing to summarize — paste some text first.</p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      <button
        type="button"
        className="rag-widget-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label="Open research assistant"
      >
        {open ? "✕" : "✨"}
      </button>
    </div>
  );
}
