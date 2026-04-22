import { useState } from "react";
import { DayPicker, DateRange } from "react-day-picker";
import { format, addDays } from "date-fns";
import "react-day-picker/dist/style.css";

interface Props {
  startDate: Date | null;
  endDate: Date | null;
  onChange: (start: Date | null, end: Date | null) => void;
}

export function DateRangePicker({ startDate, endDate, onChange }: Props) {
  const [open, setOpen] = useState(false);

  const range: DateRange = {
    from: startDate ?? undefined,
    to: endDate ?? undefined,
  };

  function handleSelect(r: DateRange | undefined) {
    onChange(r?.from ?? null, r?.to ?? null);
    if (r?.from && r?.to) setOpen(false);
  }

  const label =
    startDate && endDate
      ? `${format(startDate, "MMM d")} – ${format(endDate, "MMM d, yyyy")}`
      : startDate
      ? `${format(startDate, "MMM d, yyyy")} – pick end`
      : "Select date range";

  return (
    <div style={s.wrapper}>
      <button type="button" onClick={() => setOpen((v) => !v)} style={s.trigger}>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style={{ flexShrink: 0, color: "#86efac" }}>
          <rect x="1" y="2" width="12" height="11" rx="2" stroke="currentColor" strokeWidth="1.5"/>
          <path d="M1 6h12" stroke="currentColor" strokeWidth="1.5"/>
          <path d="M4 1v2M10 1v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
        <span>{label}</span>
        <svg
          width="12" height="12" viewBox="0 0 12 12" fill="none"
          style={{ marginLeft: 4, color: "#475569", transform: open ? "rotate(180deg)" : "none", transition: "transform .2s" }}
        >
          <path d="M2.5 4.5 6 8l3.5-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {open && (
        <div style={s.popover}>
          <DayPicker
            mode="range"
            selected={range}
            onSelect={handleSelect}
            disabled={{ before: new Date() }}
            toDate={addDays(new Date(), 90)}
            numberOfMonths={2}
            showOutsideDays
          />
          <div style={s.hint}>Max 14-day range · Past dates disabled</div>
        </div>
      )}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  wrapper: { position: "relative" },
  trigger: {
    display: "flex", alignItems: "center", gap: 8,
    padding: "10px 14px",
    background: "rgba(10,18,35,0.7)",
    border: "1px solid rgba(148,163,184,0.14)",
    borderRadius: 12, cursor: "pointer",
    fontWeight: 600, fontSize: 13, color: "#e2e8f0",
    whiteSpace: "nowrap", transition: "border-color .15s",
    outline: "none",
  },
  popover: {
    position: "absolute", top: "calc(100% + 8px)", left: 0, zIndex: 100,
    background: "rgba(8,14,28,0.97)",
    border: "1px solid rgba(148,163,184,0.12)",
    borderRadius: 18,
    boxShadow: "0 20px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.03)",
    backdropFilter: "blur(20px)",
    padding: 20,
  },
  hint: {
    textAlign: "center", fontSize: 11, color: "#475569",
    marginTop: 10, letterSpacing: ".04em",
  },
};
