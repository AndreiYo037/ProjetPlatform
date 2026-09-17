"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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
 * The programme channel, as a chat rather than a forum.
 *
 * Questions are public to the cohort by default because the answer to one
 * person's question is usually the answer to everyone's, and a rep answering
 * the same thing eight times privately is how a channel dies. The private
 * option is there for the cases that genuinely are one person's business.
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

function clockTime(value: string) {
  return new Date(value).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Today shows a time, this week a weekday, older a date — as a chat list does. */
function listStamp(value: string) {
  const at = new Date(value);
  const days = (Date.now() - at.getTime()) / 86_400_000;
  if (days < 1) return clockTime(value);
  if (days < 7) return at.toLocaleDateString(undefined, { weekday: "short" });
  return at.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

function dayStamp(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

function initials(label: string) {
  const words = label.replace(/^(the|a)\s+/i, "").split(/\s+/).filter(Boolean);
  return (words[0]?.[0] ?? "?").toUpperCase() + (words[1]?.[0]?.toUpperCase() ?? "");
}

function avatarClass(role: string) {
  if (role === "rep") return "avatar company";
  if (role === "admin") return "avatar admin";
  return "avatar";
}

function lastPost(thread: ThreadOut) {
  return thread.posts[thread.posts.length - 1];
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
  const [openId, setOpenId] = useState<string | null>(null);
  const [open, setOpen] = useState<ThreadOut | null>(null);
  const [composing, setComposing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pane, setPane] = useState<"list" | "conversation">("list");

  const load = useCallback(async () => {
    try {
      const rows = await listThreads(programmeId);
      setThreads(rows);
      // A chat opens on a conversation, not on an empty frame.
      setOpenId((current) => current ?? rows[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the channel.");
    }
  }, [programmeId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!openId) {
      setOpen(null);
      return;
    }
    let cancelled = false;
    getThread(openId)
      .then((thread) => {
        if (cancelled) return;
        setOpen(thread);
        // Opening is reading. The endpoint is participant-scoped (/me), so the
        // company side does not call it.
        if (variant === "participant") {
          markThreadRead(thread.id)
            .then(() => onChange?.())
            .catch(() => {});
        }
      })
      .catch(() => {
        if (!cancelled) setOpen(null);
      });
    return () => {
      cancelled = true;
    };
  }, [openId, variant, onChange]);

  function select(id: string) {
    setComposing(false);
    setOpenId(id);
    setPane("conversation");
  }

  if (error) return <div className="notice bad">{error}</div>;
  if (!threads) return <p className="muted small">Loading the channel…</p>;

  return (
    <div className="chat" data-pane={pane}>
      <aside className="chat-aside">
        <div className="chat-aside-head">
          <strong>Conversations</strong>
          <button
            className="small"
            onClick={() => {
              setComposing(true);
              setPane("conversation");
            }}
          >
            New
          </button>
        </div>
        <div className="chat-list">
          {threads.length === 0 ? (
            <p className="small muted" style={{ padding: "0.9rem" }}>
              {variant === "company"
                ? "When participants ask something it lands here."
                : "Nothing yet. If something in the brief is unclear, it is probably unclear to everyone."}
            </p>
          ) : (
            threads.map((thread) => {
              const last = lastPost(thread);
              return (
                <button
                  key={thread.id}
                  className="chat-item"
                  aria-selected={!composing && thread.id === openId}
                  onClick={() => select(thread.id)}
                >
                  <span className="chat-item-top">
                    <span className="chat-item-title">{thread.title ?? "(untitled)"}</span>
                    <span className="chat-item-when">{listStamp(thread.created_at)}</span>
                  </span>
                  <span className="chat-item-preview">
                    {thread.type === "direct" && "🔒 "}
                    {last ? `${last.author_label}: ${last.body}` : "No messages"}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </aside>

      <div className="chat-main">
        {composing ? (
          <NewThread
            programmeId={programmeId}
            variant={variant}
            onCancel={() => setComposing(false)}
            onPosted={async (thread) => {
              setComposing(false);
              setOpenId(thread.id);
              await load();
              onChange?.();
            }}
            onOpenExisting={(id) => select(id)}
            onBack={() => setPane("list")}
          />
        ) : open ? (
          <Conversation
            thread={open}
            onBack={() => setPane("list")}
            onReplied={async (thread) => {
              setOpen(thread);
              await load();
              onChange?.();
            }}
          />
        ) : (
          <div className="chat-empty">
            <p className="small">Pick a conversation, or start a new one.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function Conversation({
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
  const scroller = useRef<HTMLDivElement>(null);

  // A chat shows the newest message, so it opens at the bottom and stays there
  // as replies land.
  useEffect(() => {
    const node = scroller.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [thread.id, thread.posts.length]);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const text = body.trim();
    if (!text) return;
    setBusy(true);
    setError(null);
    try {
      onReplied(await postReply(thread.id, text));
      setBody("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send that.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="chat-head">
        <button className="secondary small chat-back" onClick={onBack}>
          ←
        </button>
        <span className="chat-head-title">{thread.title ?? "(untitled)"}</span>
        {thread.type === "direct" && <span className="tag">private</span>}
        {thread.pinned && <span className="tag">pinned</span>}
        {thread.status === "answered" && <span className="tag open">answered</span>}
      </div>

      <div className="chat-scroll" ref={scroller}>
        {thread.posts.map((post, index) => {
          const previous = thread.posts[index - 1];
          const sameDay =
            previous && dayStamp(previous.created_at) === dayStamp(post.created_at);
          const grouped = Boolean(
            previous && sameDay && previous.author_label === post.author_label,
          );
          return (
            <div key={post.id}>
              {!sameDay && (
                <p
                  className="small muted"
                  style={{ textAlign: "center", margin: "1rem 0 0.2rem" }}
                >
                  {dayStamp(post.created_at)}
                </p>
              )}
              <div className={grouped ? "chat-msg same" : "chat-msg"}>
                {grouped ? (
                  <span className="avatar spacer" aria-hidden="true" />
                ) : (
                  <span className={avatarClass(post.author_role)} aria-hidden="true">
                    {initials(post.author_label)}
                  </span>
                )}
                <div className="chat-msg-body">
                  {!grouped && (
                    <div className="chat-msg-meta">
                      <span className="chat-msg-author">{post.author_label}</span>
                      <span className="chat-msg-when">{clockTime(post.created_at)}</span>
                    </div>
                  )}
                  {post.removed ? (
                    <p className="chat-msg-text small muted">This message was removed.</p>
                  ) : (
                    <p className="chat-msg-text">{post.body}</p>
                  )}
                  {post.attachments.length > 0 && (
                    <ul className="small" style={{ margin: "0.3rem 0 0" }}>
                      {post.attachments.map((a) => (
                        <li key={a.url}>
                          <a href={a.url}>{a.filename}</a>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {error && (
        <div className="notice bad" style={{ margin: "0.5rem 0.6rem 0" }}>
          {error}
        </div>
      )}

      <form className="chat-compose" onSubmit={send}>
        <textarea
          aria-label="Message"
          rows={1}
          placeholder="Write a message"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => {
            // Enter sends, Shift+Enter breaks the line — the chat convention.
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(e);
            }
          }}
        />
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
  onBack,
}: {
  programmeId: string;
  variant: Variant;
  onCancel: () => void;
  onPosted: (thread: ThreadOut) => void;
  onOpenExisting: (id: string) => void;
  onBack: () => void;
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
    <>
      <div className="chat-head">
        <button className="secondary small chat-back" onClick={onBack}>
          ←
        </button>
        <span className="chat-head-title">
          {variant === "company" ? "Post to the cohort" : "New conversation"}
        </span>
      </div>

      <form className="chat-form" onSubmit={submit}>
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
            rows={4}
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
              Require everyone to acknowledge this. Use it when the week changes — it
              blocks their dashboard until they confirm they have read it.
            </label>
          </div>
        )}

        {error && <div className="notice bad">{error}</div>}
        <div className="row">
          <button type="submit" disabled={busy || !title.trim() || !body.trim()}>
            {busy ? "Posting…" : "Post"}
          </button>
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </>
  );
}
