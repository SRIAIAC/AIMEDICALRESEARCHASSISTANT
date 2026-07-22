import { useState, type FormEvent } from "react";
import { askDocuments, uploadDocument, type DocumentQAResult, type DocumentUploadResult } from "../../api";
import { useAgentCall } from "../../hooks/useAgentCall";
import { PanelShell } from "../PanelShell";

export function DocumentUploadPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [copied, setCopied] = useState(false);
  const upload = useAgentCall<DocumentUploadResult>();

  const [question, setQuestion] = useState("");
  const qa = useAgentCall<DocumentQAResult>();

  function handleUploadSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setCopied(false);
    upload.run(() => uploadDocument(file));
  }

  function handleAskSubmit(e: FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    qa.run(() => askDocuments(question.trim()));
  }

  function handleCopy() {
    if (!upload.result?.text) return;
    navigator.clipboard.writeText(upload.result.text).then(() => setCopied(true));
  }

  return (
    <PanelShell
      icon="📄"
      title="Document Upload & Q&A"
      description="Upload a PDF (OCR runs automatically on scanned pages) and index it, then ask questions answered with retrieval-augmented generation over everything indexed — your documents plus any PubMed abstracts already gathered by Literature Review."
    >
      <form onSubmit={handleUploadSubmit} className="panel-form">
        <label>
          PDF file
          <input
            type="file"
            accept=".pdf,application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
        </label>
        <button type="submit" disabled={upload.loading || !file}>
          {upload.loading ? "Extracting…" : "Upload & extract"}
        </button>
      </form>
      {upload.loading && (
        <p className="panel-hint">
          Extracting text, OCR&apos;ing any scanned pages, and indexing — this can take a little while for
          larger PDFs.
        </p>
      )}
      {upload.error && <p className="panel-error">{upload.error}</p>}
      {upload.result && (
        <div className="panel-result">
          <p className="panel-badge-row">
            <span className="panel-badge">
              {upload.result.page_count} page{upload.result.page_count === 1 ? "" : "s"}
            </span>
            <span className="panel-badge">{upload.result.chunks_indexed} chunks indexed</span>
            {upload.result.ocr_pages.length > 0 && (
              <span className="panel-badge">
                OCR used on page{upload.result.ocr_pages.length === 1 ? "" : "s"}{" "}
                {upload.result.ocr_pages.join(", ")}
              </span>
            )}
          </p>
          {upload.result.text ? (
            <>
              <h4>Extracted text</h4>
              <div className="document-text-preview">{upload.result.text}</div>
              <button type="button" className="document-copy-btn" onClick={handleCopy}>
                {copied ? "Copied!" : "Copy text"}
              </button>
            </>
          ) : (
            <p className="panel-empty">No text could be extracted from this PDF.</p>
          )}
        </div>
      )}

      <form onSubmit={handleAskSubmit} className="panel-form document-qa-form">
        <label>
          Ask a question about indexed documents
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What was the primary endpoint?"
            required
          />
        </label>
        <button type="submit" disabled={qa.loading}>
          {qa.loading ? "Answering…" : "Ask"}
        </button>
      </form>
      {qa.loading && <p className="panel-hint">Retrieving relevant excerpts and generating a grounded answer…</p>}
      {qa.error && <p className="panel-error">{qa.error}</p>}
      {qa.result && (
        <div className="panel-result">
          {qa.result.answer ? (
            <>
              <p className="panel-badge-row">
                {qa.result.confidence && (
                  <span className="panel-badge">confidence: {qa.result.confidence}</span>
                )}
              </p>
              <p>{qa.result.answer}</p>
              {qa.result.sources.length > 0 && (
                <>
                  <h4>Retrieved sources</h4>
                  <ul className="panel-sources">
                    {qa.result.sources.map((s) => (
                      <li key={s.id}>
                        <strong>
                          {qa.result!.supporting_sources.includes(s.id) ? "✓ " : ""}
                          {s.label}
                        </strong>
                        <br />
                        <span className="panel-muted">{s.excerpt}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : (
            <p className="panel-empty">
              Nothing relevant is indexed yet — upload a document or run a Literature Review search first.
            </p>
          )}
        </div>
      )}
    </PanelShell>
  );
}
