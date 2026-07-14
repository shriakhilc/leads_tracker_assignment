"use client";

import { FormEvent, useState } from "react";

const ACCEPTED = ".pdf,.doc,.docx";
const MAX_MB = 10;

export default function PublicLeadForm() {
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    const form = e.currentTarget;
    const formData = new FormData(form);

    const file = formData.get("resume") as File | null;
    if (!file || file.size === 0) {
      setError("Please attach your resume/CV.");
      return;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      setError(`Resume must be under ${MAX_MB} MB.`);
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch("/api/submit", { method: "POST", body: formData });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? "Submission failed. Please try again.");
        return;
      }
      setSubmitted(true);
      form.reset();
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="container narrow">
        <div className="card">
          <h1>Thank you!</h1>
          <p className="subtitle">
            We&apos;ve received your submission. Check your inbox for a confirmation email -
            an attorney will reach out soon.
          </p>
          <button className="secondary" onClick={() => setSubmitted(false)}>
            Submit another
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="container narrow">
      <div className="card">
        <h1>Apply now</h1>
        <p className="subtitle">
          Submit your details and resume - an attorney will review and get in touch.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="first_name">First name</label>
            <input id="first_name" name="first_name" type="text" required maxLength={200} />
          </div>
          <div className="field">
            <label htmlFor="last_name">Last name</label>
            <input id="last_name" name="last_name" type="text" required maxLength={200} />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" name="email" type="email" required />
          </div>
          <div className="field">
            <label htmlFor="resume">Resume / CV (PDF, DOC, DOCX - max {MAX_MB} MB)</label>
            <input id="resume" name="resume" type="file" accept={ACCEPTED} required />
          </div>

          <button type="submit" disabled={submitting}>
            {submitting ? "Submitting…" : "Submit application"}
          </button>
          {error && <p className="error">{error}</p>}
        </form>
      </div>
    </div>
  );
}
