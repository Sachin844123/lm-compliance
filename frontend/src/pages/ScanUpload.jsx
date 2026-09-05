import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, ScanFace, FileText } from "lucide-react";
import client from "../api/client";

function ImageDropZone({ label, hint, preview, onChange, icon: Icon }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <label className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-300 rounded-xl py-8 cursor-pointer hover:border-emerald-400 transition">
        {preview ? (
          <img src={preview} alt="preview" className="max-h-48 rounded-lg" />
        ) : (
          <>
            <Icon className="text-slate-400" size={32} />
            <span className="text-sm text-slate-500">Click to select a photo</span>
          </>
        )}
        <input type="file" accept="image/*" onChange={onChange} className="hidden" />
      </label>
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </div>
  );
}

export default function ScanUpload() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ calibration_mm_per_px: "", pdp_area_cm2: "" });
  const [frontFile, setFrontFile] = useState(null);
  const [frontPreview, setFrontPreview] = useState(null);
  const [labelFile, setLabelFile] = useState(null);
  const [labelPreview, setLabelPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handleFrontFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFrontFile(f);
    setFrontPreview(URL.createObjectURL(f));
  }

  function handleLabelFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setLabelFile(f);
    setLabelPreview(URL.createObjectURL(f));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!frontFile || !labelFile) {
      setError("Please provide both the front-of-pack photo and the declarations panel photo.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const data = new FormData();
      data.append("front_image", frontFile);
      data.append("image", labelFile);
      if (form.calibration_mm_per_px)
        data.append("calibration_mm_per_px", form.calibration_mm_per_px);
      if (form.pdp_area_cm2) data.append("pdp_area_cm2", form.pdp_area_cm2);

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
      <h1 className="text-2xl font-semibold text-slate-900">Scan a Product</h1>
      <p className="text-slate-500 text-sm mt-1 mb-6">
        Upload two photos — the product's front (to identify it automatically) and its
        declarations panel (to check against the Legal Metrology (Packaged Commodities)
        Rules, 2011). Nothing needs to be typed in; the product name, brand, and category
        are detected automatically from the front photo.
      </p>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ImageDropZone
            label="Front of pack *"
            hint="Used to automatically identify the product, brand, and category."
            preview={frontPreview}
            onChange={handleFrontFile}
            icon={ScanFace}
          />
          <ImageDropZone
            label="Declarations panel *"
            hint="The panel with net quantity, MRP, mfg date, etc. — checked for compliance."
            preview={labelPreview}
            onChange={handleLabelFile}
            icon={FileText}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
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

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="flex items-center gap-2 bg-slate-900 text-white rounded-lg px-5 py-2.5 text-sm font-medium hover:bg-slate-800 disabled:opacity-60"
        >
          {submitting && <Loader2 className="animate-spin" size={16} />}
          {submitting ? "Identifying & analyzing..." : "Run Compliance Scan"}
        </button>
      </form>
    </div>
  );
}
