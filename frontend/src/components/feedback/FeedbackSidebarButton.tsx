"use client";

import { MessageSquare } from "lucide-react";
import { useFeedback } from "./FeedbackProvider";

export default function FeedbackSidebarButton({
  onBeforeOpen,
}: {
  onBeforeOpen?: () => void;
}) {
  const { openFeedback } = useFeedback();

  return (
    <button
      onClick={() => {
        onBeforeOpen?.();
        openFeedback();
      }}
      className="flex items-center gap-3 px-4 py-2.5 rounded-xl font-literata text-sm text-on-surface-variant hover:text-primary hover:bg-surface-container/50 transition-colors w-full text-left cursor-pointer"
    >
      <MessageSquare className="w-4 h-4" />
      <span>Leave Feedback</span>
    </button>
  );
}
