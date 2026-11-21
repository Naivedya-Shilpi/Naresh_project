"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  createSingleFlightRunner,
  fetchMeetings,
  formatDuration,
  formatUploadDate,
  getStatusBadgeClasses,
  getStatusPresentation,
  MeetingSummary,
  uploadMeetingVideo,
  validateVideoFileSelection
} from "./lib/meetings";

type UploadFeedback = {
  kind: "success" | "error";
  text: string;
} | null;

export default function DashboardPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadFeedback, setUploadFeedback] = useState<UploadFeedback>(null);
  const [isUploading, setIsUploading] = useState(false);

  const [meetings, setMeetings] = useState<MeetingSummary[]>([]);
  const [isLoadingMeetings, setIsLoadingMeetings] = useState(true);
  const [meetingsError, setMeetingsError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const uploadSectionRef = useRef<HTMLElement | null>(null);
  const meetingsFetchGuardRef = useRef(createSingleFlightRunner());

  const loadMeetings = useCallback(async () => {
    await meetingsFetchGuardRef.current.run(async () => {
      setIsLoadingMeetings(true);
      setMeetingsError(null);
      try {
        const items = await fetchMeetings();
        setMeetings(items);
      } catch (error) {
        setMeetingsError(
          error instanceof Error ? error.message : "Could not load meetings from the backend."
        );
      } finally {
        setIsLoadingMeetings(false);
      }
    });
  }, []);

  useEffect(() => {
    void loadMeetings();
  }, [loadMeetings]);

  function openFilePicker() {
    uploadSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    fileInputRef.current?.click();
  }

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    setSelectedFile(event.target.files?.[0] ?? null);
    setUploadFeedback(null);
  }

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const validationError = validateVideoFileSelection(selectedFile);
    if (validationError || !selectedFile) {
      setUploadFeedback({
        kind: "error",
        text: validationError ?? "Choose an MP4, WebM, or MOV video before uploading."
      });
      return;
    }

    setIsUploading(true);
    setUploadFeedback(null);

    try {
      const created = await uploadMeetingVideo(selectedFile);
      setUploadFeedback({
        kind: "success",
        text: `Uploaded "${created.title}" as meeting #${created.id}.`
      });
      setSelectedFile(null);
      form.reset();
      await loadMeetings();
    } catch (error) {
      setUploadFeedback({
        kind: "error",
        text: error instanceof Error ? error.message : "The video could not be uploaded."
      });
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-10 sm:px-8 lg:px-10">
      <header className="mb-10 flex flex-col gap-4 border-b border-slate-700 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-cyan-300">
            Workspace
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Meeting Transcriber
          </h1>
        </div>
        <button
          type="button"
          onClick={openFilePicker}
          className="inline-flex items-center justify-center rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"
        >
          Upload new video
        </button>
      </header>

      <section
        ref={uploadSectionRef}
        aria-labelledby="upload-heading"
        className="rounded-2xl border border-dashed border-slate-600 bg-slate-900/70 p-6 shadow-2xl shadow-slate-950/30 sm:p-8"
      >
        <p className="text-sm font-medium text-cyan-300">New meeting</p>
        <h2 id="upload-heading" className="mt-2 text-2xl font-semibold text-white">
          Upload a meeting recording
        </h2>
        <p className="mt-2 max-w-2xl text-sm text-slate-300 sm:text-base">
          Select an MP4, WebM, or MOV video up to 500 MB to add it to your meetings library.
        </p>

        <form className="mt-6 space-y-4" onSubmit={submitUpload}>
          <label className="flex cursor-pointer flex-col gap-3 rounded-xl border border-slate-600 bg-slate-800 px-5 py-4 text-slate-300 transition hover:border-cyan-400/60 sm:flex-row sm:items-center sm:justify-between">
            <span>
              <span className="block font-medium text-white">
                {selectedFile?.name ?? "Choose a video file"}
              </span>
              <span className="mt-1 block text-sm text-slate-400">
                Supported formats: MP4, WebM, MOV (max 500 MB).
              </span>
            </span>
            <span className="inline-flex w-fit rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white">
              Browse
            </span>
            <input
              ref={fileInputRef}
              className="sr-only"
              type="file"
              accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov"
              onChange={selectFile}
            />
          </label>

          <div className="flex flex-wrap items-center gap-3">
            <button
              className="rounded-lg bg-cyan-400 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={isUploading}
              type="submit"
            >
              {isUploading ? "Uploading video…" : "Upload video"}
            </button>
            {selectedFile && !isUploading && (
              <span className="text-xs text-slate-400">
                Ready: {selectedFile.name}
              </span>
            )}
          </div>

          {uploadFeedback && (
            <p
              role={uploadFeedback.kind === "error" ? "alert" : "status"}
              className={
                uploadFeedback.kind === "error"
                  ? "rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200"
                  : "rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200"
              }
            >
              {uploadFeedback.text}
            </p>
          )}
        </form>
      </section>

      <section aria-labelledby="meetings-heading" className="mt-10">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 id="meetings-heading" className="text-xl font-semibold text-white">
              Meetings
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              {isLoadingMeetings
                ? "Fetching meetings…"
                : `${meetings.length} ${meetings.length === 1 ? "meeting" : "meetings"}`}
            </p>
          </div>
          <button
            type="button"
            onClick={() => void loadMeetings()}
            disabled={isLoadingMeetings}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3.5 py-2 text-sm font-medium text-slate-200 transition hover:border-slate-500 disabled:opacity-50"
          >
            {isLoadingMeetings ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {isLoadingMeetings && meetings.length === 0 ? (
          <div
            role="status"
            className="mt-4 rounded-xl border border-slate-700 bg-slate-900/50 p-8 text-center text-slate-300"
          >
            Loading meetings…
          </div>
        ) : meetingsError ? (
          <div
            role="alert"
            className="mt-4 flex flex-col items-center gap-4 rounded-xl border border-rose-500/40 bg-rose-500/10 p-6 text-center text-rose-200"
          >
            <p className="text-sm">{meetingsError}</p>
            <button
              type="button"
              onClick={() => void loadMeetings()}
              className="rounded-lg border border-rose-400/50 bg-rose-500/20 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-500/30"
            >
              Try again
            </button>
          </div>
        ) : meetings.length === 0 ? (
          <div className="mt-4 rounded-xl border border-slate-700 bg-slate-900/50 p-10 text-center">
            <p className="text-base font-medium text-white">No meetings yet</p>
            <p className="mt-2 text-sm text-slate-400">
              Upload a recorded meeting video above to start tracking your meetings here.
            </p>
          </div>
        ) : (
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {meetings.map((meeting) => {
              const statusInfo = getStatusPresentation(meeting.status);
              return (
                <article
                  key={meeting.id}
                  className="flex flex-col justify-between rounded-xl border border-slate-700/80 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20 transition hover:border-cyan-400/40"
                >
                  <div>
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="line-clamp-2 text-base font-semibold text-white">
                        {meeting.title}
                      </h3>
                      <span
                        className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium ${getStatusBadgeClasses(meeting.status)}`}
                      >
                        {statusInfo.label}
                      </span>
                    </div>

                    <dl className="mt-4 space-y-2 text-sm text-slate-300">
                      <div className="flex items-center justify-between gap-2">
                        <dt className="text-slate-400">Uploaded</dt>
                        <dd>{formatUploadDate(meeting.created_at)}</dd>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <dt className="text-slate-400">Duration</dt>
                        <dd>{formatDuration(meeting.duration)}</dd>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <dt className="text-slate-400">Transcript</dt>
                        <dd>
                          {meeting.segment_count > 0
                            ? `${meeting.segment_count} segments · ${meeting.speaker_count} ${meeting.speaker_count === 1 ? "speaker" : "speakers"}`
                            : "Not transcribed yet"}
                        </dd>
                      </div>
                    </dl>
                  </div>

                  <div className="mt-5 border-t border-slate-800 pt-4">
                    <Link
                      href={`/meetings/${meeting.id}`}
                      className="inline-flex w-full items-center justify-center rounded-lg border border-cyan-400/40 bg-cyan-400/10 px-4 py-2 text-sm font-semibold text-cyan-200 transition hover:bg-cyan-400/20"
                    >
                      Open meeting
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
