"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  assetUrl,
  attachToThread,
  createThread,
  findSimilarThreads,
  getThread,
  listThreads,
  markThreadRead,
  postAnnouncement,
  postReply,
  type ThreadOut,
} from "@/lib/api";

/**
 * The programme channel.
 *
 * Announcements is one continuous thread the company posts into, not a thread
 * per post: a link, then a correction, then a reminder is one conversation,
 * and asking for a subject each time asks it to name things that need no name.
 *
 * Questions stay one thread each, because a question has an answer and a
 * resolved state. They are public to the cohort by default — the answer to one
 * person's question is usually the answer to everyone's — with a private
 * option for what genuinely is one person's business.
 */

type Variant = "participant" | "company";
type Post = ThreadOut["posts"][number];

const ASK_TYPES = [
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

/** Not a thread id: the standing channel that holds every broadcast. */
const ANNOUNCEMENTS = "announcements";

const BROADCAST_TYPES = ["announcement", "resource"];

function isBroadcast(thread: ThreadOut) {
  return BROADCAST_TYPES.includes(thread.type);
}

function clockTime(value: string) {
  return new Date(value).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
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
  // ANNOUNCEMENTS is a standing channel rather than a thread, so it is open
  // from the first day of the programme with nothing in it yet.
  const [openId, setOpenId] = useState<string>(ANNOUNCEMENTS);
  const [open, setOpen] = useState<ThreadOut | null>(null);
  const [composing, setComposing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pane, setPane] = useState<"list" | "conversation">("list");

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

  useEffect(() => {
    if (openId === ANNOUNCEMENTS) {
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

  const broadcasts = threads.filter(isBroadcast);
  const conversations = threads.filter((t) => !isBroadcast(t));
  const latestBroadcast = broadcasts[0];
  // Reading one announcement still means you are in the announcements channel.
  const inAnnouncements =
    !composing && (openId === ANNOUNCEMENTS || Boolean(open && isBroadcast(open)));

  return (
    <div className="chat" data-pane={pane}>
      <aside className="chat-aside">
        <div className="chat-aside-head">
          <strong>Channels</strong>
          {/* The company's only compose surface is the announcements channel
              itself; there is nothing else for them to start. */}
          {variant === "participant" && (
            <button
              className="small"
              onClick={() => {
                setComposing(true);
                setPane("conversation");
              }}
            >
              Ask
            </button>
          )}
        </div>
        <div className="chat-list">
          <button
            className="chat-item"
            aria-selected={inAnnouncements}
            onClick={() => select(ANNOUNCEMENTS)}
          >
            <span className="chat-item-top">
              <span className="chat-item-title">📣 Announcements</span>
              {latestBroadcast && (
                <span className="chat-item-when">{listStamp(latestBroadcast.created_at)}</span>
              )}
            </span>
            <span className="chat-item-preview">
              {latestBroadcast
                ? (lastPost(latestBroadcast)?.body ?? "")
                : "From the company"}
            </span>
          </button>

          {conversations.map((thread) => {
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
          })}
        </div>
      </aside>

      <div className="chat-main">
        {composing ? (
          <NewThread
            programmeId={programmeId}
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
        ) : openId === ANNOUNCEMENTS ? (
          <Announcements
            programmeId={programmeId}
            broadcasts={broadcasts}
            variant={variant}
            onBack={() => setPane("list")}
            onPosted={async () => {
              await load();
              onChange?.();
            }}
          />
        ) : open ? (
          <Conversation
            thread={open}
            onBack={() => (isBroadcast(open) ? select(ANNOUNCEMENTS) : setPane("list"))}
            backLabel={isBroadcast(open) ? "← Announcements" : "←"}
            onPosted={async (thread) => {
              setOpen(thread);
              await load();
              onChange?.();
            }}
          />
        ) : (
          <div className="chat-empty">
            <p className="small">Pick a conversation, or ask a question.</p>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * A run of messages, grouped the way a chat groups them: consecutive posts
 * from one person carry the name once, and a change of day gets a divider.
 */
function MessageList({
  items,
  emptyState,
}: {
  items: { post: Post; badge?: React.ReactNode }[];
  emptyState?: React.ReactNode;
}) {
  const scroller = useRef<HTMLDivElement>(null);

  // A chat shows the newest message, so it opens at the bottom and stays there.
  useEffect(() => {
    const node = scroller.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [items.length]);

  return (
    <div className="chat-scroll" ref={scroller}>
      {items.length === 0 && emptyState}
      {items.map(({ post, badge }, index) => {
        const previous = items[index - 1]?.post;
        const sameDay =
          previous && dayStamp(previous.created_at) === dayStamp(post.created_at);
        const grouped = Boolean(
          previous && sameDay && previous.author_label === post.author_label && !badge,
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
                    {badge}
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
                        <a href={assetUrl(a.url)}>{a.filename}</a>
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
  );
}

/** Write a message, attach a file, or both. */
function Composer({
  placeholder,
  onSend,
  children,
}: {
  placeholder: string;
  onSend: (text: string, file: File | null) => Promise<void>;
  children?: React.ReactNode;
}) {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const picker = useRef<HTMLInputElement>(null);

  const ready = Boolean(text.trim() || file);

  async function send() {
    if (!ready || busy) return;
    setBusy(true);
    setError(null);
    try {
      await onSend(text.trim(), file);
      setText("");
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send that.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {error && (
        <div className="notice bad" style={{ margin: "0.5rem 0.6rem 0" }}>
          {error}
        </div>
      )}
      {file && (
        <div className="chat-attachment">
          <span className="small">📎 {file.name}</span>
          <button className="secondary small" onClick={() => setFile(null)} disabled={busy}>
            Remove
          </button>
        </div>
      )}
      {children}
      <form
        className="chat-compose"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          ref={picker}
          type="file"
          hidden
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          className="secondary"
          onClick={() => picker.current?.click()}
          disabled={busy}
          aria-label="Attach a file"
          title="Attach a file"
        >
          📎
        </button>
        <textarea
          aria-label="Message"
          rows={1}
          placeholder={placeholder}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            // Enter sends, Shift+Enter breaks the line — the chat convention.
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button type="submit" disabled={busy || !ready}>
          {busy ? "Sending…" : "Send"}
        </button>
      </form>
    </>
  );
}

/**
 * The standing announcements channel.
 *
 * It exists from the first day of the programme rather than appearing once
 * somebody posts, because a participant looking for "what has the company
 * told us" needs somewhere to look before there is anything in it.
 */
function Announcements({
  programmeId,
  broadcasts,
  variant,
  onBack,
  onPosted,
}: {
  programmeId: string;
  broadcasts: ThreadOut[];
  variant: Variant;
  onBack: () => void;
  onPosted: () => Promise<void>;
}) {
  const [requiresAck, setRequiresAck] = useState(false);

  // One feed, not one card per thread: the continuous thread holds most of it,
  // and anything that needed acknowledging sits in the same timeline.
  const items = broadcasts
    .flatMap((thread) =>
      thread.posts.map((post) => ({
        post,
        badge: thread.requires_ack ? <span className="tag">acknowledge</span> : undefined,
        at: post.created_at,
      })),
    )
    .sort((a, b) => a.at.localeCompare(b.at));

  return (
    <>
      <div className="chat-head">
        <button className="secondary small chat-back" onClick={onBack}>
          ←
        </button>
        <span className="chat-head-title">📣 Announcements</span>
      </div>

      <MessageList
        items={items}
        emptyState={
          <div className="chat-empty">
            <p className="small">
              {variant === "company"
                ? "Nothing announced yet. Anything you post here reaches everyone on the programme at once."
                : "Nothing announced yet. Anything the company tells the whole cohort appears here."}
            </p>
          </div>
        }
      />

      {variant === "company" ? (
        <Composer
          placeholder="Share something with the cohort"
          onSend={async (text, file) => {
            await postAnnouncement(programmeId, { body: text, file, requiresAck });
            setRequiresAck(false);
            await onPosted();
          }}
        >
          <div className="check" style={{ padding: "0 0.6rem" }}>
            <input
              id="requires_ack"
              type="checkbox"
              checked={requiresAck}
              onChange={(e) => setRequiresAck(e.target.checked)}
            />
            <label htmlFor="requires_ack" className="small">
              Require everyone to acknowledge this — it blocks their dashboard until they
              confirm.
            </label>
          </div>
        </Composer>
      ) : (
        <p className="small muted" style={{ padding: "0.6rem 0.9rem", margin: 0 }}>
          Only the company posts here. Use Ask to put a question to them.
        </p>
      )}
    </>
  );
}

function Conversation({
  thread,
  onBack,
  backLabel = "←",
  onPosted,
}: {
  thread: ThreadOut;
  onBack: () => void;
  backLabel?: string;
  onPosted: (thread: ThreadOut) => Promise<void>;
}) {
  return (
    <>
      <div className="chat-head">
        {/* Going back to the announcements channel matters at every width; the
            bare arrow only exists because narrow screens hide the list. */}
        <button
          className={backLabel === "←" ? "secondary small chat-back" : "secondary small"}
          onClick={onBack}
        >
          {backLabel}
        </button>
        <span className="chat-head-title">{thread.title ?? "(untitled)"}</span>
        {thread.type === "direct" && <span className="tag">private</span>}
        {thread.pinned && <span className="tag">pinned</span>}
        {thread.status === "answered" && <span className="tag open">answered</span>}
      </div>

      <MessageList items={thread.posts.map((post) => ({ post }))} />

      <Composer
        placeholder="Write a message"
        onSend={async (text, file) => {
          let latest = thread;
          if (text) latest = await postReply(thread.id, text);
          if (file) latest = await attachToThread(thread.id, file);
          await onPosted(latest);
        }}
      />
    </>
  );
}

function NewThread({
  programmeId,
  onCancel,
  onPosted,
  onOpenExisting,
  onBack,
}: {
  programmeId: string;
  onCancel: () => void;
  onPosted: (thread: ThreadOut) => void;
  onOpenExisting: (id: string) => void;
  onBack: () => void;
}) {
  const [type, setType] = useState(ASK_TYPES[0].value);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [similar, setSimilar] = useState<{ id: string; title: string; status: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // FR-611b — the same question already asked and answered is shown while they
  // type, so the channel does not fill with eight copies of one question.
  useEffect(() => {
    const term = title.trim();
    if (type === "direct" || term.length < 4) {
      setSimilar([]);
      return;
    }
    const timer = setTimeout(() => {
      findSimilarThreads(programmeId, term)
        .then(setSimilar)
        .catch(() => setSimilar([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [title, type, programmeId]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await createThread(programmeId, {
        type,
        title: title.trim(),
        body: body.trim(),
      });
      onPosted(result.thread);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not post that.");
    } finally {
      setBusy(false);
    }
  }

  const chosen = ASK_TYPES.find((t) => t.value === type);

  return (
    <>
      <div className="chat-head">
        <button className="secondary small chat-back" onClick={onBack}>
          ←
        </button>
        <span className="chat-head-title">Ask a question</span>
      </div>

      <form className="chat-form" onSubmit={submit}>
        <div className="field">
          <label htmlFor="thread_type">Who should see this</label>
          <select id="thread_type" value={type} onChange={(e) => setType(e.target.value)}>
            {ASK_TYPES.map((t) => (
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

        {error && <div className="notice bad">{error}</div>}
        <div className="row">
          <button type="submit" disabled={busy || !title.trim() || !body.trim()}>
            {busy ? "Posting…" : "Post"}
          </button>
          <button type="button" className="secondary" onClick={onCancel}>
            Cancel
          </button>
        </div>
        <p className="small muted" style={{ marginBottom: 0 }}>
          You can attach files once the question is posted.
        </p>
      </form>
    </>
  );
}
