const STYLES = {
  compliant: "bg-emerald-100 text-emerald-800 border-emerald-200",
  non_compliant: "bg-red-100 text-red-800 border-red-200",
  processing: "bg-amber-100 text-amber-800 border-amber-200",
  error: "bg-slate-200 text-slate-700 border-slate-300",
};

const LABELS = {
  compliant: "Compliant",
  non_compliant: "Non-Compliant",
  processing: "Processing",
  error: "Error",
};

export default function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${
        STYLES[status] || STYLES.error
      }`}
    >
      {LABELS[status] || status}
    </span>
  );
}
