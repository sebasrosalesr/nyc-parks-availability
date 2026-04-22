import type { FieldType } from "../types";

const FIELDS: { value: FieldType; label: string }[] = [
  { value: "soccer",     label: "Soccer"     },
  { value: "baseball",   label: "Baseball"   },
  { value: "basketball", label: "Basketball" },
  { value: "softball",   label: "Softball"   },
  { value: "football",   label: "Football"   },
  { value: "cricket",    label: "Cricket"    },
];

interface Props {
  value: FieldType;
  onChange: (v: FieldType) => void;
}

export function FieldSelector({ value, onChange }: Props) {
  return (
    <div style={s.wrapper}>
      {FIELDS.map((f) => (
        <button
          key={f.value}
          type="button"
          onClick={() => onChange(f.value)}
          style={{
            ...s.btn,
            ...(value === f.value ? s.active : s.inactive),
          }}
        >
          {value === f.value && <span style={s.activeDot} />}
          {f.label}
        </button>
      ))}
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  wrapper: { display: "flex", flexWrap: "wrap", gap: 6 },
  btn: {
    display: "flex", alignItems: "center", gap: 6,
    padding: "9px 14px", borderRadius: 999,
    border: "1px solid transparent",
    cursor: "pointer", fontWeight: 600, fontSize: 13,
    transition: "all .15s", outline: "none",
  },
  active: {
    background: "rgba(34,197,94,0.15)",
    color: "#86efac",
    borderColor: "rgba(34,197,94,0.35)",
  },
  inactive: {
    background: "rgba(15,23,42,0.5)",
    color: "#64748b",
    borderColor: "rgba(148,163,184,0.12)",
  },
  activeDot: {
    display: "inline-block", width: 5, height: 5,
    borderRadius: "50%", background: "#22c55e",
    boxShadow: "0 0 5px #22c55e",
  },
};
