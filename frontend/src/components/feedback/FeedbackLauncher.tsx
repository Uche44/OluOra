"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { MessageSquare, X } from "lucide-react";
import { useFeedback } from "./FeedbackProvider";

const SHOWN_KEY = "oluora_feedback_last_shown";
const SUBMITTED_KEY = "oluora_feedback_submitted_at";
const SESSION_KEY = "oluora_feedback_nudged";
// Wait a little while after landing, then nudge at most once per session.
const NUDGE_DELAY_MS = 45_000;
// Back off for a month after showing (or after the user submits).
const THROTTLE_MS = 30 * 24 * 60 * 60 * 1000;

function readNumber(key: string): number {
  try {
    return Number(localStorage.getItem(key) || 0);
  } catch {
    return 0;
  }
}

export default function FeedbackLauncher() {
  const { open, openFeedback } = useFeedback();
  const [nudge, setNudge] = useState(false);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    // Only nudge once per browser session.
    try {
      if (sessionStorage.getItem(SESSION_KEY) === "1") return;
    } catch {
      return;
    }

    const now = Date.now();
    if (now - readNumber(SHOWN_KEY) < THROTTLE_MS) return;
    if (now - readNumber(SUBMITTED_KEY) < THROTTLE_MS) return;

    timerRef.current = window.setTimeout(() => {
      setNudge(true);
      try {
        sessionStorage.setItem(SESSION_KEY, "1");
        localStorage.setItem(SHOWN_KEY, String(Date.now()));
      } catch (e) {
        console.error(e);
      }
    }, NUDGE_DELAY_MS);

    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, []);

  const openAndDismissNudge = () => {
    setNudge(false);
    openFeedback();
  };

  return (
    <>
      <button
        onClick={openAndDismissNudge}
        aria-label="Leave feedback"
        className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 px-4 py-3 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata shadow-lg shadow-primary/20 transition-all duration-150 hover:scale-105 cursor-pointer"
      >
        <MessageSquare className="w-4 h-4" />
        <span className="hidden sm:inline">Feedback</span>
      </button>

      <AnimatePresence>
        {nudge && !open && (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.97 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="fixed bottom-24 right-6 z-40 w-[300px] max-w-[calc(100vw-3rem)] bg-surface-container-lowest border border-outline-variant/20 rounded-3xl shadow-2xl p-5"
          >
            <button
              onClick={() => setNudge(false)}
              aria-label="Dismiss"
              className="absolute top-3 right-3 p-1.5 rounded-lg text-on-surface-variant/50 hover:text-primary hover:bg-surface-container transition-colors cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>

            <h3 className="font-playfair text-base font-bold text-primary pr-6">
              How&apos;s OluOra treating you?
            </h3>
            <p className="font-literata text-xs text-on-surface-variant leading-relaxed mt-1.5">
              Got a minute? We&apos;d love to hear what&apos;s working and what
              we could do better.
            </p>

            <div className="flex items-center gap-2 mt-4">
              <button
                onClick={() => {
                  setNudge(false);
                  openFeedback();
                }}
                className="flex-1 px-4 py-2 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition-all cursor-pointer"
              >
                Leave feedback
              </button>
              <button
                onClick={() => setNudge(false)}
                className="px-4 py-2 rounded-full border border-outline-variant/30 text-on-surface-variant text-xs font-semibold font-literata hover:bg-surface-container transition-colors cursor-pointer"
              >
                Maybe later
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
