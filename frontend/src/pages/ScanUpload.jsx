import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud, Loader2 } from "lucide-react";
import client from "../api/client";

export default function ScanUpload() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    product_name: "",
    brand_name: "",
    category: "",
    calibration_mm_per_px: "",
    pdp_area_cm2: "",
  });
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handleFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError("Please select a label image to scan.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const data = new FormData();
      data.append("product_name", form.product_name);
      if (form.brand_name) data.append("brand_name", form.brand_name);
      if (form.category) data.append("category", form.category);
      if (form.calibration_mm_per_px)
        data.append("calibration_mm_per_px", form.calibration_mm_per_px);
      if (form.pdp_area_cm2) data.append("pdp_area_cm2", form.pdp_area_cm2);
      data.append("image", file);

      const { data: scan } = await client.post("/scans/", data, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      navigate(`/scans/${scan.id}`);
    } catch (err) {
      setError(err?.response?.data?.detail || "Failed to submit scan.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold text-slate-900">Scan a Product Label</h1>
      <p className="text-slate-500 text-sm mt-1 mb-6">
        Upload a clear photo of the principal display panel. The system will extract
        mandatory declarations and check them against the Legal Metrology (Packaged
        Commodities) Rules, 2011.
      </p>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Product name *
            </label>
            <input
              required
              value={form.product_name}
              onChange={(e) => update("product_name", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="e.g. Sunrise Refined Sunflower Oil 1L"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Brand</label>
            <input
              value={form.brand_name}
              onChange={(e) => update("brand_name", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
            <input
              value={form.category}
              onChange={(e) => update("category", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="e.g. Edible Oil"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Principal display panel area (cm²)
            </label>
            <input
              type="number"
              step="0.1"
              value={form.pdp_area_cm2}
              onChange={(e) => update("pdp_area_cm2", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="Used for the font-size rule threshold"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Calibration (mm per pixel)
            </label>
            <input
              type="number"
              step="0.0001"
              value={form.calibration_mm_per_px}
              onChange={(e) => update("calibration_mm_per_px", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              placeholder="e.g. photograph a ruler alongside the label"
            />
            <p className="text-xs text-slate-400 mt-1">
              Optional. Without it, font-size compliance cannot be verified precisely.
            </p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Label image *</label>
          <label className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 rounded-xl py-8 cursor-pointer hover:border-emerald-400 transition">
            {preview ? (
              <img src={preview} alt="preview" className="max-h-56 rounded-lg" />
            ) : (
              <>
                <UploadCloud className="text-slate-400" size={32} />
                <span className="text-sm text-slate-500">Click to select an image</span>
              </>
            )}
            <input type="file" accept="image/*" onChange={handleFile} className="hidden" />
          </label>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="flex items-center gap-2 bg-slate-900 text-white rounded-lg px-5 py-2.5 text-sm font-medium hover:bg-slate-800 disabled:opacity-60"
        >
          {submitting && <Loader2 className="animate-spin" size={16} />}
          {submitting ? "Analyzing label..." : "Run Compliance Scan"}
        </button>
      </form>
    </div>
  );
}
