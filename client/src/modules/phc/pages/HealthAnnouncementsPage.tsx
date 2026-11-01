import { useState } from "react";
import { useHealthAnnouncements, usePublishAnnouncement } from "../api/hooks";

export default function HealthAnnouncementsPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [search, setSearch] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");

  const { data: announcements, isLoading, error } = useHealthAnnouncements();
  const publishAnnouncement = usePublishAnnouncement();

  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [priority, setPriority] = useState<"Normal" | "Urgent">("Normal");
  const [formError, setFormError] = useState("");

  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");

    if (!title.trim()) {
      setFormError("Title is required.");
      return;
    }
    if (!content.trim()) {
      setFormError("Content is required.");
      return;
    }

    try {
      await publishAnnouncement.mutateAsync({
        title: title.trim(),
        content: content.trim(),
        priority,
      });
      setShowCreateModal(false);
      setTitle("");
      setContent("");
      setPriority("Normal");
    } catch (err: any) {
      setFormError(err.response?.data?.error || err.message || "Failed to publish advisory.");
    }
  };

  const filtered = (announcements || []).filter((a) => {
    if (priorityFilter && a.priority !== priorityFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return a.title.toLowerCase().includes(q) || a.content.toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Health Advisories & Announcements</h1>
          <p className="text-sm text-slate-500 mt-1">
            Official campus healthcare guidelines, immunization drives, and seasonal epidemic advisories.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
        >
          Publish New Advisory
        </button>
      </div>

      {/* Filter and Search */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <input
          type="text"
          placeholder="Search advisories..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full sm:max-w-xs border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
        <div className="flex gap-2 w-full sm:w-auto">
          {["", "Normal", "Urgent"].map((p) => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                priorityFilter === p
                  ? "bg-indigo-600 text-white"
                  : "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50"
              }`}
            >
              {p || "All Priorities"}
            </button>
          ))}
        </div>
      </div>

      {/* Announcements List */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-500">Loading campus advisories...</div>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          Failed to load health announcements.
        </div>
      ) : !filtered.length ? (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center text-slate-500">
          No health announcements found.
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((item) => (
            <div
              key={item.id}
              className={`rounded-lg border p-5 shadow-sm transition-all ${
                item.priority === "Urgent"
                  ? "border-red-300 bg-red-50/40"
                  : "border-slate-200 bg-white"
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-3">
                  <h2 className="text-base font-semibold text-slate-900">{item.title}</h2>
                  {item.priority === "Urgent" ? (
                    <span className="px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-red-100 text-red-800 border border-red-200">
                      Urgent Advisory
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
                      General
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-500">
                  Published {new Date(item.published_date).toLocaleDateString(undefined, {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </div>
              </div>

              <div className="mt-3 text-sm text-slate-700 whitespace-pre-line leading-relaxed">
                {item.content}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Publish Advisory Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900 border-b pb-2">Publish Campus Health Advisory</h2>
            {formError && (
              <div className="p-3 bg-red-50 text-red-700 rounded text-xs border border-red-200">
                {formError}
              </div>
            )}
            <form onSubmit={handlePublish} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Advisory Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Seasonal Dengue & Viral Fever Precautions..."
                  className="w-full border border-slate-300 rounded p-2 text-xs"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Priority Level <span className="text-red-500">*</span>
                </label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value as "Normal" | "Urgent")}
                  className="w-full border border-slate-300 rounded p-2 text-xs"
                >
                  <option value="Normal">Normal Advisory</option>
                  <option value="Urgent">Urgent / Campus Alert</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Advisory Content & Guidelines <span className="text-red-500">*</span>
                </label>
                <textarea
                  required
                  rows={5}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Detail symptoms, preventive measures, PHC dispensary consultation timings..."
                  className="w-full border border-slate-300 rounded p-2 text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={publishAnnouncement.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded font-medium disabled:opacity-50"
                >
                  {publishAnnouncement.isPending ? "Publishing..." : "Publish Advisory"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
