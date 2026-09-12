"use client";

import { Suspense } from "react";
import ConnectCallback from "@/components/auth/ConnectCallback";

export default function TikTokConnectCallbackPage() {
  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 bg-surface bg-[radial-gradient(ellipse_at_top_right,_var(--color-primary-container),_transparent_60%)]">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-primary/5 blur-3xl" />
      <Suspense
        fallback={
          <div className="w-full max-w-md bg-white border border-outline-variant/20 rounded-3xl p-8 shadow-xl text-center font-literata text-sm text-on-surface-variant">
            Connecting your TikTok account...
          </div>
        }
      >
        <ConnectCallback provider="tiktok" />
      </Suspense>
    </div>
  );
}
