"use client";

import { ChangeEvent, FormEvent, useState } from "react";

const featureCards = [
  ["Upload a recording", "Choose a Google Meet video to prepare it for processing."],
  ["Review meetings", "Your processed meetings will appear here."],
  ["Follow the conversation", "Speaker-separated, timestamped transcripts are coming soon."]
];

export default function DashboardPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
    setMessage(null);
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setMessage("Choose an MP4, WebM, or MOV video first.");
      return;
    }

    setIsUploading(true);
    setMessage(null);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
      const response = await fetch(`${apiBaseUrl}/api/meetings/upload`, {
        method: "POST",
        body: formData
      });
      const body = await response.json();

      if (!response.ok) {
        throw new Error(body.detail ?? "The video could not be uploaded.");
      }

      setMessage(`Uploaded “${body.title}” as meeting #${body.id}.`);
      setSelectedFile(null);
      event.currentTarget.reset();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "The video could not be uploaded.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-12 sm:px-10">
      <header className="mb-12 flex items-center justify-between border-b border-slate-700 pb-6">
        <div>
          <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">Workspace</p>
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">Meeting Transcriber</h1>
        </div>
        <span className="rounded-full border border-cyan-400/40 bg-cyan-400/10 px-3 py-1 text-sm text-cyan-200">Upload ready</span>
      </header>

      <section aria-labelledby="upload-heading" className="rounded-2xl border border-dashed border-slate-600 bg-slate-900/70 p-8 shadow-2xl shadow-slate-950/30">
        <p className="text-sm font-medium text-cyan-300">New meeting</p>
        <h2 id="upload-heading" className="mt-2 text-2xl font-semibold text-white">Upload a meeting recording</h2>
        <p className="mt-3 max-w-2xl text-slate-300">Upload an MP4, WebM, or MOV recording. Transcription is not active yet.</p>
        <form className="mt-7 space-y-4" onSubmit={submitUpload}>
          <label className="flex cursor-pointer items-center justify-between rounded-xl border border-slate-600 bg-slate-800 px-5 py-4 text-slate-300">
            <span>
              <span className="block font-medium text-white">{selectedFile?.name ?? "Choose a video"}</span>
              <span className="mt-1 block text-sm">Maximum size: 500 MB.</span>
            </span>
            <span className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold">Browse</span>
            <input className="sr-only" type="file" accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov" onChange={selectFile} />
          </label>
          <button className="rounded-lg bg-cyan-400 px-4 py-2 font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50" disabled={isUploading} type="submit">
            {isUploading ? "Uploading…" : "Upload video"}
          </button>
          {message && <p className="text-sm text-slate-200" role="status">{message}</p>}
        </form>
      </section>

      <section aria-labelledby="meetings-heading" className="mt-10">
        <div className="flex items-baseline justify-between">
          <h2 id="meetings-heading" className="text-xl font-semibold text-white">Meetings</h2>
          <span className="text-sm text-slate-400">0 meetings</span>
        </div>
        <div className="mt-4 rounded-xl border border-slate-700 bg-slate-900/50 p-8 text-center text-slate-400">
          Uploaded meetings will appear here when the meetings library is implemented.
        </div>
      </section>

      <section aria-label="Planned capabilities" className="mt-10 grid gap-4 md:grid-cols-3">
        {featureCards.map(([title, description]) => (
          <article key={title} className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
            <h2 className="font-semibold text-white">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
