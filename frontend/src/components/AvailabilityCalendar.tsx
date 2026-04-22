import { format, parseISO } from "date-fns";
import type { DayAvailability, FieldSchedule, TimeBlock } from "../types";

interface Props {
  fields: FieldSchedule[];
}

export function AvailabilityCalendar({ fields }: Props) {
  if (fields.length === 0) {
    return (
      <div style={s.empty}>
        No fields matched the current filters. Try a different borough, broaden the search text, or include fully booked rows.
      </div>
    );
  }

  const days = fields[0].days;

  return (
    <div style={s.shell}>
      <div style={s.scrollWrap}>
        <table style={s.table}>
          <thead>
            <tr>
              <th style={{ ...s.headCell, ...s.fieldHead }}>Field</th>
              {days.map((day) => (
                <th key={day.date} style={s.headCell}>
                  <div style={s.dayName}>{format(parseISO(day.date), "EEE")}</div>
                  <div style={s.dayDate}>{format(parseISO(day.date), "MMM d")}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {fields.map((field) => (
              <tr key={field.field_id} className="cal-row" style={s.row}>
                <th scope="row" className="cal-field-cell" style={s.fieldCell}>
                  <div style={s.fieldName}>
                    <a
                      href={`https://www.nycgovparks.org/permits/field-and-court/issued/${field.prop_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: "inherit", textDecoration: "none" }}
                      title="View live schedule on NYC Parks"
                    >
                      {field.field_name}
                    </a>
                  </div>
                  <div style={s.fieldPark}>
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(field.park_name + " NYC Parks")}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: "inherit", textDecoration: "underline", textUnderlineOffset: 2, textDecorationColor: "rgba(148,163,184,0.4)" }}
                    >
                      {field.park_name}
                    </a>
                  </div>
                  <div style={s.fieldTags}>
                    <span style={s.boroughTag}>{field.borough}</span>
                    {field.surface_type && (
                      <span style={s.surfaceTag}>{field.surface_type}</span>
                    )}
                    <a
                      href={`https://www.nycgovparks.org/permits/field-and-court/issued/${field.prop_id}/csv`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ ...s.surfaceTag, background: "rgba(16,185,129,0.1)", border: "1px solid rgba(16,185,129,0.2)", color: "#34d399", cursor: "pointer", textDecoration: "none" }}
                      title="Download full season CSV for this park"
                    >
                      CSV
                    </a>
                  </div>
                  <div style={s.fieldHours}>{formatHours(field.total_available_minutes)} open this period</div>
                </th>
                {field.days.map((day) => (
                  <td key={day.date} className="cal-day-cell" style={{ ...s.dayCell, ...cellTone(day) }}>
                    <DaySummary day={day} propId={field.prop_id} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DaySummary({ day, propId }: { day: DayAvailability; propId: string }) {
  if (day.potential_minutes === 0) {
    return <div style={s.unavailableLabel}>Unavailable</div>;
  }
  if (day.open_blocks.length === 0) {
    return (
      <>
        <div style={s.cellHours}>0h free</div>
        <OccupancyBar ratio={0} />
        <div style={s.bookedLabel}>Fully booked</div>
      </>
    );
  }

  const ratio = day.open_minutes / day.potential_minutes;
  const preview = day.open_blocks.slice(0, 2);
  return (
    <>
      <div style={s.cellHours}>{formatHours(day.open_minutes)} free</div>
      <OccupancyBar ratio={ratio} />
      <div style={s.blockList}>
        {preview.map((block) => (
          <a
            href={`https://www.nycgovparks.org/permits/field-and-court/issued/${propId}`}
            target="_blank"
            rel="noopener noreferrer"
            key={block.start}
            style={{ ...s.blockPill, textDecoration: "none", display: "inline-block" }}
            title="View live schedule on NYC Parks"
          >
            {formatBlock(block)}
          </a>
        ))}
        {day.open_blocks.length > preview.length && (
          <div style={s.blockOverflow}>+{day.open_blocks.length - preview.length} more</div>
        )}
      </div>
    </>
  );
}

function OccupancyBar({ ratio }: { ratio: number }) {
  const trackColor = "rgba(255,255,255,0.08)";
  const fillColor = ratio >= 0.65 ? "rgba(34,197,94,0.7)" : ratio >= 0.25 ? "rgba(245,158,11,0.7)" : "rgba(239,68,68,0.55)";
  return (
    <div style={{ height: 3, borderRadius: 2, background: trackColor, marginBottom: 8, overflow: "hidden" }}>
      <div style={{ height: "100%", borderRadius: 2, width: `${Math.round(ratio * 100)}%`, background: fillColor }} />
    </div>
  );
}

function cellTone(day: DayAvailability): React.CSSProperties {
  if (day.potential_minutes === 0) {
    return { background: "rgba(30,41,59,0.35)", color: "#64748b" };
  }
  if (day.open_minutes === 0) {
    return { background: "rgba(127,29,29,0.32)", color: "#fca5a5" };
  }
  const ratio = day.open_minutes / day.potential_minutes;
  if (ratio >= 0.65) {
    return { background: "rgba(20,83,45,0.32)", color: "#d1fae5" };
  }
  return { background: "rgba(120,65,5,0.35)", color: "#fde68a" };
}

function formatBlock(block: TimeBlock) {
  const start = parseISO(block.start);
  const end = parseISO(block.end);
  const startMins = start.getMinutes();
  const endMins = end.getMinutes();

  const startFmt = startMins === 0 ? "h" : "h:mm";
  const endFmt = endMins === 0 ? "h a" : "h:mm a";

  if (format(start, "a") === format(end, "a")) {
    return `${format(start, startFmt)}–${format(end, endFmt)}`;
  }
  return `${format(start, startFmt + " a")}–${format(end, endFmt)}`;
}

function formatHours(totalMinutes: number) {
  if (!totalMinutes) return "0h";
  const h = totalMinutes / 60;
  return h % 1 === 0 ? `${h.toFixed(0)}h` : `${h.toFixed(1)}h`;
}

const s: Record<string, React.CSSProperties> = {
  shell: {
    background: "rgba(10,18,35,0.7)", borderRadius: 20,
    border: "1px solid rgba(148,163,184,0.1)", overflow: "hidden",
  },
  scrollWrap: { overflow: "auto" },
  table: {
    width: "100%", borderCollapse: "separate",
    borderSpacing: 0, minWidth: 960,
  },
  empty: {
    textAlign: "center", padding: 52, color: "#475569", fontSize: 14,
    background: "rgba(10,18,35,0.7)", borderRadius: 18,
    border: "1px dashed rgba(148,163,184,0.14)",
  },
  headCell: {
    position: "sticky", top: 0, zIndex: 2,
    background: "rgba(6,12,26,0.97)",
    textAlign: "left", padding: "14px 16px",
    borderBottom: "1px solid rgba(148,163,184,0.1)",
    color: "#e2e8f0", minWidth: 150,
  },
  fieldHead: { left: 0, zIndex: 3, minWidth: 280 },
  dayName: { fontSize: 10, textTransform: "uppercase", letterSpacing: ".14em", color: "#86efac", marginBottom: 4, fontWeight: 700 },
  dayDate: { fontSize: 14, fontWeight: 700, color: "#f1f5f9" },

  row: { borderBottom: "1px solid rgba(148,163,184,0.07)" },

  fieldCell: {
    position: "sticky", left: 0, zIndex: 1,
    minWidth: 280, maxWidth: 280,
    background: "rgba(8,14,28,0.96)",
    padding: "14px 16px",
    borderBottom: "1px solid rgba(148,163,184,0.07)",
    textAlign: "left", verticalAlign: "top",
    transition: "background .15s",
  },
  fieldName: { fontSize: 14, fontWeight: 700, color: "#f1f5f9", marginBottom: 4, lineHeight: 1.3 },
  fieldPark: { fontSize: 12, color: "#94a3b8", marginBottom: 8, lineHeight: 1.3 },
  fieldTags: { display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 },
  boroughTag: {
    fontSize: 10, padding: "2px 7px", borderRadius: 5, fontWeight: 600,
    background: "rgba(59,130,246,0.12)", border: "1px solid rgba(59,130,246,0.2)",
    color: "#93c5fd", letterSpacing: ".04em",
  },
  surfaceTag: {
    fontSize: 10, padding: "2px 7px", borderRadius: 5, fontWeight: 500,
    background: "rgba(148,163,184,0.08)", border: "1px solid rgba(148,163,184,0.14)",
    color: "#64748b",
  },
  fieldHours: { fontSize: 11, color: "#475569" },

  dayCell: {
    minWidth: 150, padding: "12px 14px",
    verticalAlign: "top",
    borderBottom: "1px solid rgba(148,163,184,0.07)",
    borderLeft: "1px solid rgba(148,163,184,0.06)",
    transition: "filter .15s",
  },
  cellHours: { fontSize: 12, fontWeight: 700, marginBottom: 6, letterSpacing: "-0.01em" },

  blockList: { display: "flex", flexDirection: "column", gap: 5 },
  blockPill: {
    display: "inline-block", fontSize: 11, padding: "2px 8px", borderRadius: 5,
    background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.2)",
    color: "#86efac", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap",
    lineHeight: 1.5, cursor: "pointer",
  },
  blockOverflow: { fontSize: 11, opacity: 0.7, marginTop: 2, fontStyle: "italic" },

  bookedLabel:     { fontSize: 11, opacity: 0.75 },
  unavailableLabel: { fontSize: 11, opacity: 0.5 },
};
