import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { quizApi } from "../api/hooks";

export function QuizCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: "", course_code: "", start_time: "", end_time: "", duration_minutes: 30, description: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await quizApi.createQuiz({
        ...form,
        start_time: new Date(form.start_time).toISOString(),
        end_time: new Date(form.end_time).toISOString(),
      });
      navigate("/quizzing");
    } catch (err: any) {
      alert("Error: " + (err?.response?.data?.error || err.message));
    }
  };

  return (
    <div style={{ padding: "1.5rem", maxWidth: 600, margin: "0 auto" }}>
      <PageHeader title="Create Quiz" subtitle="Schedule an assessment window for your course" />
      <form onSubmit={handleSubmit} style={{ background: "#fff", padding: "1.5rem", borderRadius: 8, border: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: 12 }}>
        <input placeholder="Title *" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} style={{ padding: 8, borderRadius: 6, border: "1px solid #cbd5e1" }} required />
        <input placeholder="Course Code *" value={form.course_code} onChange={(e) => setForm({ ...form, course_code: e.target.value })} style={{ padding: 8, borderRadius: 6, border: "1px solid #cbd5e1" }} required />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <input type="datetime-local" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} style={{ padding: 8, borderRadius: 6, border: "1px solid #cbd5e1" }} required />
          <input type="datetime-local" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} style={{ padding: 8, borderRadius: 6, border: "1px solid #cbd5e1" }} required />
        </div>
        <input type="number" min={1} placeholder="Duration (mins) *" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) })} style={{ padding: 8, borderRadius: 6, border: "1px solid #cbd5e1" }} required />
        <textarea placeholder="Instructions / Description" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} style={{ padding: 8, borderRadius: 6, border: "1px solid #cbd5e1" }} />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
          <button type="button" onClick={() => navigate("/quizzing")} style={{ padding: "6px 12px", border: "1px solid #cbd5e1", background: "#fff", borderRadius: 6, cursor: "pointer" }}>Cancel</button>
          <button type="submit" style={{ padding: "6px 12px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 }}>Save Draft</button>
        </div>
      </form>
    </div>
  );
}
