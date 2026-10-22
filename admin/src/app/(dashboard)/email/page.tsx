"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Mail,
  Send,
  Users,
} from "lucide-react";
import { getJson, postJson } from "@/lib/http";
import { cn, formatDate } from "@/lib/utils";

interface EmailMessageRow {
  id: string;
  to_email: string;
  user_id: string | null;
  category: string;
  subject: string;
  provider: string;
  status: string;
  error: string | null;
  batch_id: string | null;
  created_at: string;
  sent_at: string | null;
}

interface PaginatedEmails {
  data: EmailMessageRow[];
  pagination: { page: number; limit: number; total: number; pages: number };
}

interface QueueResponse {
  dry_run: boolean;
  recipients: number;
  queued: number;
  batch_id: string | null;
}

const CATEGORY_LABEL: Record<string, string> = {
  signup_welcome: "Signup welcome",
  feedback_reminder: "Feedback reminder",
  waitlist_welcome: "Waitlist welcome",
  waitlist_broadcast: "Waitlist broadcast",
};

const STATUS_STYLES: Record<string, string> = {
  sent: "text-emerald-700 bg-emerald-50 border-emerald-200",
  queued: "text-sky-700 bg-sky-50 border-sky-200",
  skipped: "text-on-surface-variant bg-surface-container border-outline-variant/30",
  failed: "text-red-700 bg-red-50 border-red-200",
};

const inputClass =
  "w-full bg-surface-container-low border border-outline-variant/20 rounded-xl py-2 px-3 font-literata text-sm focus:outline-none focus:border-primary/40 focus:bg-surface-container-lowest transition-colors";

export default function EmailPage() {
  const [rows, setRows] = useState<EmailMessageRow[]>([]);
  const [pagination, setPagination] =
    useState<PaginatedEmails["pagination"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJson<PaginatedEmails>(
        `/admin/email/messages?page=${page}&limit=20`,
      );
      setRows(data.data);
      setPagination(data.pagination);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load emails.");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-6 text-on-surface"
    >
      <div className="flex flex-col">
        <h1 className="font-playfair text-3xl font-bold text-primary">Email</h1>
        <p className="text-on-surface-variant font-literata text-sm mt-1">
          Send broadcasts and reminders, and review every email sent.
        </p>
      </div>

      {notice && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 font-literata text-sm">
          <Check className="w-4 h-4" />
          <span>{notice}</span>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <WaitlistBroadcastCard
          onSent={(msg) => {
            setNotice(msg);
            setPage(1);
            load();
          }}
          onError={setError}
        />
        <FeedbackReminderCard
          onSent={(msg) => {
            setNotice(msg);
            setPage(1);
            load();
          }}
          onError={setError}
        />
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-900 rounded-2xl flex items-center gap-2 font-literata text-sm">
          <AlertTriangle className="w-4 h-4 text-red-700" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex flex-col gap-4">
        <h2 className="font-playfair text-xl font-bold text-primary">Recent sends</h2>
        <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-outline-variant/15 text-[10px] uppercase tracking-wider text-on-surface-variant font-literata">
                  <th className="px-5 py-3 font-medium">Recipient</th>
                  <th className="px-5 py-3 font-medium">Type</th>
                  <th className="px-5 py-3 font-medium">Subject</th>
                  <th className="px-5 py-3 font-medium">Provider</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Sent</th>
                </tr>
              </thead>
              <tbody>
                {loading
                  ? Array.from({ length: 5 }).map((_, i) => (
                      <tr key={i} className="border-b border-outline-variant/10">
                        <td colSpan={6} className="px-5 py-4">
                          <div className="h-4 bg-surface-container rounded animate-pulse" />
                        </td>
                      </tr>
                    ))
                  : rows.map((r) => (
                      <tr
                        key={r.id}
                        className="border-b border-outline-variant/10 last:border-0 hover:bg-surface-container/30 transition-colors"
                      >
                        <td className="px-5 py-4 font-literata text-sm text-primary whitespace-nowrap">
                          {r.to_email}
                        </td>
                        <td className="px-5 py-4">
                          <span className="text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-full border border-outline-variant/30 text-on-surface-variant whitespace-nowrap">
                            {CATEGORY_LABEL[r.category] ?? r.category}
                          </span>
                        </td>
                        <td className="px-5 py-4 max-w-[240px]">
                          <p
                            className="font-literata text-sm text-on-surface-variant truncate"
                            title={r.error || r.subject}
                          >
                            {r.subject}
                          </p>
                        </td>
                        <td className="px-5 py-4 font-literata text-xs text-on-surface-variant">
                          {r.provider}
                        </td>
                        <td className="px-5 py-4">
                          <span
                            className={cn(
                              "text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-full border capitalize",
                              STATUS_STYLES[r.status] ??
                                "border-outline-variant/30 text-on-surface-variant",
                            )}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="px-5 py-4 font-literata text-sm text-on-surface-variant whitespace-nowrap">
                          {formatDate(r.created_at)}
                        </td>
                      </tr>
                    ))}
                {!loading && rows.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-5 py-12 text-center font-literata text-sm text-on-surface-variant/60 italic"
                    >
                      No emails sent yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {pagination && pagination.pages > 1 && (
            <div className="flex items-center justify-between px-5 py-4 border-t border-outline-variant/15">
              <span className="font-literata text-xs text-on-surface-variant">
                Page {pagination.page} of {pagination.pages}
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="p-2 rounded-full border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  disabled={page >= pagination.pages}
                  onClick={() => setPage((p) => p + 1)}
                  className="p-2 rounded-full border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                  aria-label="Next page"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function Card({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: typeof Mail;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl shadow-sm p-6 flex flex-col gap-4">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl bg-surface-container flex items-center justify-center flex-shrink-0">
          <Icon className="w-4 h-4 text-primary" />
        </div>
        <div className="flex flex-col">
          <h2 className="font-playfair text-lg font-bold text-primary">{title}</h2>
          <p className="font-literata text-xs text-on-surface-variant mt-0.5">
            {description}
          </p>
        </div>
      </div>
      {children}
    </div>
  );
}

function useSender(
  path: string,
  buildPayload: () => Record<string, unknown>,
  onSent: (msg: string) => void,
  onError: (msg: string) => void,
) {
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<number | null>(null);

  const run = async (dryRun: boolean) => {
    setBusy(true);
    onError("");
    try {
      const data = await postJson<QueueResponse>(path, {
        ...buildPayload(),
        dry_run: dryRun,
      });
      if (dryRun) {
        setPreview(data.recipients);
      } else {
        setPreview(null);
        onSent(
          data.queued > 0
            ? `Queued ${data.queued} email${data.queued === 1 ? "" : "s"}.`
            : "No eligible recipients — nothing sent.",
        );
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : "Request failed.");
    } finally {
      setBusy(false);
    }
  };

  return { busy, preview, setPreview, run };
}

function WaitlistBroadcastCard({
  onSent,
  onError,
}: {
  onSent: (msg: string) => void;
  onError: (msg: string) => void;
}) {
  const [subject, setSubject] = useState("");
  const [heading, setHeading] = useState("");
  const [body, setBody] = useState("");
  const [limit, setLimit] = useState("");
  const [includeExisting, setIncludeExisting] = useState(false);

  const payload = () => ({
    subject,
    heading: heading || undefined,
    body,
    limit: limit ? Number(limit) : undefined,
    include_existing_users: includeExisting,
  });

  const { busy, preview, setPreview, run } = useSender(
    "/admin/email/waitlist-broadcast",
    payload,
    onSent,
    onError,
  );

  const invalid = !subject.trim() || !body.trim();

  return (
    <Card
      icon={Users}
      title="Waitlist broadcast"
      description="Compose one email and send it to your waitlist."
    >
      <div className="flex flex-col gap-3">
        <input
          value={subject}
          onChange={(e) => {
            setSubject(e.target.value);
            setPreview(null);
          }}
          placeholder="Subject"
          className={inputClass}
        />
        <input
          value={heading}
          onChange={(e) => setHeading(e.target.value)}
          placeholder="Heading (optional — defaults to the subject)"
          className={inputClass}
        />
        <textarea
          value={body}
          onChange={(e) => {
            setBody(e.target.value);
            setPreview(null);
          }}
          placeholder={"Your message. Separate paragraphs with a blank line."}
          rows={7}
          className={cn(inputClass, "resize-y")}
        />
        <div className="flex items-center gap-3 flex-wrap">
          <input
            value={limit}
            onChange={(e) => {
              setLimit(e.target.value.replace(/[^0-9]/g, ""));
              setPreview(null);
            }}
            placeholder="Max recipients"
            className={cn(inputClass, "w-36")}
          />
          <label className="flex items-center gap-2 font-literata text-xs text-on-surface-variant cursor-pointer">
            <input
              type="checkbox"
              checked={includeExisting}
              onChange={(e) => {
                setIncludeExisting(e.target.checked);
                setPreview(null);
              }}
            />
            Include people who already signed up
          </label>
        </div>

        <SendActions
          busy={busy}
          disabled={invalid}
          preview={preview}
          onPreview={() => run(true)}
          onSend={() => run(false)}
          sendLabel="Send to waitlist"
        />
      </div>
    </Card>
  );
}

function FeedbackReminderCard({
  onSent,
  onError,
}: {
  onSent: (msg: string) => void;
  onError: (msg: string) => void;
}) {
  const [minAgeDays, setMinAgeDays] = useState("");
  const [limit, setLimit] = useState("");

  const payload = () => ({
    min_age_days: minAgeDays ? Number(minAgeDays) : undefined,
    limit: limit ? Number(limit) : undefined,
  });

  const { busy, preview, setPreview, run } = useSender(
    "/admin/email/feedback-reminders",
    payload,
    onSent,
    onError,
  );

  return (
    <Card
      icon={Mail}
      title="Feedback reminders"
      description="Nudge users who haven't left feedback yet. Respects opt-outs and a cooldown."
    >
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <input
            value={minAgeDays}
            onChange={(e) => {
              setMinAgeDays(e.target.value.replace(/[^0-9]/g, ""));
              setPreview(null);
            }}
            placeholder="Min account age (days)"
            className={cn(inputClass, "w-52")}
          />
          <input
            value={limit}
            onChange={(e) => {
              setLimit(e.target.value.replace(/[^0-9]/g, ""));
              setPreview(null);
            }}
            placeholder="Max recipients"
            className={cn(inputClass, "w-36")}
          />
        </div>
        <p className="font-literata text-xs text-on-surface-variant">
          Preview the recipient count first — nothing is sent until you confirm.
        </p>

        <SendActions
          busy={busy}
          disabled={false}
          preview={preview}
          onPreview={() => run(true)}
          onSend={() => run(false)}
          sendLabel="Send reminders"
        />
      </div>
    </Card>
  );
}

function SendActions({
  busy,
  disabled,
  preview,
  onPreview,
  onSend,
  sendLabel,
}: {
  busy: boolean;
  disabled: boolean;
  preview: number | null;
  onPreview: () => void;
  onSend: () => void;
  sendLabel: string;
}) {
  const [confirming, setConfirming] = useState(false);

  if (confirming && preview !== null) {
    return (
      <div className="flex items-center gap-2 flex-wrap p-3 rounded-xl bg-surface-container border border-outline-variant/20">
        <span className="font-literata text-xs text-on-surface-variant">
          Send to <strong className="text-primary">{preview}</strong> recipient
          {preview === 1 ? "" : "s"}?
        </span>
        <button
          onClick={() => {
            setConfirming(false);
            onSend();
          }}
          disabled={busy}
          className="flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-primary text-on-primary text-xs font-semibold font-literata hover:opacity-90 disabled:opacity-40 transition cursor-pointer"
        >
          <Send className="w-3.5 h-3.5" />
          Confirm send
        </button>
        <button
          onClick={() => setConfirming(false)}
          className="px-4 py-1.5 rounded-full border border-outline-variant/30 text-xs font-semibold font-literata text-on-surface-variant hover:bg-surface-container-lowest transition cursor-pointer"
        >
          Cancel
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        onClick={() => {
          setConfirming(false);
          onPreview();
        }}
        disabled={busy || disabled}
        className="px-4 py-2 rounded-full border border-outline-variant/30 text-xs font-semibold font-literata text-primary hover:bg-surface-container disabled:opacity-40 transition cursor-pointer"
      >
        Preview recipients
      </button>
      {preview !== null && (
        <button
          onClick={() => setConfirming(true)}
          disabled={busy || disabled || preview === 0}
          className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-primary text-on-primary text-xs font-semibold font-literata hover:opacity-90 disabled:opacity-40 transition cursor-pointer"
        >
          <Send className="w-3.5 h-3.5" />
          {sendLabel}
        </button>
      )}
      {preview !== null && (
        <span className="font-literata text-xs text-on-surface-variant">
          {preview} eligible
        </span>
      )}
    </div>
  );
}
