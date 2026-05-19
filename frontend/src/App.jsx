const { useEffect, useMemo, useState } = React;

const defaultHeaders = '{\n  "Accept-Language": "en-US,en;q=0.9"\n}';

const samples = [
  "https://example.com",
  "https://www.python.org",
  "https://www.promptingguide.ai/",
];

function Icon({ name, size = 18 }) {
  return <i data-lucide={name} style={{ width: size, height: size }} aria-hidden="true"></i>;
}

function parseUrls(value) {
  const urls = value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);

  return urls.length === 1 ? urls[0] : urls;
}

function parseHeaders(value) {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return JSON.parse(trimmed);
}

function statusIcon(status) {
  if (status === "success") {
    return "check";
  }
  if (status === "invalid_url") {
    return "link";
  }
  if (status === "timeout") {
    return "clock-alert";
  }
  if (status === "empty_content") {
    return "file-x";
  }
  return "triangle-alert";
}

function App() {
  const [apiBase, setApiBase] = useState("http://127.0.0.1:8007");
  const [urls, setUrls] = useState("https://example.com");
  const [headers, setHeaders] = useState(defaultHeaders);
  const [proxy, setProxy] = useState("");
  const [extractSummary, setExtractSummary] = useState(true);
  const [extractLinks, setExtractLinks] = useState(true);
  const [health, setHealth] = useState({ state: "checking", label: "Checking" });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [response, setResponse] = useState(null);
  const [tab, setTab] = useState("formatted");
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const endpoint = useMemo(() => `${apiBase.replace(/\/$/, "")}/scrape`, [apiBase]);
  const results = response?.results || [];
  const successCount = results.filter((item) => item.status === "success").length;
  const urlItems = useMemo(() => {
    const parsed = parseUrls(urls);
    return Array.isArray(parsed) ? parsed : parsed ? [parsed] : [];
  }, [urls]);
  const headersValid = useMemo(() => {
    try {
      parseHeaders(headers);
      return true;
    } catch (err) {
      return false;
    }
  }, [headers]);

  useEffect(() => {
    if (window.lucide) {
      window.lucide.createIcons();
    }
  });

  async function checkHealth() {
    setHealth({ state: "checking", label: "Checking" });
    try {
      const res = await fetch(`${apiBase.replace(/\/$/, "")}/health`);
      const data = await res.json();
      setHealth({
        state: data.database === "connected" ? "ok" : "error",
        label: data.database === "connected" ? "Connected" : "DB offline",
      });
    } catch (err) {
      setHealth({ state: "error", label: "Offline" });
    }
  }

  useEffect(() => {
    checkHealth();
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setIsLoading(true);
    setError("");
    setResponse(null);

    try {
      const payload = {
        urls: parseUrls(urls),
        custom_headers: parseHeaders(headers),
        proxy: proxy.trim() || null,
        extract_summary: extractSummary,
        extract_links: extractLinks,
      };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }

      setResponse(data);
      setTab("formatted");
      await checkHealth();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  function clearForm() {
    setUrls("");
    setHeaders("");
    setProxy("");
    setResponse(null);
    setError("");
  }

  function addSample(url) {
    setUrls((current) => {
      const existing = current.trim();
      if (!existing) {
        return url;
      }
      if (existing.includes(url)) {
        return existing;
      }
      return `${existing}\n${url}`;
    });
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Icon name="sparkles" size={22} />
          </div>
          <div>
            <h1>MicroScraper Studio</h1>
            <span>FastAPI at {apiBase.replace("http://", "")}</span>
          </div>
        </div>

        <div className="top-actions">
          <button className={`health-chip ${health.state}`} onClick={checkHealth} type="button">
            <Icon name={health.state === "ok" ? "database" : "server-crash"} size={16} />
            {health.label}
          </button>
        </div>
      </header>

      <section className="workspace">
        <form className="control-panel" onSubmit={handleSubmit}>
          <div className="panel-heading">
            <div>
              <span className="section-kicker">Request</span>
              <h2>Scrape run</h2>
            </div>
            <div className="request-stats">
              <span>
                <Icon name="globe-2" size={15} />
                {urlItems.length} {urlItems.length === 1 ? "URL" : "URLs"}
              </span>
              <span className={headersValid ? "valid" : "invalid"}>
                <Icon name={headersValid ? "check" : "triangle-alert"} size={15} />
                Headers
              </span>
            </div>
          </div>

          <div className="field compact-field">
            <div className="label-row">
              <label htmlFor="apiBase">API base</label>
              <button className="text-action" type="button" onClick={checkHealth}>
                <Icon name="refresh-cw" size={14} />
                Check
              </button>
            </div>
            <div className="input-shell">
              <Icon name="radio-tower" size={17} />
              <input
                id="apiBase"
                value={apiBase}
                onChange={(event) => setApiBase(event.target.value)}
              />
            </div>
          </div>

          <div className="endpoint-card">
            <span>POST</span>
            <code>/scrape</code>
            <small>{extractSummary ? "summary" : "no summary"} · {extractLinks ? "links" : "no links"}</small>
          </div>

          <section className="request-card url-card">
            <div className="request-card-head">
              <div>
                <h3>Target pages</h3>
                <p>Paste one URL per line or separate them with commas.</p>
              </div>
              <span>{urlItems.length || 0}</span>
            </div>

            <textarea
              id="urls"
              className="url-box"
              value={urls}
              onChange={(event) => setUrls(event.target.value)}
              placeholder="https://example.com&#10;https://www.python.org"
              required
            />

            <div className="sample-row">
              {samples.map((sample) => (
                <button key={sample} type="button" onClick={() => addSample(sample)}>
                  <Icon name="plus" size={14} />
                  {new URL(sample).hostname.replace("www.", "")}
                </button>
              ))}
            </div>
          </section>

          <div className="switch-grid request-card">
            <label className="switch-card">
              <input
                type="checkbox"
                checked={extractSummary}
                onChange={(event) => setExtractSummary(event.target.checked)}
              />
              <span>
                <Icon name="file-text" size={18} />
                <strong>Summary</strong>
                <small>Short preview</small>
              </span>
            </label>

            <label className="switch-card">
              <input
                type="checkbox"
                checked={extractLinks}
                onChange={(event) => setExtractLinks(event.target.checked)}
              />
              <span>
                <Icon name="link-2" size={18} />
                <strong>Links</strong>
                <small>Internal URLs</small>
              </span>
            </label>
          </div>

          <section className="advanced-card">
            <button
              className="advanced-toggle"
              type="button"
              onClick={() => setAdvancedOpen((open) => !open)}
            >
              <span>
                <Icon name="sliders-horizontal" size={17} />
                Advanced request
              </span>
              <Icon name={advancedOpen ? "chevron-up" : "chevron-down"} size={18} />
            </button>

            <div className={`advanced-body ${advancedOpen ? "open" : ""}`}>
              <div className="field">
                <div className="label-row">
                  <label htmlFor="headers">Headers JSON</label>
                  <span className={`mini-status ${headersValid ? "valid" : "invalid"}`}>
                    {headersValid ? "Valid" : "Invalid"}
                  </span>
                </div>
                <textarea
                  id="headers"
                  value={headers}
                  onChange={(event) => setHeaders(event.target.value)}
                  spellCheck="false"
                />
              </div>

              <div className="field">
                <label htmlFor="proxy">Proxy</label>
                <div className="input-shell">
                  <Icon name="shield" size={17} />
                  <input
                    id="proxy"
                    value={proxy}
                    onChange={(event) => setProxy(event.target.value)}
                    placeholder="http://user:pass@host:port"
                  />
                </div>
              </div>
            </div>
          </section>

          <div className="actions">
            <button className="btn primary" disabled={isLoading} type="submit">
              <Icon name={isLoading ? "loader-circle" : "play"} size={18} />
              {isLoading ? "Scraping" : `Run ${urlItems.length || 1} scrape`}
            </button>
            <button className="btn icon-btn" type="button" onClick={clearForm} title="Clear">
              <Icon name="rotate-ccw" size={18} />
            </button>
          </div>
        </form>

        <section className="results-panel">
          <div className="results-hero">
            <div>
              <span className="section-kicker">Results</span>
              <h2>{results.length ? `${successCount}/${results.length} completed` : "Ready"}</h2>
            </div>
            <div className="metric-strip">
              <span>
                <Icon name="clock-3" size={15} />
                {results[0]?.duration_ms ? `${results[0].duration_ms} ms` : "0 ms"}
              </span>
              <span>
                <Icon name="layers-3" size={15} />
                {results.length} pages
              </span>
            </div>
          </div>

          <div className="tabs">
            <button
              className={`tab ${tab === "formatted" ? "active" : ""}`}
              onClick={() => setTab("formatted")}
              type="button"
            >
              <Icon name="layout-list" size={16} />
              Results
            </button>
            <button
              className={`tab ${tab === "json" ? "active" : ""}`}
              onClick={() => setTab("json")}
              type="button"
            >
              <Icon name="braces" size={16} />
              JSON
            </button>
          </div>

          <div className="results-body">
            {error && (
              <div className="notice error">
                <Icon name="triangle-alert" size={18} />
                <p>{error}</p>
              </div>
            )}

            {!error && !response && (
              <div className="empty-state">
                <div className="empty-visual">
                  <Icon name="scan-search" size={42} />
                </div>
                <strong>No runs yet</strong>
                <span>Waiting for the first scrape.</span>
              </div>
            )}

            {response && tab === "json" && (
              <pre className="json-view">{JSON.stringify(response, null, 2)}</pre>
            )}

            {response && tab === "formatted" && (
              <div className="result-list">
                {results.map((item, index) => (
                  <article className="result-card" key={`${item.url}-${index}`}>
                    <div className="result-head">
                      <div className="favicon-tile">
                        <Icon name={statusIcon(item.status)} size={18} />
                      </div>
                      <div className="result-title">
                        <strong>{item.title || "Untitled page"}</strong>
                        <a href={item.url} target="_blank" rel="noreferrer">
                          {item.url}
                        </a>
                      </div>
                      <span className={`badge ${item.status}`}>{item.status}</span>
                    </div>

                    <div className="result-content">
                      <div className="result-meta">
                        {item.duration_ms !== null && item.duration_ms !== undefined && (
                          <span>
                            <Icon name="timer" size={14} />
                            {item.duration_ms} ms
                          </span>
                        )}
                        {item.links?.length > 0 && (
                          <span>
                            <Icon name="link-2" size={14} />
                            {item.links.length} links
                          </span>
                        )}
                      </div>

                      {item.error && (
                        <div className="notice error">
                          <Icon name="triangle-alert" size={18} />
                          <p>{item.error}</p>
                        </div>
                      )}

                      {item.summary && <p className="summary">{item.summary}</p>}

                      {item.links && item.links.length > 0 && (
                        <div className="links">
                          {item.links.slice(0, 8).map((link) => (
                            <a href={link} key={link} target="_blank" rel="noreferrer">
                              {link}
                            </a>
                          ))}
                        </div>
                      )}

                      {item.markdown && (
                        <pre className="markdown-preview">{item.markdown.slice(0, 4000)}</pre>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
