import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowClockwise,
  ArrowCounterClockwise,
  Check,
  CheckCircle,
  Copy,
  DownloadSimple,
  FileText,
  FolderOpen,
  ImageSquare,
  Plus,
  Scan,
  TextAlignLeft,
  Trash,
  UploadSimple,
  WarningCircle,
  X,
  MagnifyingGlassMinus,
  MagnifyingGlassPlus,
  Crop,
  FloppyDisk,
  CaretUp,
  CaretDown,
} from "@phosphor-icons/react";
import { AnimatePresence, motion, MotionConfig } from "motion/react";
import Landing from "./Landing";
import SettingsPanel from "./SettingsPanel";
import { request, json } from "./api";
import {
  defaults,
  type Settings,
  type Job,
  type Line,
  type Point,
  type DocumentResult,
  type Capabilities,
} from "./types";

const terminal = (job: Job | null) =>
  !!job && ["completed", "cancelled", "failed"].includes(job.status);
const textOf = (document: DocumentResult) =>
  document.lines
    .map(
      (line, i) =>
        (i
          ? document.settings.paragraph_mode === "lines"
            ? "\n"
            : line.paragraph_start
              ? "\n\n"
              : " "
          : "") + line.text,
    )
    .join("");
const message = (error: unknown) =>
  error instanceof Error ? error.message : String(error);

export default function App() {
  const [studio, setStudio] = useState(location.hash.startsWith("#studio"));
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [settings, setSettings] = useState<Settings>(defaults);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [job, setJob] = useState<Job | null>(null);
  const [draft, setDraft] = useState<DocumentResult | null>(null);
  const [title, setTitle] = useState("Untitled notes");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [saved, setSaved] = useState("Saved locally");
  const [reference, setReference] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [showOriginal, setShowOriginal] = useState(false);
  const [tab, setTab] = useState<"image" | "text">("image");
  const [crop, setCrop] = useState(false);
  const [adding, setAdding] = useState(false);
  const [find, setFind] = useState("");
  const [replace, setReplace] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const revision = useRef(0);
  const lastSaved = useRef("");
  const queue = useRef<Promise<void>>(Promise.resolve());
  const current = useRef({ draft, title, reference, job });
  current.current = { draft, title, reference, job };
  const history = useRef<DocumentResult[]>([]);
  const future = useRef<DocumentResult[]>([]);
  const active = !!job && !terminal(job);

  function refreshJobs() {
    request<Job[]>("/api/jobs")
      .then(setJobs)
      .catch((e) => setError(message(e)));
  }
  useEffect(() => {
    request<Capabilities>("/api/models")
      .then(setCapabilities)
      .catch(() =>
        setError(
          "The local backend is unavailable. Start it with python scripts/serve.py.",
        ),
      );
    refreshJobs();
    const hash = () => setStudio(location.hash.startsWith("#studio"));
    window.addEventListener("hashchange", hash);
    const id = new URLSearchParams(location.search).get("job");
    if (id) openJob(id);
    return () => window.removeEventListener("hashchange", hash);
  }, []);
  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (!job || terminal(job)) return;
    const source = new EventSource(`/api/jobs/${job.id}/events`);
    source.onmessage = (event) => {
      const updated: Job = JSON.parse(event.data);
      setJob(updated);
      if (updated.document) {
        setDraft(updated.document);
        lastSaved.current = serialize(updated.document, updated.title, null);
      }
      revision.current = updated.revision;
      if (terminal(updated)) {
        source.close();
        refreshJobs();
        setSaved("Saved locally");
      }
    };
    source.onerror = () => {
      request<Job>(`/api/jobs/${job.id}`)
        .then((updated) => {
          setJob(updated);
          if (updated.document) setDraft(updated.document);
          if (terminal(updated)) source.close();
        })
        .catch((e) => setError(message(e)));
    };
    return () => source.close();
  }, [job?.id, job?.status]);
  useEffect(() => {
    if (!draft || !job || active) return;
    if (serialize(draft, title, reference) === lastSaved.current) return;
    setSaved("Unsaved changes");
    const timer = setTimeout(() => {
      save().catch((e) => setError(message(e)));
    }, 850);
    return () => clearTimeout(timer);
  }, [draft, title, reference, active, job?.id]);
  useEffect(() => {
    const paste = (event: ClipboardEvent) => {
      const image = Array.from(event.clipboardData?.files ?? []).find((f) =>
        f.type.startsWith("image/"),
      );
      if (image && !active) {
        event.preventDefault();
        acceptFile(image);
      }
    };
    window.addEventListener("paste", paste);
    return () => window.removeEventListener("paste", paste);
  }, [active]);

  function serialize(doc: DocumentResult, name: string, ref: string | null) {
    return JSON.stringify({
      title: name.trim() || "Untitled notes",
      lines: doc.lines,
      paragraph_mode: doc.settings.paragraph_mode,
      reference: ref,
    });
  }
  function save() {
    const task = queue.current
      .catch(() => {})
      .then(async () => {
        const {
          draft: doc,
          title: name,
          reference: ref,
          job: currentJob,
        } = current.current;
        if (!doc || !currentJob || !terminal(currentJob)) return;
        const snapshot = serialize(doc, name, ref);
        if (snapshot === lastSaved.current) return;
        setSaved("Saving…");
        const updated = await request<Job>(
          `/api/jobs/${currentJob.id}/document`,
          json("PATCH", {
            ...JSON.parse(snapshot),
            revision: revision.current,
          }),
        );
        // Do not overwrite edits typed while this request was in flight.
        if (current.current.job?.id === updated.id) {
          revision.current = updated.revision;
          lastSaved.current = snapshot;
          setJob(updated);
          setSaved(
            snapshot ===
              serialize(
                current.current.draft!,
                current.current.title,
                current.current.reference,
              )
              ? "Saved locally"
              : "Unsaved changes",
          );
        }
      });
    queue.current = task;
    return task;
  }
  function open() {
    location.hash = "studio";
    setStudio(true);
    window.scrollTo({ top: 0, behavior: "instant" });
  }
  async function openJob(id: string) {
    try {
      await save();
      const next = await request<Job>(`/api/jobs/${id}`);
      setJob(next);
      setDraft(next.document);
      setTitle(next.title);
      setSettings(next.settings);
      setReference(next.reference ?? null);
      setFile(null);
      setSelected(null);
      history.current = [];
      future.current = [];
      revision.current = next.revision;
      lastSaved.current = next.document
        ? serialize(next.document, next.title, next.reference ?? null)
        : "";
      setSaved("Saved locally");
      setError("");
      open();
      historyReplace(id);
    } catch (e) {
      setError(message(e));
    }
  }
  function historyReplace(id?: string) {
    window.history.replaceState(
      null,
      "",
      `${location.pathname}${id ? "?job=" + id : ""}#studio`,
    );
  }
  async function acceptFile(next: File) {
    if (!["image/jpeg", "image/png"].includes(next.type)) {
      setError("Choose a PNG or JPEG image.");
      return;
    }
    if (next.size > 50 * 1024 * 1024) {
      setError("Choose an image smaller than 50 MiB.");
      return;
    }
    try {
      await save();
      setFile(next);
      setJob(null);
      setDraft(null);
      setTitle(next.name.replace(/\.[^.]+$/, ""));
      setReference(null);
      setError("");
      setSelected(null);
      setSettings((s) => ({ ...s, corners: null, rotation: 0 }));
      history.current = [];
      future.current = [];
      historyReplace();
      open();
    } catch (e) {
      setError(message(e));
    }
  }
  async function sample() {
    try {
      const [response, data] = await Promise.all([
        fetch("/sample.png"),
        request<{ text: string }>("/sample.json"),
      ]);
      if (!response.ok) throw new Error("Sample image is unavailable.");
      await acceptFile(
        new File([await response.blob()], "IAM example.png", {
          type: "image/png",
        }),
      );
      setReference(data.text);
      setNotice(
        "Sample loaded. The reference text is dataset ground truth; press Transcribe to run your selected model.",
      );
    } catch (e) {
      setError(message(e));
      open();
    }
  }
  async function transcribe() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const data = new FormData();
      data.append("file", file);
      data.append("settings", JSON.stringify(settings));
      data.append("title", title);
      const next = await request<Job>("/api/jobs", {
        method: "POST",
        body: data,
      });
      setJob(next);
      setDraft(null);
      revision.current = 0;
      historyReplace(next.id);
      refreshJobs();
      setCrop(false);
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  function update(doc: DocumentResult) {
    if (draft)
      history.current = [...history.current.slice(-49), structuredClone(draft)];
    future.current = [];
    setDraft({ ...doc, full_text: textOf(doc) });
  }
  function editLine(id: string, change: Partial<Line>) {
    if (draft)
      update({
        ...draft,
        lines: draft.lines.map((line) =>
          line.id === id ? { ...line, ...change } : line,
        ),
      });
  }
  function undo() {
    const previous = history.current.pop();
    if (previous && draft) {
      future.current.push(draft);
      setDraft(previous);
    }
  }
  function redo() {
    const next = future.current.pop();
    if (next && draft) {
      history.current.push(draft);
      setDraft(next);
    }
  }
  async function action(endpoint: string, body?: unknown) {
    if (!job) return;
    try {
      await save();
      const next = await request<Job>(
        `/api/jobs/${job.id}/${endpoint}`,
        body ? json("POST", body) : { method: "POST" },
      );
      setJob(next);
      setError("");
    } catch (e) {
      setError(message(e));
    }
  }
  async function download(format: string) {
    if (!job) return;
    try {
      await save();
      const response = await fetch(`/api/jobs/${job.id}/export/${format}`);
      if (!response.ok)
        throw new Error("Export failed. Try saving and downloading again.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `${title}.${format}`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(message(e));
    }
  }
  async function remove() {
    if (!job || !window.confirm(`Delete “${title}” and its local images?`))
      return;
    try {
      await request(`/api/jobs/${job.id}`, { method: "DELETE" });
      setJob(null);
      setDraft(null);
      setFile(null);
      historyReplace();
      refreshJobs();
    } catch (e) {
      setError(message(e));
    }
  }
  const selectedLine = draft?.lines.find((line) => line.id === selected);
  const ready =
    capabilities?.engines.find((e) => e.id === settings.engine)?.ready &&
    capabilities?.detectors.find((d) => d.id === settings.detector)?.ready;
  const imageUrl = job
    ? `/api/jobs/${job.id}/image/${draft && !showOriginal ? "page" : "original"}`
    : preview;

  return (
    <MotionConfig reducedMotion="user">
      <AnimatePresence mode="wait">
        {!studio ? (
          <motion.div
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            <Landing open={open} sample={sample} />
          </motion.div>
        ) : (
          <motion.div
            key="studio"
            className="studio"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.18 }}
          >
            <header className="studio-header">
              <button
                className="brand"
                onClick={() => {
                  window.history.replaceState(null, "", location.pathname);
                  setStudio(false);
                }}
              >
                <span className="brand-icon">
                  <TextAlignLeft weight="bold" />
                </span>
                Handwriting Analyser
              </button>
              <span className="local-badge">
                <span /> Local workspace
              </span>
              <button
                className="text-button"
                onClick={() => {
                  window.history.replaceState(null, "", location.pathname);
                  setStudio(false);
                }}
              >
                <ArrowLeft /> Back to home
              </button>
            </header>
            <div className="studio-layout">
              <aside className="history-panel">
                <div className="history-heading">
                  <h2>Your documents</h2>
                  <button
                    className="icon-button"
                    aria-label="Upload a new document"
                    onClick={() => input.current?.click()}
                  >
                    <Plus />
                  </button>
                </div>
                <button
                  className="button secondary"
                  onClick={() => input.current?.click()}
                  disabled={active}
                >
                  <UploadSimple /> New transcription
                </button>
                <div className="history-list">
                  {jobs.length === 0 ? (
                    <p className="hint">
                      Your transcribed pages will appear here. Stored only on
                      this computer.
                    </p>
                  ) : (
                    jobs.map((item) => (
                      <button
                        key={item.id}
                        className={`history-item ${job?.id === item.id ? "selected" : ""}`}
                        onClick={() => openJob(item.id)}
                      >
                        <FileText />
                        <span>
                          {item.title}
                          <small>
                            {new Date(item.created * 1000).toLocaleDateString()}{" "}
                            · {item.status}
                          </small>
                        </span>
                      </button>
                    ))
                  )}
                </div>
                <div className="sidebar-foot">
                  <FolderOpen />
                  <p>
                    A home for your words.
                    <small>Images and edits stay on your computer.</small>
                  </p>
                </div>
              </aside>
              <main className="workspace">
                <div className="workspace-heading">
                  <div>
                    <h1>Your page, with possibilities.</h1>
                    <p>Bring the original. Leave with something editable.</p>
                  </div>
                  <button
                    className="text-button"
                    onClick={sample}
                    disabled={active}
                  >
                    Try a sample <ArrowUpRightIcon />
                  </button>
                </div>
                <input
                  ref={input}
                  type="file"
                  accept="image/png,image/jpeg"
                  className="sr-only"
                  aria-label="Upload handwritten image"
                  onChange={(e) => {
                    if (e.target.files?.[0]) acceptFile(e.target.files[0]);
                    e.target.value = "";
                  }}
                />
                {error && (
                  <div className="alert" role="alert">
                    <WarningCircle />
                    <span>{error}</span>
                    <button
                      aria-label="Dismiss error"
                      className="icon-button"
                      onClick={() => setError("")}
                    >
                      <X />
                    </button>
                  </div>
                )}
                {notice && (
                  <div className="notice" role="status">
                    {notice}
                    <button
                      aria-label="Dismiss notice"
                      className="icon-button"
                      onClick={() => setNotice("")}
                    >
                      <X />
                    </button>
                  </div>
                )}
                {!file && !job ? (
                  <div
                    className="dropzone"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      if (e.dataTransfer.files[0])
                        acceptFile(e.dataTransfer.files[0]);
                    }}
                  >
                    <div className="upload-emblem">
                      <UploadSimple />
                    </div>
                    <h2>A new chapter starts here.</h2>
                    <p>
                      Drop your handwritten page here, or choose an image.
                      <br />
                      You can also paste an image from your clipboard.
                    </p>
                    <button
                      className="button"
                      onClick={() => input.current?.click()}
                    >
                      Choose a page <ArrowRight />
                    </button>
                    <small>PNG or JPEG · Up to 50 MiB and 100 megapixels</small>
                  </div>
                ) : (
                  <>
                    <div className="document-toolbar">
                      <label className="title-input">
                        <span className="sr-only">Document title</span>
                        <input
                          value={title}
                          maxLength={160}
                          disabled={active}
                          onChange={(e) => setTitle(e.target.value)}
                        />
                      </label>
                      <span className="save-state" role="status">
                        {draft ? (
                          <>
                            <Check size={14} /> {saved}
                          </>
                        ) : file ? (
                          `${(file.size / 1024 / 1024).toFixed(1)} MiB`
                        ) : (
                          "Preparing"
                        )}
                      </span>
                      <div className="toolbar-spacer" />
                      {draft && (
                        <>
                          <button
                            className="icon-button"
                            onClick={undo}
                            disabled={active || !history.current.length}
                            aria-label="Undo edit"
                          >
                            <ArrowCounterClockwise />
                          </button>
                          <button
                            className="icon-button"
                            onClick={redo}
                            disabled={active || !future.current.length}
                            aria-label="Redo edit"
                          >
                            <ArrowClockwise />
                          </button>
                          <button
                            className="button small secondary"
                            onClick={() =>
                              save().catch((e) => setError(message(e)))
                            }
                            disabled={active}
                          >
                            <FloppyDisk /> Save
                          </button>
                        </>
                      )}
                      {!job && (
                        <button
                          className="button small"
                          disabled={!ready || busy}
                          onClick={transcribe}
                        >
                          <Scan />
                          {busy ? "Uploading…" : "Transcribe page"}
                        </button>
                      )}
                    </div>
                    {active && (
                      <div className="processing" aria-live="polite">
                        <div>
                          <Scan />
                          <strong>
                            {(
                              {
                                queued: "Waiting for the local worker",
                                preparing: "Preparing your page",
                                detecting: "Finding handwritten lines",
                                recognizing: "Recognizing your words",
                                assembling: "Assembling your document",
                              } as Record<string, string>
                            )[job!.stage] ?? job!.stage}
                          </strong>
                          <span>
                            {job!.total > 0
                              ? `${job!.completed} / ${job!.total} lines`
                              : ""}
                          </span>
                          <button
                            className="text-button"
                            onClick={() => action("cancel")}
                          >
                            Cancel
                          </button>
                        </div>
                        {job!.stage === "recognizing" && job!.total > 0 ? (
                          <progress max={job!.total} value={job!.completed} />
                        ) : (
                          <progress />
                        )}
                        <p>
                          Processing locally. You can reopen this document from
                          history.
                        </p>
                      </div>
                    )}
                    {job?.error && (
                      <div className="alert">
                        <WarningCircle />
                        <span>{job.error}</span>
                        {terminal(job) && (
                          <button
                            className="text-button"
                            onClick={() => action("retry")}
                          >
                            Retry
                          </button>
                        )}
                      </div>
                    )}
                    <div className="mobile-tabs">
                      <button
                        className={tab === "image" ? "active" : ""}
                        onClick={() => setTab("image")}
                      >
                        <ImageSquare /> Original
                      </button>
                      <button
                        className={tab === "text" ? "active" : ""}
                        onClick={() => setTab("text")}
                      >
                        <FileText /> Transcript
                      </button>
                    </div>
                    <div className="editor-grid">
                      <section
                        className={`image-panel ${tab === "image" ? "mobile-visible" : ""}`}
                      >
                        <div className="panel-heading">
                          <h2>
                            <ImageSquare />
                            {draft ? (
                              <select
                                aria-label="Page image"
                                value={showOriginal ? "original" : "page"}
                                onChange={(e) =>
                                  setShowOriginal(e.target.value === "original")
                                }
                              >
                                <option value="page">Prepared page</option>
                                <option value="original">Original page</option>
                              </select>
                            ) : (
                              "Original page"
                            )}
                          </h2>
                          <div>
                            <button
                              className="icon-button"
                              onClick={() =>
                                setZoom((z) => Math.max(0.5, z - 0.25))
                              }
                              aria-label="Zoom out"
                            >
                              <MagnifyingGlassMinus />
                            </button>
                            <span className="zoom-value">
                              {Math.round(zoom * 100)}%
                            </span>
                            <button
                              className="icon-button"
                              onClick={() =>
                                setZoom((z) => Math.min(3, z + 0.25))
                              }
                              aria-label="Zoom in"
                            >
                              <MagnifyingGlassPlus />
                            </button>
                            {!job && (
                              <>
                                <button
                                  className={`icon-button ${crop ? "pressed" : ""}`}
                                  onClick={() => {
                                    setCrop(!crop);
                                    if (!settings.corners)
                                      setSettings((s) => ({
                                        ...s,
                                        corners: [
                                          [0.04, 0.04],
                                          [0.96, 0.04],
                                          [0.96, 0.96],
                                          [0.04, 0.96],
                                        ],
                                      }));
                                  }}
                                  aria-label="Adjust page corners"
                                >
                                  <Crop />
                                </button>
                                <button
                                  className="icon-button"
                                  aria-label="Rotate page clockwise"
                                  onClick={() =>
                                    setSettings((s) => ({
                                      ...s,
                                      rotation: ((s.rotation + 90) %
                                        360) as Settings["rotation"],
                                    }))
                                  }
                                >
                                  <ArrowClockwise />
                                </button>
                              </>
                            )}
                            {draft && (
                              <button
                                className={`icon-button ${adding ? "pressed" : ""}`}
                                disabled={active || showOriginal}
                                aria-label="Draw a new line region"
                                onClick={() => setAdding(!adding)}
                              >
                                <Plus />
                              </button>
                            )}
                          </div>
                        </div>
                        <div className="image-scroll">
                          <PageImage
                            url={imageUrl}
                            draft={showOriginal ? null : draft}
                            selected={selected}
                            onSelect={(id) => {
                              setSelected(id);
                              setTab("text");
                            }}
                            zoom={zoom}
                            rotation={!job && !crop ? settings.rotation : 0}
                            corners={crop && !job ? settings.corners : null}
                            onCorners={(corners) =>
                              setSettings((s) => ({ ...s, corners }))
                            }
                            adding={adding && !active && !showOriginal}
                            onAdd={(polygon) => {
                              if (!draft) return;
                              const id = crypto.randomUUID();
                              update({
                                ...draft,
                                lines: [
                                  ...draft.lines,
                                  {
                                    id,
                                    polygon,
                                    text: "",
                                    raw_text: "",
                                    score: null,
                                    warnings: [
                                      "New region. Rerun recognition to transcribe it.",
                                    ],
                                    reviewed: false,
                                    paragraph_start: false,
                                  },
                                ],
                              });
                              setSelected(id);
                              setAdding(false);
                            }}
                          />
                        </div>
                        {crop && !job && (
                          <p className="panel-hint">
                            Drag the four corners around the page.{" "}
                            <button
                              className="text-button"
                              onClick={() => {
                                setSettings((s) => ({ ...s, corners: null }));
                                setCrop(false);
                              }}
                            >
                              Reset crop
                            </button>
                          </p>
                        )}
                        {draft && (
                          <p className="panel-hint">
                            Select a region to review its text. Use + to draw a
                            missing line.
                          </p>
                        )}
                      </section>
                      <section
                        className={`text-panel ${tab === "text" ? "mobile-visible" : ""}`}
                      >
                        <div className="panel-heading">
                          <h2>
                            <FileText /> Your transcription
                          </h2>
                          <span>{draft?.lines.length ?? 0} lines</span>
                        </div>
                        {!draft ? (
                          <div className="transcript-empty">
                            <TextAlignLeft />
                            <h3>Words will appear here.</h3>
                            <p>
                              Choose your settings, then transcribe the page.
                              Every line stays connected to its original.
                            </p>
                          </div>
                        ) : (
                          <>
                            <div className="transcript-controls">
                              <label
                                className="sr-only"
                                htmlFor="output-layout"
                              >
                                Paragraph formatting
                              </label>
                              <select
                                id="output-layout"
                                value={draft.settings.paragraph_mode}
                                disabled={active}
                                onChange={(e) =>
                                  update({
                                    ...draft,
                                    settings: {
                                      ...draft.settings,
                                      paragraph_mode: e.target
                                        .value as Settings["paragraph_mode"],
                                    },
                                  })
                                }
                              >
                                <option value="paragraphs">
                                  Reflow paragraphs
                                </option>
                                <option value="lines">
                                  Preserve line breaks
                                </option>
                              </select>
                              <span>
                                {
                                  textOf(draft)
                                    .trim()
                                    .split(/\s+/)
                                    .filter(Boolean).length
                                }{" "}
                                words
                              </span>
                            </div>
                            <div className="lines-editor">
                              {draft.lines.length === 0 && (
                                <p className="hint">
                                  No lines detected. Add a region on the
                                  prepared page to transcribe it manually.
                                </p>
                              )}
                              {draft.lines.map((line, index) => {
                                const review =
                                  !line.reviewed &&
                                  (line.warnings.length > 0 ||
                                    (line.score !== null &&
                                      line.score <
                                        draft.settings.review_threshold));
                                return (
                                  <div
                                    className={`line-editor ${selected === line.id ? "selected" : ""}`}
                                    key={line.id}
                                  >
                                    <div className="line-label">
                                      <button
                                        onClick={() => setSelected(line.id)}
                                        className="line-number"
                                      >
                                        {String(index + 1).padStart(2, "0")}
                                      </button>
                                      {review ? (
                                        <span className="review-label">
                                          <WarningCircle /> Review suggested
                                        </span>
                                      ) : line.reviewed ? (
                                        <span className="reviewed-label">
                                          <Check /> Reviewed
                                        </span>
                                      ) : (
                                        <span className="hint">
                                          Model output
                                        </span>
                                      )}
                                      {line.score !== null && (
                                        <span
                                          className="model-score"
                                          title="Uncalibrated model score; not an accuracy percentage"
                                        >
                                          Score {line.score.toFixed(2)}
                                        </span>
                                      )}
                                    </div>
                                    <textarea
                                      aria-label={`Text for line ${index + 1}`}
                                      value={line.text}
                                      disabled={active}
                                      rows={Math.max(
                                        1,
                                        Math.ceil(line.text.length / 65),
                                      )}
                                      onFocus={() => setSelected(line.id)}
                                      onChange={(e) =>
                                        editLine(line.id, {
                                          text: e.target.value,
                                        })
                                      }
                                    />
                                    {selected === line.id && (
                                      <div className="line-detail">
                                        {line.warnings.map((note, i) => (
                                          <p key={i} className="hint">
                                            {note}
                                          </p>
                                        ))}
                                        <div>
                                          <button
                                            className="text-button"
                                            disabled={active}
                                            onClick={() =>
                                              editLine(line.id, {
                                                reviewed: !line.reviewed,
                                              })
                                            }
                                          >
                                            <CheckCircle />
                                            {line.reviewed
                                              ? "Mark unreviewed"
                                              : "Mark reviewed"}
                                          </button>
                                          <label className="checkbox">
                                            <input
                                              type="checkbox"
                                              checked={line.paragraph_start}
                                              disabled={active}
                                              onChange={(e) =>
                                                editLine(line.id, {
                                                  paragraph_start:
                                                    e.target.checked,
                                                })
                                              }
                                            />{" "}
                                            New paragraph
                                          </label>
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                            <div className="export-bar">
                              <button
                                className="icon-button"
                                aria-label="Copy transcription"
                                onClick={() =>
                                  navigator.clipboard
                                    .writeText(textOf(draft))
                                    .then(() =>
                                      setNotice("Transcription copied."),
                                    )
                                    .catch(() =>
                                      setError(
                                        "Clipboard access failed. Select and copy the text manually.",
                                      ),
                                    )
                                }
                              >
                                <Copy />
                              </button>
                              <button
                                className="button small secondary"
                                onClick={() => download("txt")}
                                disabled={active}
                              >
                                <DownloadSimple /> TXT
                              </button>
                              <button
                                className="button small"
                                onClick={() => download("docx")}
                                disabled={active}
                              >
                                <DownloadSimple /> Download DOCX
                              </button>
                            </div>
                          </>
                        )}
                      </section>
                    </div>
                    {selectedLine && draft && (
                      <RegionEditor
                        line={selectedLine}
                        width={draft.width}
                        height={draft.height}
                        disabled={active}
                        onChange={(change) => editLine(selectedLine.id, change)}
                        onDelete={() => {
                          update({
                            ...draft,
                            lines: draft.lines.filter(
                              (line) => line.id !== selectedLine.id,
                            ),
                          });
                          setSelected(null);
                        }}
                        onMove={(direction) => {
                          const lines = [...draft.lines];
                          const index = lines.findIndex(
                            (line) => line.id === selectedLine.id,
                          );
                          const target = index + direction;
                          if (target >= 0 && target < lines.length) {
                            [lines[index], lines[target]] = [
                              lines[target],
                              lines[index],
                            ];
                            update({ ...draft, lines });
                          }
                        }}
                        onRerun={() =>
                          action("rerun", { line_ids: [selectedLine.id] })
                        }
                      />
                    )}
                    {draft?.warnings.map((warning, i) => (
                      <p className="document-warning" key={i}>
                        <WarningCircle />
                        {warning}
                      </p>
                    ))}
                    {draft && (
                      <details className="review-tools">
                        <summary>
                          Find & replace · reference evaluation · document
                          details
                        </summary>
                        <div className="find-replace">
                          <label>
                            Find
                            <input
                              value={find}
                              onChange={(e) => setFind(e.target.value)}
                            />
                          </label>
                          <label>
                            Replace with
                            <input
                              value={replace}
                              onChange={(e) => setReplace(e.target.value)}
                            />
                          </label>
                          <button
                            className="button small secondary"
                            disabled={active || !find}
                            onClick={() =>
                              update({
                                ...draft,
                                lines: draft.lines.map((line) => ({
                                  ...line,
                                  text: line.text.split(find).join(replace),
                                })),
                              })
                            }
                          >
                            Replace all
                          </button>
                        </div>
                        <label>
                          Reference text (optional)
                          <textarea
                            value={reference ?? ""}
                            placeholder="Paste a verified transcription to measure CER and WER."
                            disabled={active}
                            onChange={(e) =>
                              setReference(e.target.value || null)
                            }
                            rows={3}
                          />
                        </label>
                        {job?.metrics && (
                          <p>
                            CER {(job.metrics.cer * 100).toFixed(1)}% · WER{" "}
                            {(job.metrics.wer * 100).toFixed(1)}% — compared
                            against your reference.
                          </p>
                        )}
                        <p className="hint">
                          {draft.model.version ?? settings.engine} ·{" "}
                          {draft.model.device ?? "Processing"} ·{" "}
                          {draft.timings.total_seconds ?? "—"} seconds ·
                          revision {job?.revision ?? 0}
                        </p>
                        <button
                          className="text-button danger"
                          onClick={remove}
                          disabled={active}
                        >
                          <Trash /> Delete document and images
                        </button>
                      </details>
                    )}
                  </>
                )}
                {!job && (
                  <SettingsPanel
                    value={settings}
                    onChange={setSettings}
                    capabilities={capabilities}
                    disabled={active || busy}
                  />
                )}
              </main>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </MotionConfig>
  );
}

function ArrowUpRightIcon() {
  return <ArrowRight style={{ transform: "rotate(-45deg)" }} />;
}

function PageImage({
  url,
  draft,
  selected,
  onSelect,
  zoom,
  rotation,
  corners,
  onCorners,
  adding,
  onAdd,
}: {
  url: string;
  draft: DocumentResult | null;
  selected: string | null;
  onSelect: (id: string) => void;
  zoom: number;
  rotation: number;
  corners: Point[] | null;
  onCorners: (points: Point[]) => void;
  adding: boolean;
  onAdd: (polygon: Point[]) => void;
}) {
  const [size, setSize] = useState<[number, number]>([1, 1]);
  const [drag, setDrag] = useState<number | null>(null);
  const [start, setStart] = useState<Point | null>(null);
  const [end, setEnd] = useState<Point | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const w = draft?.width ?? size[0],
    h = draft?.height ?? size[1];
  function position(event: React.PointerEvent): Point {
    const rect = svg.current!.getBoundingClientRect();
    return [
      Math.max(0, Math.min(w, ((event.clientX - rect.left) / rect.width) * w)),
      Math.max(0, Math.min(h, ((event.clientY - rect.top) / rect.height) * h)),
    ];
  }
  function point(event: React.PointerEvent) {
    const pos = position(event);
    if (drag !== null && corners) {
      const next = [...corners];
      next[drag] = [pos[0] / w, pos[1] / h];
      onCorners(next);
    }
    if (start) setEnd(pos);
  }
  return (
    <div
      className="page-stage"
      style={{
        width: `${zoom * 100}%`,
        transform: rotation ? `rotate(${rotation}deg)` : undefined,
      }}
    >
      <img
        src={url}
        alt="Uploaded handwritten page"
        draggable={false}
        onLoad={(e) =>
          setSize([e.currentTarget.naturalWidth, e.currentTarget.naturalHeight])
        }
      />
      <svg
        ref={svg}
        viewBox={`0 0 ${w} ${h}`}
        className={`page-overlay ${adding || corners ? "drawing" : ""}`}
        onPointerMove={point}
        onPointerDown={(e) => {
          if (adding) {
            const pos = position(e);
            setStart(pos);
            setEnd(pos);
            e.currentTarget.setPointerCapture(e.pointerId);
          }
        }}
        onPointerUp={() => {
          if (
            start &&
            end &&
            Math.abs(start[0] - end[0]) > 5 &&
            Math.abs(start[1] - end[1]) > 5
          ) {
            const [x1, x2] = [start[0], end[0]].sort((a, b) => a - b),
              [y1, y2] = [start[1], end[1]].sort((a, b) => a - b);
            onAdd([
              [x1, y1],
              [x2, y1],
              [x2, y2],
              [x1, y2],
            ]);
          }
          setStart(null);
          setEnd(null);
          setDrag(null);
        }}
        onPointerCancel={() => {
          setDrag(null);
          setStart(null);
        }}
      >
        {draft?.lines.map((line, i) => (
          <polygon
            role="button"
            tabIndex={0}
            aria-label={`Select line ${i + 1}`}
            key={line.id}
            points={line.polygon.map((p) => p.join(",")).join(" ")}
            className={`line-polygon ${selected === line.id ? "selected" : ""}`}
            onClick={() => onSelect(line.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(line.id);
              }
            }}
          />
        ))}
        {corners && (
          <>
            <polygon
              className="crop-polygon"
              points={corners.map(([x, y]) => `${x * w},${y * h}`).join(" ")}
            />
            {corners.map(([x, y], i) => (
              <circle
                key={i}
                role="slider"
                tabIndex={0}
                aria-label={`Page corner ${i + 1}; arrow keys move, shift for larger steps`}
                aria-valuetext={`${Math.round(x * 100)}%, ${Math.round(y * 100)}%`}
                cx={x * w}
                cy={y * h}
                r={Math.max(w, h) * 0.018}
                className="crop-handle"
                onPointerDown={(e) => {
                  e.stopPropagation();
                  setDrag(i);
                  svg.current?.setPointerCapture(e.pointerId);
                }}
                onKeyDown={(e) => {
                  const moves: Record<string, Point> = {
                    ArrowLeft: [-0.005, 0],
                    ArrowRight: [0.005, 0],
                    ArrowUp: [0, -0.005],
                    ArrowDown: [0, 0.005],
                  };
                  if (moves[e.key]) {
                    e.preventDefault();
                    const [dx, dy] = moves[e.key],
                      next = [...corners];
                    next[i] = [
                      Math.max(0, Math.min(1, x + dx * (e.shiftKey ? 5 : 1))),
                      Math.max(0, Math.min(1, y + dy * (e.shiftKey ? 5 : 1))),
                    ];
                    onCorners(next);
                  }
                }}
              />
            ))}
          </>
        )}
        {start && end && (
          <rect
            className="new-region"
            x={Math.min(start[0], end[0])}
            y={Math.min(start[1], end[1])}
            width={Math.abs(end[0] - start[0])}
            height={Math.abs(end[1] - start[1])}
          />
        )}
      </svg>
    </div>
  );
}

function RegionEditor({
  line,
  width,
  height,
  disabled,
  onChange,
  onDelete,
  onMove,
  onRerun,
}: {
  line: Line;
  width: number;
  height: number;
  disabled: boolean;
  onChange: (change: Partial<Line>) => void;
  onDelete: () => void;
  onMove: (direction: number) => void;
  onRerun: () => void;
}) {
  const xs = line.polygon.map((p) => p[0]),
    ys = line.polygon.map((p) => p[1]);
  const bounds = [
    Math.min(...xs),
    Math.min(...ys),
    Math.max(...xs),
    Math.max(...ys),
  ];
  return (
    <fieldset className="region-editor" disabled={disabled}>
      <legend>Selected region</legend>
      <div className="region-coordinates">
        {["Left", "Top", "Right", "Bottom"].map((name, i) => (
          <label key={name}>
            {name}
            <input
              aria-label={`Region ${name.toLowerCase()}`}
              type="number"
              min="0"
              max={i % 2 ? height : width}
              value={Math.round(bounds[i])}
              onChange={(e) => {
                const next = [...bounds];
                next[i] = Math.max(
                  0,
                  Math.min(i % 2 ? height : width, Number(e.target.value)),
                );
                if (next[2] > next[0] && next[3] > next[1])
                  onChange({
                    polygon: [
                      [next[0], next[1]],
                      [next[2], next[1]],
                      [next[2], next[3]],
                      [next[0], next[3]],
                    ],
                  });
              }}
            />
          </label>
        ))}
      </div>
      <button
        className="icon-button"
        aria-label="Move line earlier in reading order"
        onClick={() => onMove(-1)}
      >
        <CaretUp />
      </button>
      <button
        className="icon-button"
        aria-label="Move line later in reading order"
        onClick={() => onMove(1)}
      >
        <CaretDown />
      </button>
      <button className="button small secondary" onClick={onRerun}>
        <ArrowClockwise /> Rerun line
      </button>
      <button
        className="icon-button danger"
        aria-label="Delete selected line region"
        onClick={onDelete}
      >
        <Trash />
      </button>
    </fieldset>
  );
}
