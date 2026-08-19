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
