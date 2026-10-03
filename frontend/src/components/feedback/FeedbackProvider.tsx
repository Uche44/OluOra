"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";
import FeedbackModal from "./FeedbackModal";

interface FeedbackContextValue {
  open: boolean;
  openFeedback: () => void;
  closeFeedback: () => void;
}

const FeedbackContext = createContext<FeedbackContextValue | null>(null);

export function useFeedback(): FeedbackContextValue {
  const ctx = useContext(FeedbackContext);
  if (!ctx) {
    throw new Error("useFeedback must be used within a FeedbackProvider");
  }
  return ctx;
}

export default function FeedbackProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  const openFeedback = useCallback(() => setOpen(true), []);
  const closeFeedback = useCallback(() => setOpen(false), []);

  const value = useMemo(
    () => ({ open, openFeedback, closeFeedback }),
    [open, openFeedback, closeFeedback],
  );

  // Remember the last submission so the pro-active nudge backs off afterwards.
  const handleSubmitted = useCallback(() => {
    try {
      localStorage.setItem("oluora_feedback_submitted_at", String(Date.now()));
    } catch (e) {
      console.error(e);
    }
  }, []);

  return (
    <FeedbackContext.Provider value={value}>
      {children}
      <FeedbackModal
        open={open}
        onClose={closeFeedback}
        onSubmitted={handleSubmitted}
      />
    </FeedbackContext.Provider>
  );
}
