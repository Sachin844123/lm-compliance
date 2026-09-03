export default function StatCard({ label, value, tone = "default", icon: Icon }) {
  const toneClasses = {
    default: "text-slate-900",
    good: "text-emerald-600",
    bad: "text-red-600",
    warn: "text-amber-600",
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        {Icon && <Icon size={18} className="text-slate-400" />}
      </div>
      <p className={`mt-2 text-3xl font-semibold ${toneClasses[tone]}`}>{value}</p>
    </div>
  );
}
