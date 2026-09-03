import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { ClipboardList, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import client from "../api/client";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";

const PIE_COLORS = ["#10b981", "#ef4444", "#f59e0b"];

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client
      .get("/dashboard/stats")
      .then(({ data }) => setStats(data))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-slate-500">Loading dashboard...</p>;
  if (!stats) return <p className="text-red-600">Failed to load dashboard.</p>;

  const pieData = [
    { name: "Compliant", value: stats.compliant_count },
    { name: "Non-Compliant", value: stats.non_compliant_count },
    { name: "Processing", value: stats.processing_count },
  ].filter((d) => d.value > 0);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Enforcement Dashboard</h1>
        <p className="text-slate-500 text-sm mt-1">
          Overview of scanned products and Legal Metrology compliance status.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Scans" value={stats.total_scans} icon={ClipboardList} />
        <StatCard
          label="Compliant"
          value={stats.compliant_count}
          tone="good"
          icon={CheckCircle2}
        />
        <StatCard
          label="Non-Compliant"
          value={stats.non_compliant_count}
          tone="bad"
          icon={XCircle}
        />
        <StatCard
          label="Compliance Rate"
          value={`${stats.compliance_rate}%`}
          tone="warn"
          icon={Loader2}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <h2 className="font-semibold text-slate-800 mb-4">Top Violations by Rule</h2>
          {stats.violation_breakdown.length === 0 ? (
            <p className="text-sm text-slate-400">No violations recorded yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={stats.violation_breakdown} layout="vertical" margin={{ left: 40 }}>
                <XAxis type="number" allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="rule_ref"
                  width={110}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip
                  formatter={(value, _n, props) => [value, props.payload.label]}
                />
                <Bar dataKey="violation_count" fill="#ef4444" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <h2 className="font-semibold text-slate-800 mb-4">Compliance Split</h2>
          {pieData.length === 0 ? (
            <p className="text-sm text-slate-400">No scans yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={90} label>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800">Recent Scans</h2>
          <Link to="/repository" className="text-sm text-emerald-600 hover:underline">
            View all
          </Link>
        </div>
        <div className="divide-y divide-slate-100">
          {stats.recent_scans.length === 0 && (
            <p className="p-5 text-sm text-slate-400">No scans yet. Start by uploading one.</p>
          )}
          {stats.recent_scans.map((s) => (
            <Link
              key={s.id}
              to={`/scans/${s.id}`}
              className="flex items-center justify-between px-5 py-3 hover:bg-slate-50"
            >
              <div>
                <p className="text-sm font-medium text-slate-800">{s.product_name}</p>
                <p className="text-xs text-slate-400">
                  {new Date(s.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm text-slate-500">{s.overall_score}%</span>
                <StatusBadge status={s.status} />
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
