import { useDeferredValue, useState } from "react";
import { addDays, differenceInCalendarDays } from "date-fns";
import { FieldSelector } from "./components/FieldSelector";
import { DateRangePicker } from "./components/DateRangePicker";
import { AvailabilityCalendar } from "./components/AvailabilityCalendar";
import { useAvailability } from "./hooks/useAvailability";
import type { FieldType } from "./types";

export default function App() {
  const [fieldType, setFieldType] = useState<FieldType>("soccer");
  const [startDate, setStartDate] = useState<Date | null>(new Date());
  const [endDate, setEndDate] = useState<Date | null>(addDays(new Date(), 2));
  const [query, setQuery] = useState("");
  const [borough, setBorough] = useState("All boroughs");
  const [showOnlyOpen, setShowOnlyOpen] = useState(true);
  const deferredQuery = useDeferredValue(query.trim().toLowerCase());

  const { data, loading, error } = useAvailability({ fieldType, startDate, endDate });
  const dayCount = startDate && endDate ? differenceInCalendarDays(endDate, startDate) + 1 : 0;
  const boroughs = data ? [...new Set(data.fields.map((f) => f.borough))].sort() : [];
  const visibleFields = data
    ? data.fields.filter((field) => {
        if (showOnlyOpen && field.total_available_minutes === 0) return false;
        if (borough !== "All boroughs" && field.borough !== borough) return false;
        if (!deferredQuery) return true;
        return `${field.field_name} ${field.park_name} ${field.borough} ${field.prop_id}`
          .toLowerCase()
          .includes(deferredQuery);
      })
    : [];
  const visibleMinutes = visibleFields.reduce((t, f) => t + f.total_available_minutes, 0);

  return (
    <div style={s.page}>
      {/* ── Header ── */}
      <header style={s.header}>
        <div style={s.headerInner}>
          <div style={s.headerRow}>
            <div style={s.brand}>
              <div style={s.brandMark}>
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                  <path d="M9 1C9 1 3 6 3 11a6 6 0 0 0 12 0C15 6 9 1 9 1Z" fill="#22c55e" opacity=".9"/>
                  <rect x="8.25" y="12" width="1.5" height="5" rx=".75" fill="#16a34a"/>
                </svg>
              </div>
              <div>
                <div style={s.brandTitle}>NYC Parks Field Availability</div>
                <div style={s.brandSub}>
                  Compare every permittable field across the city — one calendar instead of clicking pins one at a time.
                </div>
              </div>
            </div>
            <div style={s.headerBadge}>
              <span style={s.badgeDot} />
              Live catalog · Cached snapshots
            </div>
          </div>
        </div>
      </header>

      <main style={s.main}>
        {/* ── Controls ── */}
        <div style={s.controls}>
          <div style={s.controlGroup}>
            <div style={s.controlLabel}>Sport</div>
            <FieldSelector value={fieldType} onChange={setFieldType} />
          </div>
          <div style={s.controlDivider} />
          <div style={s.controlGroup}>
            <div style={s.controlLabel}>Dates</div>
            <DateRangePicker
              startDate={startDate}
              endDate={endDate}
              onChange={(s, e) => { setStartDate(s); setEndDate(e); }}
            />
          </div>
          <div style={s.controlNote}>
            {dayCount > 0
              ? `${dayCount}-day window · ~${dayCount} availability requests`
              : "Pick a date range to get started"}
          </div>
        </div>

        {/* ── Loading ── */}
        {loading && (
          <div style={s.loadingCard}>
            <div style={s.spinner} />
            <div>
              <div style={s.loadingTitle}>
                Searching {fieldType} fields across NYC
              </div>
              <div style={s.loadingSub}>
                Pulling permit snapshots from NYC Parks and assembling your calendar…
              </div>
            </div>
          </div>
        )}

        {/* ── Error ── */}
        {error && (
          <div style={{ ...s.loadingCard, background: "rgba(127, 29, 29, 0.28)", borderColor: "rgba(248,113,113,0.2)" }}>
            <div style={{ color: "#fca5a5", fontWeight: 600, fontSize: 14 }}>Search failed</div>
            <div style={{ color: "#fecaca", fontSize: 13, marginTop: 4 }}>{error}</div>
          </div>
        )}

        {/* ── Results ── */}
        {data && !loading && (
          <div className="fade-up">
            <div style={s.metrics}>
              <MetricCard label="Matching fields" value={data.query.matching_field_count.toLocaleString()} accent="#22c55e" />
              <MetricCard label="Matching parks"  value={data.query.matching_park_count.toLocaleString()}  accent="#3b82f6" />
              <MetricCard label="Open time visible" value={formatHours(visibleMinutes)}                   accent="#a78bfa" />
              <MetricCard
                label="Cached snapshots"
                value={`${data.query.cached_snapshot_count} / ${data.query.snapshot_count}`}
                accent="#f59e0b"
              />
            </div>

            <div style={s.filters}>
              <div style={s.searchBox}>
                <svg width="15" height="15" viewBox="0 0 15 15" fill="none" style={{ flexShrink: 0, color: "#7dd3a6" }}>
                  <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M10 10 13.5 13.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Filter by field, park, borough, or prop ID"
                  style={s.searchInput}
                />
              </div>

              <select
                value={borough}
                onChange={(e) => setBorough(e.target.value)}
                style={s.select}
              >
                <option>All boroughs</option>
                {boroughs.map((b) => <option key={b}>{b}</option>)}
              </select>

              <Toggle
                checked={showOnlyOpen}
                onChange={setShowOnlyOpen}
                label="Only fields with open time"
              />
            </div>

            <div style={s.resultsMeta}>
              <span style={s.resultCount}>
                {visibleFields.length} of {data.query.matching_field_count} fields
              </span>
              <span style={s.legend}>
                <LegendSwatch color="rgba(20,83,45,0.7)"    border="rgba(34,197,94,0.35)"   label="Available" />
                <LegendSwatch color="rgba(133,77,14,0.55)"  border="rgba(245,158,11,0.3)"   label="Partial" />
                <LegendSwatch color="rgba(127,29,29,0.45)"  border="rgba(248,113,113,0.25)" label="Fully booked" />
              </span>
            </div>

            <AvailabilityCalendar fields={visibleFields} />
          </div>
        )}

        {/* ── Placeholder ── */}
        {!data && !loading && !error && (
          <div style={s.placeholder}>
            <div style={s.placeholderIcon}>
              <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
                <path d="M18 3C18 3 7 12 7 21a11 11 0 0 0 22 0C29 12 18 3 18 3Z" fill="rgba(34,197,94,0.18)" stroke="rgba(34,197,94,0.35)" strokeWidth="1.5"/>
                <rect x="16.75" y="22" width="2.5" height="10" rx="1.25" fill="rgba(34,197,94,0.35)"/>
              </svg>
            </div>
            <div style={s.placeholderTitle}>Pick a sport and date range</div>
            <div style={s.placeholderSub}>
              Builds a field-by-field availability calendar from the public NYC Parks vector tile and permit data.
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ── Small components ──────────────────────────────────────────

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer", userSelect: "none" }}>
      <div
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        style={{
          width: 40, height: 22, borderRadius: 11, flexShrink: 0, position: "relative",
          background: checked ? "#22c55e" : "rgba(148,163,184,0.18)",
          border: "1px solid rgba(0,0,0,0.15)",
          transition: "background .2s", cursor: "pointer",
        }}
      >
        <div style={{
          position: "absolute", top: 2,
          left: checked ? 20 : 2,
          width: 16, height: 16, borderRadius: "50%",
          background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
          transition: "left .2s",
        }} />
      </div>
      <span style={{ fontSize: 13, color: "#cbd5e1" }}>{label}</span>
    </label>
  );
}

function MetricCard({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{ ...s.metricCard, borderLeft: `3px solid ${accent}` }}>
      <div style={s.metricLabel}>{label}</div>
      <div style={{ ...s.metricValue, color: accent === "#22c55e" ? "#f0fdf4" : "#f8fafc" }}>{value}</div>
    </div>
  );
}

function LegendSwatch({ color, border, label }: { color: string; border: string; label: string }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <span style={{
        display: "inline-block", width: 12, height: 12, borderRadius: 3,
        background: color, border: `1px solid ${border}`,
      }} />
      <span>{label}</span>
    </span>
  );
}

function formatHours(totalMinutes: number) {
  if (!totalMinutes) return "0h";
  const h = totalMinutes / 60;
  return h % 1 === 0 ? `${h.toFixed(0)}h` : `${h.toFixed(1)}h`;
}

// ── Styles ────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  page: { minHeight: "100vh", color: "#e5e7eb" },

  header: {
    borderBottom: "1px solid rgba(148,163,184,0.1)",
    backdropFilter: "blur(20px)",
    background: "rgba(6,15,28,0.88)",
    position: "sticky", top: 0, zIndex: 50,
  },
  headerInner: { maxWidth: 1440, margin: "0 auto", padding: "16px 24px 18px" },
  headerRow: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center", gap: 16, flexWrap: "wrap",
  },
  brand: { display: "flex", alignItems: "flex-start", gap: 14 },
  brandMark: {
    width: 38, height: 38, borderRadius: 10, flexShrink: 0,
    background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.22)",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  brandTitle: { fontWeight: 800, fontSize: 22, color: "#f8fafc", letterSpacing: "-0.03em", lineHeight: 1.2 },
  brandSub: { fontSize: 13, color: "#64748b", marginTop: 5, maxWidth: 620, lineHeight: 1.5 },
  headerBadge: {
    display: "flex", alignItems: "center", gap: 7,
    border: "1px solid rgba(34,197,94,0.2)",
    borderRadius: 999, padding: "8px 14px",
    fontSize: 12, color: "#bbf7d0",
    background: "rgba(34,197,94,0.07)",
    whiteSpace: "nowrap", flexShrink: 0,
  },
  badgeDot: {
    display: "inline-block", width: 6, height: 6, borderRadius: "50%",
    background: "#22c55e", boxShadow: "0 0 6px #22c55e",
    animation: "pulse 2s ease-in-out infinite",
  },

  main: { maxWidth: 1440, margin: "0 auto", padding: "28px 24px 64px" },

  controls: {
    background: "rgba(10,18,35,0.7)",
    borderRadius: 20, padding: "20px 22px",
    border: "1px solid rgba(148,163,184,0.1)",
    display: "flex", flexWrap: "wrap", alignItems: "center",
    gap: 0, marginBottom: 24,
  },
  controlGroup: { display: "flex", flexDirection: "column", gap: 10, padding: "0 22px 0 0" },
  controlDivider: {
    width: 1, height: 52, background: "rgba(148,163,184,0.1)",
    margin: "0 22px 0 0", flexShrink: 0,
  },
  controlLabel: {
    fontWeight: 700, fontSize: 10, color: "#86efac",
    textTransform: "uppercase", letterSpacing: ".16em",
  },
  controlNote: {
    marginLeft: "auto", maxWidth: 280, color: "#475569",
    fontSize: 12, lineHeight: 1.55, textAlign: "right",
  },

  loadingCard: {
    display: "flex", alignItems: "flex-start", gap: 16,
    padding: "18px 20px", borderRadius: 16, marginBottom: 20,
    background: "rgba(34,197,94,0.07)",
    border: "1px solid rgba(34,197,94,0.14)",
  },
  spinner: {
    width: 20, height: 20, flexShrink: 0, marginTop: 2,
    border: "2.5px solid rgba(34,197,94,0.2)",
    borderTopColor: "#22c55e", borderRadius: "50%",
    animation: "spin 0.75s linear infinite",
  },
  loadingTitle: { fontSize: 14, fontWeight: 600, color: "#d1fae5", marginBottom: 4 },
  loadingSub:   { fontSize: 13, color: "#6ee7b7", lineHeight: 1.5 },

  metrics: {
    display: "grid", gap: 10,
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    marginBottom: 16,
  },
  metricCard: {
    background: "rgba(10,18,35,0.7)", borderRadius: 16,
    border: "1px solid rgba(148,163,184,0.1)",
    borderLeft: "3px solid #22c55e",
    padding: "14px 16px",
  },
  metricLabel: {
    fontSize: 10, textTransform: "uppercase", letterSpacing: ".14em",
    color: "#64748b", marginBottom: 10, fontWeight: 600,
  },
  metricValue: { fontSize: 26, fontWeight: 800, color: "#f8fafc", letterSpacing: "-0.03em" },

  filters: {
    display: "flex", gap: 10, flexWrap: "wrap",
    alignItems: "center", marginBottom: 14,
  },
  searchBox: {
    display: "flex", alignItems: "center", gap: 10,
    flex: "1 1 320px", minWidth: 260,
    background: "rgba(10,18,35,0.7)", border: "1px solid rgba(148,163,184,0.12)",
    borderRadius: 12, padding: "0 14px",
  },
  searchInput: {
    width: "100%", border: "none", outline: "none",
    background: "transparent", color: "#f8fafc",
    padding: "11px 0", fontSize: 13,
  },
  select: {
    borderRadius: 12, border: "1px solid rgba(148,163,184,0.12)",
    background: "rgba(10,18,35,0.7)", color: "#e2e8f0",
    padding: "11px 14px", fontSize: 13, cursor: "pointer",
  },

  resultsMeta: {
    display: "flex", justifyContent: "space-between",
    alignItems: "center", marginBottom: 12,
    flexWrap: "wrap", gap: 8,
  },
  resultCount: { fontWeight: 700, fontSize: 14, color: "#94a3b8" },
  legend: { fontSize: 12, color: "#64748b", display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" },

  placeholder: {
    textAlign: "center", padding: "72px 24px",
    background: "rgba(10,18,35,0.7)", borderRadius: 22,
    border: "1px dashed rgba(148,163,184,0.15)",
  },
  placeholderIcon: { display: "flex", justifyContent: "center", marginBottom: 20 },
  placeholderTitle: { fontSize: 18, fontWeight: 700, color: "#f1f5f9", marginBottom: 10 },
  placeholderSub: { fontSize: 14, color: "#475569", maxWidth: 440, margin: "0 auto", lineHeight: 1.6 },
};
