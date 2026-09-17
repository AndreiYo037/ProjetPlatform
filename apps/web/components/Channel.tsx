"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createThread,
  findSimilarThreads,
  getThread,
  listThreads,
  markThreadRead,
  postReply,
  type ThreadOut,
} from "@/lib/api";

/**
 * The programme channel: everyone's questions and the company's answers in one
 * place, plus a private line to the rep.
 *
 * Questions are public to the cohort by default because the answer to one
 * person's question is usually the answer to everyone's, and a rep answering
 * the same thing eight times in DMs is how a channel dies. The private option
 * is there for the cases that genuinely are one person's business.
 */

type Variant = "participant" | "company";

const PARTICIPANT_TYPES = [
  {
    value: "question_challenge",
    label: "About the brief",
    hint: "Scope, data, what counts as done. Everyone on the programme sees this.",
  },
  {
    value: "question_logistics",
    label: "Logistics",
    hint: "Timing, submission, the pitch. Everyone on the programme sees this.",
  },
  {
    value: "direct",
    label: "Private message",
    hint: "Goes to the company rep and admin only. Nobody else on the programme sees it.",
  },
];

const COMPANY_TYPES = [
  {
    value: "announcement",
    label: "Announcement",
    hint: "Goes to everyone on the programme at once.",
  },
  {
    value: "resource",
    label: "Resource",
    hint: "Something you are handing the cohort — a file, a link, a clarification.",
  },
];

function typesFor(variant: Variant) {
  return variant === "company" ? COMPANY_TYPES : PARTICIPANT_TYPES;
}

function when(value: string) {
  return new Date(value).toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function typeLabel(type: string) {
  if (type === "direct") return "private";
  return type.replace(/^question_/, "").replace(/_/g, " ");
}

export default function Channel({
  programmeId,
  variant = "participant",
  onChange,
}: {
  programmeId: string;
  variant?: Variant;
  onChange?: () => void;
}) {
  const [threads, setThreads] = useState<ThreadOut[] | null>(null);
  const [open, setOpen] = useState<ThreadOut | null>(null);
  const [composing, setComposing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setThreads(await listThreads(programmeId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the channel.");
    }
  }, [programmeId]);

  useEffect(() => {
    load();
  }, [load]);

  async function openThread(id: string) {
    setError(null);
    try {
      const thread = await getThread(id);
      setOpen(thread);
      // Opening is reading, so the unread badge should clear without a
      // separate "mark as read" the participant has to remember. The endpoint
      // is participant-scoped (/me), so it is not called for the company side.
      if (variant === "participant") await markThreadRead(id).catch(() => {});
      onChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open that thread.");
    }
  }

  if (error) return <div className="notice bad">{error}</div>;
  if (!threads) return <p className="muted small">Loading the channel…</p>;

  if (composing) {
    return (
      <NewThread
        programmeId={programmeId}
        variant={variant}
        onCancel={() => setComposing(false)}
        onPosted={async (thread) => {
          setComposing(false);
          setOpen(thread);
          await load();
          onChange?.();
        }}
        onOpenExisting={async (id) => {
          setComposing(false);
          await openThread(id);
        }}
      />
    );
  }

  if (open) {
    return (
      <ThreadView
        thread={open}
        onBack={async () => {
          setOpen(null);
          await load();
          onChange?.();
        }}
        onReplied={setOpen}
      />
    );
  }

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <p className="small muted" style={{ margin: 0 }}>
          {variant === "company"
            ? "Questions from the cohort, and anything you post to them."
            : "Questions, answers and anything the company posts."}
        </p>
        <button onClick={() => setComposing(true)}>
          {variant === "company" ? "Post to the cohort" : "Ask a question"}
        </button>
      </div>

      {threads.length === 0 ? (
        <div className="panel">
          <strong>Nothing posted yet.</strong>
          <p className="small muted" style={{ margin: "0.4rem 0 0" }}>
            {variant === "company"
              ? "When participants ask something it lands here. You can also post an announcement to everyone."
              : "Be the first — if something in the brief is unclear, it is probably unclear to everyone."}
          </p>
        </div>
      ) : (
        threads.map((thread) => (
          <div
            className="card"
            key={thread.id}
            role="button"
            tabIndex={0}
            style={{ cursor: "pointer" }}
            onClick={() => openThread(thread.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openThread(thread.id);
              }
            }}
          >
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div>
                <strong>{thread.title ?? "(untitled)"}</strong>
                <div className="small muted">
                  {typeLabel(thread.type)} · {Math.max(0, thread.posts.length - 1)} repl
                  {thread.posts.length - 1 === 1 ? "y" : "ies"} · {when(thread.created_at)}
                </div>
              </div>
              <div className="row">
                {thread.pinned && <span className="tag">pinned</span>}
                {thread.type === "direct" && <span className="tag">private</span>}
                {thread.status === "answered" && <span className="tag open">answered</span>}
              </div>
            </div>
          </div>
        ))
      )}
    </>
  );
}

function ThreadView({
  thread,
  onBack,
  onReplied,
}: {
  thread: ThreadOut;
  onBack: () => void;
  onReplied: (thread: ThreadOut) => void;
}) {
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    setError(null);
    try {
      onReplied(await postReply(thread.id, body.trim()));
      setBody("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send that.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button className="secondary" onClick={onBack}>
        ← All messages
      </button>

      <h3 style={{ marginBottom: "0.2rem" }}>{thread.title ?? "(untitled)"}</h3>
      <div className="row small muted" style={{ marginBottom: "1rem" }}>
        <span>{typeLabel(thread.type)}</span>
        {thread.type === "direct" && <span className="tag">private</span>}
        {thread.status === "answered" && <span className="tag open">answered</span>}
      </div>

      {thread.posts.map((post) => (
        <div className="card" key={post.id}>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong>{post.author_label}</strong>
            <span className="small muted">{when(post.created_at)}</span>
          </div>
          {post.removed ? (
            <p className="small muted" style={{ margin: "0.4rem 0 0" }}>
              This message was removed.
            </p>
          ) : (
            <p style={{ whiteSpace: "pre-wrap", margin: "0.4rem 0 0" }}>{post.body}</p>
          )}
          {post.attachments.length > 0 && (
            <ul className="small" style={{ marginBottom: 0 }}>
              {post.attachments.map((a) => (
                <li key={a.url}>
                  <a href={a.url}>{a.filename}</a>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}

      <form onSubmit={send}>
        <div className="field">
          <label htmlFor="reply">Reply</label>
          <textarea
            id="reply"
            rows={3}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            required
          />
        </div>
        {error && <div className="notice bad">{error}</div>}
        <button type="submit" disabled={busy || !body.trim()}>
          {busy ? "Sending…" : "Send"}
        </button>
      </form>
    </>
  );
}

function NewThread({
  programmeId,
  variant,
  onCancel,
  onPosted,
  onOpenExisting,
}: {
  programmeId: string;
  variant: Variant;
  onCancel: () => void;
  onPosted: (thread: ThreadOut) => void;
  onOpenExisting: (id: string) => void;
}) {
  const options = typesFor(variant);
  const [type, setType] = useState(options[0].value);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [requiresAck, setRequiresAck] = useState(false);
  const [similar, setSimilar] = useState<{ id: string; title: string; status: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // FR-611b — the same question already asked and answered is shown while they
  // type, so the channel does not fill with eight copies of one question.
  useEffect(() => {
    const term = title.trim();
    if (variant === "company" || type === "direct" || term.length < 4) {
      setSimilar([]);
      return;
    }
    const timer = setTimeout(() => {
      findSimilarThreads(programmeId, term)
        .then(setSimilar)
        .catch(() => setSimilar([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [title, type, programmeId, variant]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await createThread(programmeId, {
        type,
        title: title.trim(),
        body: body.trim(),
        requires_ack: variant === "company" && requiresAck,
      });
      onPosted(result.thread);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not post that.");
    } finally {
      setBusy(false);
    }
  }

  const chosen = options.find((t) => t.value === type);

  return (
    <form onSubmit={submit}>
      <button type="button" className="secondary" onClick={onCancel}>
        ← All messages
      </button>

      <div className="field">
        <label htmlFor="thread_type">Who should see this</label>
        <select id="thread_type" value={type} onChange={(e) => setType(e.target.value)}>
          {options.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
        {chosen && <div className="hint">{chosen.hint}</div>}
      </div>

      <div className="field">
        <label htmlFor="thread_title">Subject</label>
        <input
          id="thread_title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          maxLength={400}
        />
      </div>

      {similar.length > 0 && (
        <div className="notice">
          <strong>Already asked</strong>
          <p className="small" style={{ margin: "0.4rem 0" }}>
            This may already have an answer:
          </p>
          <ul className="small" style={{ marginBottom: 0 }}>
            {similar.map((s) => (
              <li key={s.id}>
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    onOpenExisting(s.id);
                  }}
                >
                  {s.title}
                </a>
                {s.status === "answered" && <span className="tag open">answered</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="field">
        <label htmlFor="thread_body">Your message</label>
        <textarea
          id="thread_body"
          rows={5}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          required
        />
      </div>

      {variant === "company" && (
        <div className="check">
          <input
            id="requires_ack"
            type="checkbox"
            checked={requiresAck}
            onChange={(e) => setRequiresAck(e.target.checked)}
          />
          <label htmlFor="requires_ack">
            Require everyone to acknowledge this. Use it when the week changes —
            it blocks their dashboard until they confirm they have read it.
          </label>
        </div>
      )}

      {error && <div className="notice bad">{error}</div>}
      <button type="submit" disabled={busy || !title.trim() || !body.trim()}>
        {busy ? "Posting…" : "Post"}
      </button>
    </form>
  );
}
