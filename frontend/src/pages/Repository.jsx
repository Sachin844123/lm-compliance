import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Trash2 } from "lucide-react";
import client from "../api/client";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "compliant", label: "Compliant" },
  { value: "non_compliant", label: "Non-Compliant" },
  { value: "processing", label: "Processing" },
  { value: "error", label: "Error" },
];

export default function Repository() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const { data } = await client.get("/scans/", {
        params: { search: search || undefined, status: status || undefined, limit: 50 },
      });
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  function handleSearchSubmit(e) {
    e.preventDefault();
    load();
  }

  async function handleDelete(id) {
    if (!confirm("Delete this scan and its report permanently?")) return;
    await client.delete(`/scans/${id}`);
    load();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Product Repository</h1>
          <p className="text-slate-500 text-sm mt-1">{total} scanned product(s) on record</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[240px] flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 text-slate-400" size={16} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by product name..."
              className="w-full pl-9 pr-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <button className="px-4 py-2 rounded-lg bg-slate-900 text-white text-sm font-medium hover:bg-slate-800">
            Search
          </button>
        </form>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-5 py-3">Product</th>
              <th className="text-left px-5 py-3">Category</th>
              <th className="text-left px-5 py-3">Scanned</th>
              <th className="text-left px-5 py-3">Score</th>
              <th className="text-left px-5 py-3">Status</th>
              <th className="px-5 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr>
                <td colSpan={6} className="px-5 py-6 text-center text-slate-400">
                  Loading...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-6 text-center text-slate-400">
                  No scans found.
                </td>
              </tr>
            )}
            {items.map((s) => (
              <tr key={s.id} className="hover:bg-slate-50">
                <td className="px-5 py-3">
                  <Link to={`/scans/${s.id}`} className="font-medium text-slate-800 hover:text-emerald-600">
                    {s.product_name}
                  </Link>
                  {s.brand_name && <p className="text-xs text-slate-400">{s.brand_name}</p>}
                </td>
                <td className="px-5 py-3 text-slate-500">{s.category || "-"}</td>
                <td className="px-5 py-3 text-slate-500">
                  {new Date(s.created_at).toLocaleDateString()}
                </td>
                <td className="px-5 py-3 text-slate-700">{s.overall_score}%</td>
                <td className="px-5 py-3">
                  <StatusBadge status={s.status} />
                </td>
                <td className="px-5 py-3 text-right">
                  {(user?.role === "admin" || user?.role === "inspector") && (
                    <button
                      onClick={() => handleDelete(s.id)}
                      className="text-slate-400 hover:text-red-600"
                      title="Delete scan"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
