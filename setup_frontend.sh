#!/usr/bin/env bash
# Scaffolds the Aperture underwriter console.
# Run from the repository root:  bash setup_frontend.sh
set -euo pipefail

if [ ! -d "ml" ] || [ ! -d "backend" ]; then
  echo "Run this from the repository root (the folder containing ml/ and backend/)." >&2
  exit 1
fi

mkdir -p frontend/src/components

echo "  writing frontend/package.json"
cat > frontend/package.json << 'APERTURE_EOF_PACKAGE_JSON'
{
  "name": "aperture-console",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^5.4.11"
  }
}
APERTURE_EOF_PACKAGE_JSON

echo "  writing frontend/vite.config.js"
cat > frontend/vite.config.js << 'APERTURE_EOF_VITE_CONFIG_JS'
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The console talks to the decision API on :8000. Proxying in development
    // keeps the browser on one origin, so no CORS preflight is involved.
    proxy: {
      "/v1": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
APERTURE_EOF_VITE_CONFIG_JS

echo "  writing frontend/index.html"
cat > frontend/index.html << 'APERTURE_EOF_INDEX_HTML'
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Aperture — Underwriting Console</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
      rel="stylesheet"
    />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
APERTURE_EOF_INDEX_HTML

echo "  writing frontend/src/main.jsx"
cat > frontend/src/main.jsx << 'APERTURE_EOF_MAIN_JSX'
import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App.jsx";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
APERTURE_EOF_MAIN_JSX

echo "  writing frontend/src/styles.css"
cat > frontend/src/styles.css << 'APERTURE_EOF_STYLES_CSS'
/* Aperture console.
 *
 * The visual language is a records system, not a dashboard. Underwriting runs
 * on files, and the domain's own term for the population this product serves is
 * "thin file" -- so the interface is built around showing what is and is not in
 * an applicant's file.
 *
 * Two rules carry the personality:
 *   1. Every figure, identifier and reason code is set in monospace with
 *      tabular figures, so columns of numbers align and regulatory codes look
 *      like the artifacts they are.
 *   2. Colour is reserved for decisions. Nothing else is allowed to be bright.
 */

:root {
  /* Ledger paper and ink */
  --paper: #f1f4f2;
  --surface: #ffffff;
  --surface-sunk: #f7f9f8;
  --ink: #10201c;
  --ink-muted: #5f6f6a;
  --ink-faint: #8b9995;
  --rule: #dde5e2;
  --rule-strong: #c3d0cb;

  /* Decisions */
  --approve: #0b5d4e;
  --approve-wash: #e6f0ec;
  --refer: #9a6410;
  --refer-wash: #f7efe1;
  --decline: #99302c;
  --decline-wash: #f6e8e7;

  --accent: #0b5d4e;

  --font-ui: "Instrument Sans", -apple-system, BlinkMacSystemFont, "Segoe UI",
    sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;

  --radius: 3px;
  --shadow: 0 1px 2px rgba(16, 32, 28, 0.06), 0 4px 16px rgba(16, 32, 28, 0.04);
}

* {
  box-sizing: border-box;
}

html,
body,
#root {
  height: 100%;
  margin: 0;
}

body {
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-ui);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

.mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
}

/* ---------------------------------------------------------------- shell -- */

.app {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.masthead {
  display: flex;
  align-items: baseline;
  gap: 20px;
  padding: 14px 22px;
  background: var(--surface);
  border-bottom: 1px solid var(--rule);
}

.masthead h1 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.masthead .tagline {
  color: var(--ink-muted);
  font-size: 12.5px;
}

.masthead .spacer {
  flex: 1;
}

.model-chip {
  font-size: 11px;
  color: var(--ink-faint);
  border: 1px solid var(--rule);
  border-radius: var(--radius);
  padding: 3px 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 340px;
}

.tabs {
  display: flex;
  gap: 2px;
  padding: 0 22px;
  background: var(--surface);
  border-bottom: 1px solid var(--rule);
}

.tab {
  appearance: none;
  border: 0;
  background: none;
  font: inherit;
  font-size: 13px;
  color: var(--ink-muted);
  padding: 9px 12px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.tab:hover {
  color: var(--ink);
}

.tab[aria-selected="true"] {
  color: var(--ink);
  font-weight: 500;
  border-bottom-color: var(--accent);
}

.tab:focus-visible,
button:focus-visible,
input:focus-visible,
select:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* -------------------------------------------------------------- layout -- */

.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(360px, 460px) 1fr;
  gap: 18px;
  padding: 18px 22px;
  overflow: hidden;
}

.workspace.single {
  grid-template-columns: 1fr;
}

.pane {
  background: var(--surface);
  border: 1px solid var(--rule);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.pane-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-bottom: 1px solid var(--rule);
  background: var(--surface-sunk);
}

.pane-head h2 {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-muted);
}

.pane-head .spacer {
  flex: 1;
}

.pane-body {
  overflow-y: auto;
  flex: 1;
}

.pane-body.pad {
  padding: 16px;
}

/* --------------------------------------------------------------- queue -- */

.queue-row {
  display: block;
  width: 100%;
  text-align: left;
  appearance: none;
  border: 0;
  border-bottom: 1px solid var(--rule);
  border-left: 3px solid transparent;
  background: none;
  font: inherit;
  padding: 11px 14px;
  cursor: pointer;
}

.queue-row:hover {
  background: var(--surface-sunk);
}

.queue-row[aria-current="true"] {
  background: var(--surface-sunk);
  border-left-color: var(--accent);
}

.queue-row-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.queue-name {
  font-weight: 500;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 5px;
  font-size: 12px;
  color: var(--ink-muted);
}

/* ------------------------------------------------------------ verdicts -- */

.verdict {
  font-family: var(--font-mono);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  padding: 2px 7px;
  border-radius: var(--radius);
  white-space: nowrap;
}

.verdict.APPROVE {
  color: var(--approve);
  background: var(--approve-wash);
}
.verdict.REFER {
  color: var(--refer);
  background: var(--refer-wash);
}
.verdict.DECLINE,
.verdict.BLOCK {
  color: var(--decline);
  background: var(--decline-wash);
}
.verdict.REVIEW {
  color: var(--refer);
  background: var(--refer-wash);
}
.verdict.PASS {
  color: var(--ink-muted);
  background: var(--surface-sunk);
}

.thin-tag {
  font-size: 10.5px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--accent);
  border: 1px solid var(--rule-strong);
  border-radius: var(--radius);
  padding: 1px 6px;
}

/* ------------------------------------------- signature: evidence ticks -- */
/* Two rows of discrete marks standing in for the pages in an applicant's
 * file. A thin-file applicant shows an almost empty bureau row beside a full
 * behavioural row, which is the argument of this whole product rendered in
 * about forty pixels. */

.evidence {
  display: grid;
  gap: 5px;
}

.evidence-line {
  display: flex;
  align-items: center;
  gap: 9px;
}

.evidence-label {
  font-size: 10.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink-faint);
  width: 82px;
  flex-shrink: 0;
}

.ticks {
  display: flex;
  gap: 2px;
}

.tick {
  width: 4px;
  height: 13px;
  border-radius: 1px;
  background: var(--rule);
}

.tick.filled {
  background: var(--rule-strong);
}

.tick.filled.behavioural {
  background: var(--accent);
}

.evidence-count {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-faint);
}

/* ------------------------------------------------------------- detail -- */

.headline {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  border-bottom: 1px solid var(--rule);
}

.headline-main h3 {
  margin: 0 0 3px;
  font-size: 19px;
  font-weight: 600;
  letter-spacing: -0.015em;
}

.headline-sub {
  font-size: 12.5px;
  color: var(--ink-muted);
}

.headline .spacer {
  flex: 1;
}

.outcome-block {
  text-align: right;
}

.outcome-word {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.outcome-word.APPROVE {
  color: var(--approve);
}
.outcome-word.REFER {
  color: var(--refer);
}
.outcome-word.DECLINE {
  color: var(--decline);
}

.stat-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  border-bottom: 1px solid var(--rule);
}

.stat {
  padding: 11px 14px;
  border-right: 1px solid var(--rule);
}

.stat:last-child {
  border-right: 0;
}

.stat-label {
  font-size: 10.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink-faint);
  margin-bottom: 2px;
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.stat-value.absent {
  color: var(--ink-faint);
  font-style: italic;
  font-size: 13px;
}

.section {
  padding: 16px;
  border-bottom: 1px solid var(--rule);
}

.section:last-child {
  border-bottom: 0;
}

.section-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 11px;
}

.section-head h4 {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--ink-muted);
}

.section-note {
  font-size: 12px;
  color: var(--ink-faint);
}

/* -------------------------------------------------------- reason list -- */

.reason {
  display: grid;
  grid-template-columns: 52px 1fr auto;
  gap: 11px;
  padding: 10px 0;
  border-top: 1px solid var(--rule);
  align-items: start;
}

.reason:first-of-type {
  border-top: 0;
}

.reason-code {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--accent);
}

.reason-statement {
  font-size: 13.5px;
}

.reason-improvement {
  font-size: 12px;
  color: var(--ink-muted);
  margin-top: 2px;
}

.reason-evidence {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-faint);
  margin-top: 3px;
}

.reason-share {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ink-muted);
  text-align: right;
  white-space: nowrap;
}

/* -------------------------------------------------------- attribution -- */

.attrib-row {
  display: grid;
  grid-template-columns: 190px 1fr 62px;
  gap: 10px;
  align-items: center;
  padding: 3px 0;
}

.attrib-name {
  font-size: 12px;
  color: var(--ink-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attrib-track {
  position: relative;
  height: 15px;
  background: var(--surface-sunk);
  border-radius: 1px;
}

.attrib-axis {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--rule-strong);
}

.attrib-bar {
  position: absolute;
  top: 2px;
  bottom: 2px;
  border-radius: 1px;
}

.attrib-bar.risk {
  background: var(--decline);
  opacity: 0.75;
}

.attrib-bar.safe {
  background: var(--approve);
  opacity: 0.75;
}

.attrib-value {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-faint);
  text-align: right;
}

.attrib-legend {
  display: flex;
  gap: 16px;
  margin-top: 10px;
  font-size: 11.5px;
  color: var(--ink-faint);
}

.swatch {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 1px;
  margin-right: 5px;
}

/* --------------------------------------------------------- forms/table -- */

.field {
  display: grid;
  gap: 4px;
  margin-bottom: 11px;
}

.field label {
  font-size: 11.5px;
  color: var(--ink-muted);
}

input,
select,
textarea {
  font: inherit;
  font-size: 13px;
  padding: 7px 9px;
  border: 1px solid var(--rule-strong);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--ink);
  width: 100%;
}

input[type="number"] {
  font-family: var(--font-mono);
}

.btn {
  appearance: none;
  font: inherit;
  font-size: 13px;
  font-weight: 500;
  padding: 7px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
  cursor: pointer;
}

.btn:hover {
  filter: brightness(1.12);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn.ghost {
  background: none;
  color: var(--ink);
  border-color: var(--rule-strong);
}

.btn.small {
  font-size: 12px;
  padding: 4px 10px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

th {
  text-align: left;
  font-size: 10.5px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--ink-faint);
  font-weight: 600;
  padding: 9px 12px;
  border-bottom: 1px solid var(--rule);
  background: var(--surface-sunk);
  position: sticky;
  top: 0;
}

td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--rule);
  vertical-align: top;
}

td.mono {
  font-size: 11.5px;
  color: var(--ink-muted);
}

/* --------------------------------------------------------------- misc -- */

.empty {
  padding: 40px 20px;
  text-align: center;
  color: var(--ink-muted);
  font-size: 13px;
}

.empty strong {
  display: block;
  color: var(--ink);
  font-weight: 500;
  margin-bottom: 4px;
}

.banner {
  padding: 9px 14px;
  font-size: 12.5px;
  border-radius: var(--radius);
  margin-bottom: 12px;
}

.banner.error {
  background: var(--decline-wash);
  color: var(--decline);
}

.banner.info {
  background: var(--approve-wash);
  color: var(--approve);
}

.signal-list {
  margin: 0;
  padding-left: 17px;
  font-size: 12.5px;
  color: var(--ink-muted);
}

.override-log {
  border-left: 2px solid var(--rule-strong);
  padding-left: 11px;
  margin-top: 9px;
  font-size: 12.5px;
}

.filters {
  display: flex;
  gap: 7px;
  align-items: center;
}

.filters select {
  width: auto;
  font-size: 12px;
  padding: 4px 7px;
}

.checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ink-muted);
  white-space: nowrap;
}

.checkbox input {
  width: auto;
}

@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
    animation: none !important;
  }
}

@media (max-width: 900px) {
  .workspace {
    grid-template-columns: 1fr;
    overflow: auto;
  }
}
APERTURE_EOF_STYLES_CSS

echo "  writing frontend/src/api.js"
cat > frontend/src/api.js << 'APERTURE_EOF_API_JS'
/**
 * Single point of contact with the decision API.
 *
 * Vite proxies /v1 and /health to the backend in development, so the browser
 * stays on one origin and no CORS preflight is involved. Every call funnels
 * through `request` so error handling is uniform: FastAPI returns validation
 * failures as a `detail` array, which is flattened into one readable message
 * rather than surfacing "[object Object]" to the underwriter.
 */

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (Array.isArray(body.detail)) {
        message = body.detail
          .map((item) => `${(item.loc || []).slice(-1)[0]}: ${item.msg}`)
          .join("; ");
      } else if (body.detail) {
        message = body.detail;
      }
    } catch {
      // Response carried no JSON body; the status line is the best we have.
    }
    throw new Error(message);
  }
  return response.json();
}

export const api = {
  health: () => request("/health"),

  queue: ({ outcome = "", thinFileOnly = false, limit = 50 } = {}) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (outcome) params.set("outcome", outcome);
    if (thinFileOnly) params.set("thin_file_only", "true");
    return request(`/v1/queue?${params}`);
  },

  decision: (id) => request(`/v1/decisions/${id}`),

  decide: (payload) =>
    request("/v1/decisions", { method: "POST", body: JSON.stringify(payload) }),

  override: (id, payload) =>
    request(`/v1/decisions/${id}/override`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  ledger: ({ limit = 100 } = {}) => request(`/v1/ledger?limit=${limit}`),
};

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------
// Absent values are rendered as an explicit em dash rather than 0. A blank
// bureau score means "unknown", and showing zero would assert something false
// about the applicant -- the same principle the model follows internally.

export const fmt = {
  currency: (value) =>
    value === null || value === undefined
      ? "—"
      : `₹${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`,

  percent: (value, digits = 1) =>
    value === null || value === undefined
      ? "—"
      : `${(Number(value) * 100).toFixed(digits)}%`,

  number: (value, digits = 2) =>
    value === null || value === undefined
      ? "—"
      : Number(value).toLocaleString("en-IN", { maximumFractionDigits: digits }),

  time: (value) =>
    value
      ? new Date(value).toLocaleString("en-IN", {
          day: "2-digit",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "—",

  featureName: (key) =>
    key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase()),
};
APERTURE_EOF_API_JS

echo "  writing frontend/src/App.jsx"
cat > frontend/src/App.jsx << 'APERTURE_EOF_APP_JSX'
/**
 * Aperture console.
 *
 * Three views, matching the three things an underwriter does: work the queue,
 * score a new application, and audit what was decided.
 *
 * State is kept deliberately plain -- `useState` and explicit reloads rather
 * than a data-fetching library. The console has one data source and a handful
 * of endpoints; a cache layer would add indirection without removing any real
 * problem.
 */

import { useCallback, useEffect, useState } from "react";

import { api } from "./api.js";
import DecisionDetail from "./components/DecisionDetail.jsx";
import Ledger from "./components/Ledger.jsx";
import NewApplication from "./components/NewApplication.jsx";
import Queue from "./components/Queue.jsx";

const VIEWS = [
  { key: "queue", label: "Queue" },
  { key: "new", label: "Score application" },
  { key: "ledger", label: "Audit ledger" },
];

export default function App() {
  const [view, setView] = useState("queue");
  const [health, setHealth] = useState(null);

  const [items, setItems] = useState([]);
  const [filters, setFilters] = useState({ outcome: "", thinFileOnly: false });
  const [queueLoading, setQueueLoading] = useState(false);
  const [queueError, setQueueError] = useState(null);

  const [selectedId, setSelectedId] = useState(null);
  const [decision, setDecision] = useState(null);

  const [ledger, setLedger] = useState([]);
  const [ledgerLoading, setLedgerLoading] = useState(false);
  const [ledgerError, setLedgerError] = useState(null);

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch(() =>
        setHealth({ status: "unreachable", model_version: "API not responding" })
      );
  }, []);

  const loadQueue = useCallback(async () => {
    setQueueLoading(true);
    setQueueError(null);
    try {
      setItems(await api.queue(filters));
    } catch (err) {
      setQueueError(`Could not load the queue — ${err.message}`);
    } finally {
      setQueueLoading(false);
    }
  }, [filters]);

  const loadLedger = useCallback(async () => {
    setLedgerLoading(true);
    setLedgerError(null);
    try {
      setLedger(await api.ledger({ limit: 200 }));
    } catch (err) {
      setLedgerError(`Could not load the ledger — ${err.message}`);
    } finally {
      setLedgerLoading(false);
    }
  }, []);

  const loadDecision = useCallback(async (id) => {
    if (!id) {
      setDecision(null);
      return;
    }
    try {
      setDecision(await api.decision(id));
    } catch {
      setDecision(null);
    }
  }, []);

  useEffect(() => {
    if (view === "queue") loadQueue();
    if (view === "ledger") loadLedger();
  }, [view, loadQueue, loadLedger]);

  useEffect(() => {
    loadDecision(selectedId);
  }, [selectedId, loadDecision]);

  function handleScored(decisionId) {
    setSelectedId(decisionId);
    setView("queue");
    loadQueue();
  }

  return (
    <div className="app">
      <header className="masthead">
        <h1>Aperture</h1>
        <span className="tagline">
          Real-time, multi-modal underwriting
        </span>
        <span className="spacer" />
        <span className="model-chip mono" title={health?.model_version}>
          {health ? health.model_version : "connecting…"}
        </span>
      </header>

      <nav className="tabs" role="tablist">
        {VIEWS.map((item) => (
          <button
            key={item.key}
            className="tab"
            role="tab"
            aria-selected={view === item.key}
            onClick={() => setView(item.key)}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {view === "ledger" ? (
        <main className="workspace single">
          <Ledger entries={ledger} loading={ledgerLoading} error={ledgerError} />
        </main>
      ) : (
        <main className="workspace">
          {view === "queue" ? (
            <Queue
              items={items}
              selectedId={selectedId}
              onSelect={setSelectedId}
              filters={filters}
              onFilterChange={setFilters}
              loading={queueLoading}
              error={queueError}
            />
          ) : (
            <NewApplication onScored={handleScored} />
          )}
          <DecisionDetail
            decision={decision}
            onRefresh={() => {
              loadDecision(selectedId);
              loadQueue();
            }}
          />
        </main>
      )}
    </div>
  );
}
APERTURE_EOF_APP_JSX

echo "  writing frontend/src/components/EvidenceBar.jsx"
cat > frontend/src/components/EvidenceBar.jsx << 'APERTURE_EOF_EVIDENCEBAR_JSX'
/**
 * Evidence ticks.
 *
 * The point of the product, drawn in about forty pixels: two rows of marks
 * standing for the evidence available in an applicant's file. The bureau row
 * counts traditional fields that are actually populated; the behavioural row
 * counts alternative-data fields.
 *
 * For a thin-file applicant the bureau row is nearly empty while the
 * behavioural row is full. A conventional lender reads only the top row and
 * declines. This system reads both.
 */

const BUREAU_FIELDS = [
  "bureau_score",
  "ext_source_1",
  "ext_source_3",
  "bureau_active_accounts",
  "bureau_closed_accounts",
  "bureau_max_days_overdue",
  "bureau_total_debt",
  "credit_history_months",
];

const BEHAVIOURAL_FIELDS = [
  "cashflow_inflow_regularity",
  "cashflow_volatility",
  "salary_credit_consistency",
  "avg_monthly_balance",
  "balance_trend_90d",
  "utility_ontime_ratio",
  "rent_ontime_ratio",
  "telecom_recharge_cadence_days",
  "ecom_txn_count_90d",
  "device_tenure_days",
];

/**
 * A field counts as evidence only if it carries a real value. Null, undefined
 * and NaN are absences. Zero counts -- "zero accounts on file" is a fact about
 * the applicant, not a gap in the record.
 */
function countPresent(features, fields) {
  return fields.filter((field) => {
    const value = features?.[field];
    return value !== null && value !== undefined && !Number.isNaN(value);
  }).length;
}

function TickRow({ label, filled, total, variant }) {
  return (
    <div className="evidence-line">
      <span className="evidence-label">{label}</span>
      <span className="ticks" role="img" aria-label={`${filled} of ${total} present`}>
        {Array.from({ length: total }, (_, index) => (
          <span
            key={index}
            className={
              index < filled ? `tick filled ${variant}` : "tick"
            }
          />
        ))}
      </span>
      <span className="evidence-count">
        {filled}/{total}
      </span>
    </div>
  );
}

export default function EvidenceBar({ features }) {
  const bureau = countPresent(features, BUREAU_FIELDS);
  const behavioural = countPresent(features, BEHAVIOURAL_FIELDS);

  return (
    <div className="evidence">
      <TickRow
        label="Bureau"
        filled={bureau}
        total={BUREAU_FIELDS.length}
        variant="bureau"
      />
      <TickRow
        label="Behavioural"
        filled={behavioural}
        total={BEHAVIOURAL_FIELDS.length}
        variant="behavioural"
      />
    </div>
  );
}
APERTURE_EOF_EVIDENCEBAR_JSX

echo "  writing frontend/src/components/Attribution.jsx"
cat > frontend/src/components/Attribution.jsx << 'APERTURE_EOF_ATTRIBUTION_JSX'
/**
 * SHAP attribution, drawn as a diverging bar chart around a centre axis.
 *
 * Hand-built rather than pulled from a charting library: the chart has one job
 * and needs exact control of the axis position, so a dependency would add
 * weight without adding capability.
 *
 * Bars to the right of the axis pushed this applicant toward decline; bars to
 * the left counted in their favour. Only the factors that actually moved the
 * decision are shown -- a full list of twenty-four near-zero contributions
 * would bury the four that matter.
 */

import { fmt } from "../api.js";

const VISIBLE_ROWS = 10;

export default function Attribution({ attribution }) {
  const entries = Object.entries(attribution || {});
  if (entries.length === 0) {
    return <p className="section-note">No attribution recorded for this decision.</p>;
  }

  const ranked = entries
    .map(([feature, value]) => ({ feature, value: Number(value) }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, VISIBLE_ROWS);

  // Scale to the largest magnitude on show, so the widest bar always fills its
  // half of the track and small differences stay legible.
  const scale = Math.max(...ranked.map((row) => Math.abs(row.value))) || 1;

  return (
    <div>
      {ranked.map(({ feature, value }) => {
        const width = (Math.abs(value) / scale) * 50;
        const increasesRisk = value > 0;

        return (
          <div className="attrib-row" key={feature}>
            <span className="attrib-name" title={fmt.featureName(feature)}>
              {fmt.featureName(feature)}
            </span>
            <span className="attrib-track">
              <span className="attrib-axis" style={{ left: "50%" }} />
              <span
                className={`attrib-bar ${increasesRisk ? "risk" : "safe"}`}
                style={
                  increasesRisk
                    ? { left: "50%", width: `${width}%` }
                    : { right: "50%", width: `${width}%` }
                }
              />
            </span>
            <span className="attrib-value">
              {value > 0 ? "+" : ""}
              {value.toFixed(3)}
            </span>
          </div>
        );
      })}

      <div className="attrib-legend">
        <span>
          <span className="swatch" style={{ background: "var(--approve)" }} />
          Counted in favour
        </span>
        <span>
          <span className="swatch" style={{ background: "var(--decline)" }} />
          Increased risk
        </span>
      </div>
    </div>
  );
}
APERTURE_EOF_ATTRIBUTION_JSX

echo "  writing frontend/src/components/Queue.jsx"
cat > frontend/src/components/Queue.jsx << 'APERTURE_EOF_QUEUE_JSX'
/**
 * The application queue.
 *
 * Each row carries the evidence ticks, so an underwriter scanning the list sees
 * at a glance which applicants a conventional lender would have had nothing to
 * work with -- before opening a single file.
 */

import { fmt } from "../api.js";
import EvidenceBar from "./EvidenceBar.jsx";

export default function Queue({
  items,
  selectedId,
  onSelect,
  filters,
  onFilterChange,
  loading,
  error,
}) {
  return (
    <div className="pane">
      <div className="pane-head">
        <h2>Queue</h2>
        <span className="spacer" />
        <div className="filters">
          <select
            aria-label="Filter by outcome"
            value={filters.outcome}
            onChange={(event) =>
              onFilterChange({ ...filters, outcome: event.target.value })
            }
          >
            <option value="">All outcomes</option>
            <option value="APPROVE">Approved</option>
            <option value="REFER">Referred</option>
            <option value="DECLINE">Declined</option>
          </select>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={filters.thinFileOnly}
              onChange={(event) =>
                onFilterChange({ ...filters, thinFileOnly: event.target.checked })
              }
            />
            Thin file
          </label>
        </div>
      </div>

      <div className="pane-body">
        {error && <div className="banner error" style={{ margin: 12 }}>{error}</div>}

        {loading && items.length === 0 && (
          <div className="empty">Loading applications…</div>
        )}

        {!loading && items.length === 0 && !error && (
          <div className="empty">
            <strong>Nothing in the queue yet</strong>
            Score an application to see it here.
          </div>
        )}

        {items.map((item) => (
          <button
            key={item.decision_id}
            className="queue-row"
            aria-current={item.decision_id === selectedId}
            onClick={() => onSelect(item.decision_id)}
          >
            <span className="queue-row-top">
              <span className="queue-name">{item.applicant_name}</span>
              <span className={`verdict ${item.outcome}`}>{item.outcome}</span>
            </span>
            <span className="queue-meta">
              <span className="mono">{fmt.currency(item.requested_amount)}</span>
              <span className="mono">
                PD {fmt.percent(item.probability_of_default, 1)}
              </span>
              {item.is_thin_file && <span className="thin-tag">Thin file</span>}
              {item.fraud_verdict !== "PASS" && (
                <span className={`verdict ${item.fraud_verdict}`}>
                  {item.fraud_verdict}
                </span>
              )}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
APERTURE_EOF_QUEUE_JSX

echo "  writing frontend/src/components/Ledger.jsx"
cat > frontend/src/components/Ledger.jsx << 'APERTURE_EOF_LEDGER_JSX'
/**
 * The audit ledger.
 *
 * Append-only, newest first. Every row carries the model version, the hash of
 * the feature set, and the hash of the exact inputs, so a decision can be
 * verified years later against the record of how it was made -- and any
 * tampering with the stored inputs shows up as a hash that no longer matches.
 */

import { fmt } from "../api.js";

export default function Ledger({ entries, loading, error }) {
  return (
    <div className="pane">
      <div className="pane-head">
        <h2>Decision ledger</h2>
        <span className="spacer" />
        <span className="section-note">
          Append-only · {entries.length} record{entries.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="pane-body">
        {error && <div className="banner error" style={{ margin: 12 }}>{error}</div>}
        {loading && entries.length === 0 && (
          <div className="empty">Loading ledger…</div>
        )}
        {!loading && entries.length === 0 && !error && (
          <div className="empty">
            <strong>The ledger is empty</strong>
            Every decision writes a permanent record here.
          </div>
        )}

        {entries.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Recorded</th>
                <th>Outcome</th>
                <th>PD</th>
                <th>Thresholds</th>
                <th>Model</th>
                <th>Input hash</th>
                <th>Reasons</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, index) => (
                <tr key={`${entry.decision_id}-${index}`}>
                  <td className="mono">{fmt.time(entry.recorded_at)}</td>
                  <td>
                    <span className={`verdict ${entry.outcome.replace("OVERRIDE:", "")}`}>
                      {entry.outcome}
                    </span>
                  </td>
                  <td className="mono">
                    {fmt.percent(entry.probability_of_default, 2)}
                  </td>
                  <td className="mono">
                    {fmt.percent(entry.approve_threshold, 0)} /{" "}
                    {fmt.percent(entry.refer_threshold, 0)}
                  </td>
                  <td className="mono" title={entry.model_version}>
                    {entry.feature_set_hash}
                  </td>
                  <td className="mono" title={entry.input_hash}>
                    {entry.input_hash?.slice(0, 12)}…
                  </td>
                  <td className="mono">
                    {(entry.reason_codes || [])
                      .map((reason) => reason.code)
                      .join(" ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
APERTURE_EOF_LEDGER_JSX

echo "  writing frontend/src/components/DecisionDetail.jsx"
cat > frontend/src/components/DecisionDetail.jsx << 'APERTURE_EOF_DECISIONDETAIL_JSX'
/**
 * One decision, in full.
 *
 * The order of the page is the order an underwriter reasons in: what was
 * decided, on what evidence, for what stated reasons, with what fraud signal,
 * and then -- last -- the control to disagree with it.
 *
 * The override form demands a written justification because an override with no
 * recorded rationale is indistinguishable from an unexplained deviation when
 * the file is reviewed a year later.
 */

import { useState } from "react";

import { api, fmt } from "../api.js";
import Attribution from "./Attribution.jsx";
import EvidenceBar from "./EvidenceBar.jsx";

const MIN_JUSTIFICATION = 15;

function OverrideForm({ decision, onDone }) {
  const [outcome, setOutcome] = useState(
    decision.outcome === "APPROVE" ? "DECLINE" : "APPROVE"
  );
  const [underwriter, setUnderwriter] = useState("");
  const [justification, setJustification] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const ready =
    underwriter.trim().length > 0 &&
    justification.trim().length >= MIN_JUSTIFICATION;

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.override(decision.decision_id, {
        underwriter: underwriter.trim(),
        new_outcome: outcome,
        justification: justification.trim(),
      });
      setJustification("");
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {error && <div className="banner error">{error}</div>}

      <div className="field">
        <label htmlFor="ov-underwriter">Underwriter</label>
        <input
          id="ov-underwriter"
          value={underwriter}
          onChange={(event) => setUnderwriter(event.target.value)}
          placeholder="Your name"
        />
      </div>

      <div className="field">
        <label htmlFor="ov-outcome">Change outcome to</label>
        <select
          id="ov-outcome"
          value={outcome}
          onChange={(event) => setOutcome(event.target.value)}
        >
          <option value="APPROVE">Approve</option>
          <option value="REFER">Refer</option>
          <option value="DECLINE">Decline</option>
        </select>
      </div>

      <div className="field">
        <label htmlFor="ov-why">
          Justification — recorded permanently against this file
        </label>
        <textarea
          id="ov-why"
          rows={3}
          value={justification}
          onChange={(event) => setJustification(event.target.value)}
          placeholder="What evidence supports departing from the model's decision?"
        />
        <span className="section-note">
          {justification.trim().length < MIN_JUSTIFICATION
            ? `${MIN_JUSTIFICATION - justification.trim().length} more characters needed`
            : "Ready to record"}
        </span>
      </div>

      <button className="btn" onClick={submit} disabled={!ready || busy}>
        {busy ? "Recording…" : "Record override"}
      </button>
    </div>
  );
}

export default function DecisionDetail({ decision, onRefresh }) {
  if (!decision) {
    return (
      <div className="pane">
        <div className="pane-head">
          <h2>Decision</h2>
        </div>
        <div className="empty">
          <strong>No application selected</strong>
          Choose an application from the queue, or score a new one.
        </div>
      </div>
    );
  }

  const reasons = decision.reasons || [];
  const overrides = decision.overrides || [];
  const features = decision.features || {};
  const bureauScoreAbsent =
    features.bureau_score === null || features.bureau_score === undefined;

  return (
    <div className="pane">
      <div className="pane-head">
        <h2>Decision</h2>
        <span className="spacer" />
        <span className="mono" style={{ fontSize: 11, color: "var(--ink-faint)" }}>
          {decision.decision_id?.slice(0, 8)}
        </span>
      </div>

      <div className="pane-body">
        <div className="headline">
          <div className="headline-main">
            <h3>{decision.applicant_name}</h3>
            <div className="headline-sub">
              Requested {fmt.currency(decision.requested_amount)} ·{" "}
              {fmt.time(decision.decided_at)}
            </div>
            <div style={{ marginTop: 10, maxWidth: 320 }}>
              <EvidenceBar features={features} />
            </div>
          </div>
          <span className="spacer" />
          <div className="outcome-block">
            <div className={`outcome-word ${decision.outcome}`}>
              {decision.outcome}
            </div>
            {decision.is_thin_file && (
              <span className="thin-tag">Thin file</span>
            )}
          </div>
        </div>

        <div className="stat-strip">
          <div className="stat">
            <div className="stat-label">Default probability</div>
            <div className="stat-value">
              {fmt.percent(decision.probability_of_default, 2)}
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Approved line</div>
            <div className="stat-value">
              {fmt.currency(decision.approved_line)}
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Bureau score</div>
            <div className={`stat-value ${bureauScoreAbsent ? "absent" : ""}`}>
              {bureauScoreAbsent
                ? "none on file"
                : fmt.number(features.bureau_score, 0)}
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Decided in</div>
            <div className="stat-value">{fmt.number(decision.latency_ms, 1)} ms</div>
          </div>
        </div>

        <div className="section">
          <div className="section-head">
            <h4>Principal reasons</h4>
            <span className="section-note">
              Disclosable under ECOA / Reg B · derived from SHAP attribution
            </span>
          </div>
          {reasons.length === 0 ? (
            <p className="section-note">
              No adverse factors carried material weight in this decision.
            </p>
          ) : (
            reasons.map((reason, index) => (
              <div className="reason" key={`${reason.code}-${index}`}>
                <span className="reason-code">{reason.code}</span>
                <span>
                  <div className="reason-statement">{reason.statement}</div>
                  <div className="reason-improvement">{reason.improvement}</div>
                  <div className="reason-evidence">
                    {reason.feature}
                    {reason.feature_value === null ||
                    reason.feature_value === undefined
                      ? " · not on file"
                      : ` = ${fmt.number(reason.feature_value, 3)}`}
                  </div>
                </span>
                <span className="reason-share">
                  {fmt.percent(reason.contribution_share, 0)}
                </span>
              </div>
            ))
          )}
        </div>

        <div className="section">
          <div className="section-head">
            <h4>What moved this decision</h4>
            <span className="section-note">Per-applicant SHAP contribution</span>
          </div>
          <Attribution attribution={decision.shap_attribution} />
        </div>

        <div className="section">
          <div className="section-head">
            <h4>Fraud screen</h4>
            <span className={`verdict ${decision.fraud_verdict}`}>
              {decision.fraud_verdict}
            </span>
            <span className="section-note">
              score {fmt.number(decision.fraud_score, 2)}
            </span>
          </div>
          {decision.fraud_signals?.length ? (
            <ul className="signal-list">
              {decision.fraud_signals.map((signal) => (
                <li key={signal}>{signal}</li>
              ))}
            </ul>
          ) : (
            <p className="section-note">
              No behavioural fraud signals triggered.
            </p>
          )}
        </div>

        <div className="section">
          <div className="section-head">
            <h4>Underwriter override</h4>
            <span className="section-note">
              The model's original decision is never overwritten
            </span>
          </div>

          {overrides.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              {overrides.map((override, index) => (
                <div className="override-log" key={index}>
                  <strong>{override.underwriter}</strong> changed{" "}
                  <span className="mono">{override.original_outcome}</span> →{" "}
                  <span className="mono">{override.new_outcome}</span>
                  <div style={{ color: "var(--ink-muted)", marginTop: 3 }}>
                    {override.justification}
                  </div>
                  <div
                    className="mono"
                    style={{ fontSize: 11, color: "var(--ink-faint)", marginTop: 2 }}
                  >
                    {fmt.time(override.created_at)}
                  </div>
                </div>
              ))}
            </div>
          )}

          <OverrideForm decision={decision} onDone={onRefresh} />
        </div>

        <div className="section">
          <div className="section-head">
            <h4>Provenance</h4>
          </div>
          <div className="mono" style={{ fontSize: 11.5, color: "var(--ink-muted)" }}>
            {decision.model_version}
          </div>
        </div>
      </div>
    </div>
  );
}
APERTURE_EOF_DECISIONDETAIL_JSX

echo "  writing frontend/src/components/NewApplication.jsx"
cat > frontend/src/components/NewApplication.jsx << 'APERTURE_EOF_NEWAPPLICATION_JSX'
/**
 * Score a new application.
 *
 * The three presets are the argument of the product, made clickable. They are
 * not decoration: the first is the case a conventional lender gets wrong, the
 * second is the case it gets right, and the third is the case where good credit
 * behaviour must not be allowed to outweigh a fraud signal.
 *
 * Editing is limited to the fields that carry the story. Sending the full
 * twenty-four-field payload through a form would take longer to fill than it
 * takes to explain, and the preset already establishes a coherent applicant.
 */

import { useState } from "react";

import { api, fmt } from "../api.js";

const PRESETS = {
  thin: {
    label: "Thin file, strong behaviour",
    note: "No bureau record. Rent, utilities and cashflow all excellent. A conventional model has nothing to score and declines.",
    payload: {
      applicant_name: "Priya Sharma",
      requested_amount: 150000,
      income_annual: 420000,
      employment_years: 1.5,
      debt_to_income: 1.8,
      age_years: 24,
      loan_amount: 150000,
      loan_term_months: 24,
      credit_history_months: 4,
      bureau_active_accounts: 0,
      bureau_closed_accounts: 0,
      utility_ontime_ratio: 0.96,
      rent_ontime_ratio: 0.98,
      salary_credit_consistency: 0.88,
      cashflow_inflow_regularity: 0.99,
      cashflow_volatility: 0.12,
      avg_monthly_balance: 38000,
      balance_trend_90d: -0.05,
      telecom_recharge_cadence_days: -2,
      ecom_txn_count_90d: 22,
      device_tenure_days: 900,
      form_correction_count: 2,
      pan_field_pasted: false,
      session_duration_seconds: 310,
      applications_per_device_30d: 1,
      hour_of_day: 14,
      geo_velocity_kmh: 12,
    },
  },
  thick: {
    label: "Established file, weakening",
    note: "Long bureau history, but arrears on record, rising balances and irregular payments.",
    payload: {
      applicant_name: "Rakesh Menon",
      requested_amount: 400000,
      income_annual: 900000,
      employment_years: 11,
      debt_to_income: 3.4,
      age_years: 43,
      loan_amount: 400000,
      loan_term_months: 48,
      bureau_score: 612,
      ext_source_1: 0.24,
      ext_source_3: 0.29,
      bureau_active_accounts: 6,
      bureau_closed_accounts: 5,
      bureau_max_days_overdue: 74,
      bureau_total_debt: 2100000,
      credit_history_months: 168,
      utility_ontime_ratio: 0.61,
      rent_ontime_ratio: 0.58,
      salary_credit_consistency: 0.31,
      cashflow_inflow_regularity: 0.72,
      cashflow_volatility: 0.94,
      avg_monthly_balance: 21000,
      balance_trend_90d: 1.4,
      telecom_recharge_cadence_days: 19,
      ecom_txn_count_90d: 9,
      device_tenure_days: 210,
      form_correction_count: 3,
      pan_field_pasted: false,
      session_duration_seconds: 280,
      applications_per_device_30d: 1,
      hour_of_day: 11,
      geo_velocity_kmh: 30,
    },
  },
  fraud: {
    label: "Good credit, fraud signals",
    note: "The credit profile looks fine. The session does not: seven applications from one device, implausible travel, identity number pasted.",
    payload: {
      applicant_name: "Unverified Applicant",
      requested_amount: 250000,
      income_annual: 800000,
      employment_years: 6,
      debt_to_income: 1.1,
      age_years: 33,
      loan_amount: 250000,
      loan_term_months: 36,
      bureau_score: 742,
      ext_source_1: 0.71,
      ext_source_3: 0.68,
      bureau_active_accounts: 3,
      bureau_closed_accounts: 2,
      bureau_max_days_overdue: 0,
      bureau_total_debt: 380000,
      credit_history_months: 96,
      utility_ontime_ratio: 0.99,
      rent_ontime_ratio: 0.99,
      salary_credit_consistency: 0.93,
      cashflow_inflow_regularity: 1.0,
      cashflow_volatility: 0.08,
      avg_monthly_balance: 96000,
      balance_trend_90d: -0.1,
      telecom_recharge_cadence_days: -3,
      ecom_txn_count_90d: 31,
      device_tenure_days: 1400,
      form_correction_count: 14,
      pan_field_pasted: true,
      session_duration_seconds: 19,
      applications_per_device_30d: 7,
      hour_of_day: 3,
      geo_velocity_kmh: 820,
    },
  },
};

const EDITABLE = [
  { key: "applicant_name", label: "Applicant name", type: "text" },
  { key: "requested_amount", label: "Requested amount (₹)", type: "number" },
  { key: "income_annual", label: "Annual income (₹)", type: "number" },
  { key: "credit_history_months", label: "Credit history (months)", type: "number" },
  { key: "bureau_score", label: "Bureau score (blank if none)", type: "number" },
  { key: "utility_ontime_ratio", label: "Utility bills paid on time (0–1)", type: "number" },
  { key: "rent_ontime_ratio", label: "Rent paid on time (0–1)", type: "number" },
  { key: "applications_per_device_30d", label: "Applications from device (30d)", type: "number" },
];

export default function NewApplication({ onScored }) {
  const [presetKey, setPresetKey] = useState("thin");
  const [form, setForm] = useState(PRESETS.thin.payload);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  function choosePreset(key) {
    setPresetKey(key);
    setForm(PRESETS[key].payload);
    setResult(null);
    setError(null);
  }

  function update(key, rawValue, type) {
    setForm((current) => {
      const next = { ...current };
      if (type === "number") {
        // An empty box means "not on file", which is a distinct state from
        // zero and must be sent as an absence, not a value.
        if (rawValue === "") delete next[key];
        else next[key] = Number(rawValue);
      } else {
        next[key] = rawValue;
      }
      return next;
    });
  }

  async function score() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const decision = await api.decide(form);
      setResult(decision);
      onScored?.(decision.decision_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="pane">
      <div className="pane-head">
        <h2>Score an application</h2>
      </div>

      <div className="pane-body pad">
        <div className="section-head">
          <h4>Scenario</h4>
        </div>
        <div style={{ display: "grid", gap: 6, marginBottom: 16 }}>
          {Object.entries(PRESETS).map(([key, preset]) => (
            <button
              key={key}
              className={`btn ${presetKey === key ? "" : "ghost"} small`}
              style={{ textAlign: "left", padding: "8px 11px" }}
              onClick={() => choosePreset(key)}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <p className="section-note" style={{ marginTop: 0, marginBottom: 18 }}>
          {PRESETS[presetKey].note}
        </p>

        {EDITABLE.map((field) => (
          <div className="field" key={field.key}>
            <label htmlFor={`f-${field.key}`}>{field.label}</label>
            <input
              id={`f-${field.key}`}
              type={field.type}
              step="any"
              value={form[field.key] ?? ""}
              onChange={(event) =>
                update(field.key, event.target.value, field.type)
              }
            />
          </div>
        ))}

        {error && <div className="banner error">{error}</div>}

        <button className="btn" onClick={score} disabled={busy}>
          {busy ? "Scoring…" : "Score application"}
        </button>

        {result && (
          <div className="banner info" style={{ marginTop: 14 }}>
            <strong className="mono">{result.outcome}</strong> · PD{" "}
            {fmt.percent(result.probability_of_default, 2)} ·{" "}
            {result.approved_line
              ? `line ${fmt.currency(result.approved_line)}`
              : "no line offered"}{" "}
            · {fmt.number(result.latency_ms, 1)} ms
          </div>
        )}
      </div>
    </div>
  );
}
APERTURE_EOF_NEWAPPLICATION_JSX

echo ""
echo "Files written. Installing dependencies (this takes a minute)..."
cd frontend
npm install --no-audit --no-fund
echo ""
echo "Done. Start the console with:"
echo "    cd frontend && npm run dev"
echo "Keep the API running in another terminal:"
echo "    uvicorn backend.main:app --reload --port 8000"
