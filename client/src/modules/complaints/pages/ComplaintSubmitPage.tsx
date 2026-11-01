import { useState, type FormEvent } from "react";
import { errorMessage, http } from "../../../lib/http";
import type { ComplaintSubmission } from "../api/types";

export function ComplaintSubmitPage() {
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [attachments, setAttachments] = useState<FileList | null>(null);
  const [submission, setSubmission] = useState<ComplaintSubmission | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = new FormData();
      body.append("category", category);
      body.append("description", description);
      Array.from(attachments ?? []).forEach((file) => body.append("attachments", file));
      const result = await http.post<ComplaintSubmission>("/complaints/", body);
      setSubmission(result.data);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  if (submission) {
    return <main>
      <h1>Complaint submitted</h1>
      <p>{submission.confirmation}</p>
      <p>Reference: <strong>{submission.complaint_id}</strong></p>
      <button onClick={() => setSubmission(null)}>Submit another complaint</button>
    </main>;
  }

  return <main>
    <h1>Submit a complaint</h1>
    <p>Describe your concern. Required fields are marked.</p>
    {error && <p role="alert">{error}</p>}
    <form onSubmit={onSubmit}>
      <label htmlFor="complaint-category">Category *</label>
      <input id="complaint-category" required maxLength={120} value={category}
        onChange={(event) => setCategory(event.target.value)} />
      <label htmlFor="complaint-description">Description *</label>
      <textarea id="complaint-description" required value={description}
        onChange={(event) => setDescription(event.target.value)} />
      <label htmlFor="complaint-attachments">Supporting files</label>
      <input id="complaint-attachments" type="file" multiple
        onChange={(event) => setAttachments(event.target.files)} />
      <button type="submit" disabled={busy}>{busy ? "Submitting…" : "Submit complaint"}</button>
    </form>
  </main>;
}
