"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Send,
  Star,
  X,
} from "lucide-react";
import { submitFeedback, type FeedbackCategory } from "@/lib/api";
import { cn } from "@/lib/utils";

interface FeedbackModalProps {
  open: boolean;
  onClose: () => void;
  onSubmitted?: () => void;
}

const CATEGORIES: { id: FeedbackCategory; label: string }[] = [
  { id: "bug", label: "Report a bug" },
  { id: "idea", label: "Share an idea" },
  { id: "praise", label: "Give praise" },
  { id: "other", label: "Something else" },
];

type Status = "idle" | "loading" | "success" | "error";

/** Mounted only while open, so each open starts with a clean form. */
function FeedbackDialog({
  onClose,
  onSubmitted,
}: {
  onClose: () => void;
  onSubmitted?: () => void;
}) {
  const [rating, setRating] = useState<number | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [category, setCategory] = useState<FeedbackCategory>("idea");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  // Escape closes the dialog; lock background scroll while it is open.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || status === "loading") return;

    setStatus("loading");
    setErrorMsg("");
    try {
      await submitFeedback({
        rating,
        category,
        message: message.trim(),
        page: typeof window !== "undefined" ? window.location.pathname : null,
      });
      setStatus("success");
      onSubmitted?.();
      setTimeout(onClose, 1800);
    } catch (err) {
      setStatus("error");
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again.",
      );
    }
  };

  const activeRating = hovered ?? rating;

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        className="fixed inset-0 bg-primary/30 backdrop-blur-sm"
        onClick={() => status !== "loading" && onClose()}
      />

      <motion.div
        role="dialog"
        aria-modal="true"
        aria-labelledby="feedback-title"
        initial={{ opacity: 0, y: 40, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 40, scale: 0.98 }}
        transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        className="relative w-full sm:max-w-lg bg-surface-container-lowest border border-outline-variant/20 rounded-t-3xl sm:rounded-3xl shadow-2xl p-6 sm:p-8"
      >
        <button
          onClick={onClose}
          disabled={status === "loading"}
          aria-label="Close feedback form"
          className="absolute top-4 right-4 p-2 rounded-lg text-on-surface-variant/60 hover:text-primary hover:bg-surface-container transition-colors cursor-pointer disabled:opacity-40"
        >
          <X className="w-4 h-4" />
        </button>

        {status === "success" ? (
          <div className="flex flex-col items-center text-center gap-3 py-10">
            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-700" />
            </div>
            <h2 className="font-playfair text-2xl font-bold text-primary">
              Thank you!
            </h2>
            <p className="font-literata text-sm text-on-surface-variant max-w-xs leading-relaxed">
              Your feedback helps us make OluOra better. We read every note.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            <div className="flex flex-col gap-1 pr-8">
              <h2
                id="feedback-title"
                className="font-playfair text-2xl font-bold text-primary"
              >
                Share your feedback
              </h2>
              <p className="font-literata text-sm text-on-surface-variant">
                Tell us what&apos;s working and what isn&apos;t.
              </p>
            </div>

            {/* Star rating (optional) */}
            <div className="flex flex-col gap-2">
              <label className="font-literata text-xs font-semibold text-on-surface-variant">
                How would you rate OluOra?
              </label>
              <div
                className="flex items-center gap-1.5"
                onMouseLeave={() => setHovered(null)}
              >
                {[1, 2, 3, 4, 5].map((value) => (
                  <button
                    key={value}
                    type="button"
                    aria-label={`${value} star${value > 1 ? "s" : ""}`}
                    onMouseEnter={() => setHovered(value)}
                    onClick={() =>
                      setRating((prev) => (prev === value ? null : value))
                    }
                    className="p-1 cursor-pointer transition-transform hover:scale-110"
                  >
                    <Star
                      className={cn(
                        "w-6 h-6 transition-colors",
                        activeRating && value <= activeRating
                          ? "text-secondary-container fill-secondary-container"
                          : "text-outline-variant",
                      )}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Category */}
            <div className="flex flex-col gap-2">
              <label className="font-literata text-xs font-semibold text-on-surface-variant">
                What&apos;s this about?
              </label>
              <div className="flex flex-wrap gap-2">
                {CATEGORIES.map((c) => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setCategory(c.id)}
                    className={cn(
                      "px-4 py-2 rounded-full text-xs font-literata font-semibold border transition-colors cursor-pointer",
                      category === c.id
                        ? "bg-primary text-on-primary border-primary"
                        : "border-outline-variant/30 text-on-surface-variant hover:bg-surface-container",
                    )}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Message */}
            <div className="flex flex-col gap-2">
              <label className="font-literata text-xs font-semibold text-on-surface-variant">
                Your message
              </label>
              <textarea
                value={message}
                onChange={(e) => {
                  setMessage(e.target.value);
                  if (status === "error") setStatus("idle");
                }}
                rows={4}
                maxLength={2000}
                required
                placeholder="Tell us more..."
                className="w-full resize-none px-4 py-3 rounded-2xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition"
              />
            </div>

            {status === "error" && (
              <div className="flex items-center gap-2 text-xs font-literata text-error">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={!message.trim() || status === "loading"}
              className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-full bg-primary hover:bg-primary-container text-on-primary text-sm font-semibold font-literata transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {status === "loading" ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  Send feedback
                  <Send className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        )}
      </motion.div>
    </>
  );
}

export default function FeedbackModal({
  open,
  onClose,
  onSubmitted,
}: FeedbackModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="feedback-overlay"
          className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-6"
        >
          <FeedbackDialog onClose={onClose} onSubmitted={onSubmitted} />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
