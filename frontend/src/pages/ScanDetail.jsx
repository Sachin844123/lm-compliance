import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CheckCircle2, XCircle, Download, ArrowLeft, Loader2 } from "lucide-react";
import client from "../api/client";
import StatusBadge from "../components/StatusBadge";

export default function ScanDetail() {
  const { id } = useParams();
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [imageUrl, setImageUrl] = useState(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    client.get(`/scans/${id}`).then(({ data }) => setScan(data)).finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    // The image endpoint requires auth (a Bearer token), which a plain <img
    // src> can't send - fetch it through the authenticated client instead
    // and turn the result into an object URL.
    let objectUrl;
    client
      .get(`/scans/${id}/image`, { responseType: "blob" })
      .then(({ data }) => {
        objectUrl = URL.createObjectURL(data);
        setImageUrl(objectUrl);
      })
      .catch(() => setImageUrl(null));
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [id]);

  async function handleDownloadReport() {
    setDownloading(true);
    try {
      const { data } = await client.get(`/scans/${id}/report`, { responseType: "blob" });
      const url = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `compliance_report_${id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err?.response?.data?.detail || "Failed to generate the report.");
    } finally {
      setDownloading(false);
    }
  }

  if (loading) return <p className="text-slate-500">Loading scan...</p>;
  if (!scan) return <p className="text-red-600">Scan not found.</p>;

  return (
    <div className="space-y-6">
      <Link to="/repository" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft size={16} /> Back to repository
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{scan.product_name}</h1>
          <p className="text-slate-500 text-sm mt-1">
            {scan.brand_name && <span>{scan.brand_name} · </span>}
            {scan.category && <span>{scan.category} · </span>}
            Scanned {new Date(scan.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={scan.status} />
          <button
            onClick={handleDownloadReport}
            disabled={downloading}
            className="flex items-center gap-2 bg-slate-900 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-slate-800 disabled:opacity-60"
          >
            {downloading ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            {downloading ? "Generating..." : "Download PDF Report"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            {imageUrl ? (
              <img src={imageUrl} alt={scan.product_name} className="w-full rounded-lg" />
            ) : (
              <div className="w-full h-40 flex items-center justify-center text-sm text-slate-400 bg-slate-50 rounded-lg">
                Image unavailable
              </div>
            )}
          </div>
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
            <p className="text-sm font-medium text-slate-700 mb-1">Compliance Score</p>
            <p className="text-3xl font-semibold text-slate-900">{scan.overall_score}%</p>
          </div>
          {scan.notes && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
              <p className="text-sm font-medium text-slate-700 mb-1">AI-Assisted Summary</p>
              <p className="text-sm text-slate-600">{scan.notes}</p>
            </div>
          )}
        </div>

        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm">
          <div className="px-5 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">Declaration Checklist</h2>
          </div>
          <div className="divide-y divide-slate-100">
            {scan.declarations.map((d) => (
              <div key={d.id} className="px-5 py-4 flex gap-3">
                {d.compliant ? (
                  <CheckCircle2 className="text-emerald-500 shrink-0 mt-0.5" size={20} />
                ) : (
                  <XCircle className="text-red-500 shrink-0 mt-0.5" size={20} />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-slate-800">{d.label}</p>
                    <span className="text-xs text-slate-400 shrink-0">{d.rule_ref}</span>
                  </div>
                  {d.matched_text && (
                    <p className="text-xs text-slate-500 mt-1 truncate">
                      Detected: "{d.matched_text}"
                    </p>
                  )}
                  {d.font_height_mm != null && (
                    <p className="text-xs text-slate-500 mt-1">
                      Font height: {d.font_height_mm}mm (min required: {d.min_required_mm}mm)
                    </p>
                  )}
                  {d.issue && (
                    <p
                      className={`text-xs mt-1 ${
                        d.compliant ? "text-amber-600" : "text-red-600"
                      }`}
                    >
                      {d.issue}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
