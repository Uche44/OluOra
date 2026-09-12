"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { ShieldAlert, Sparkles } from "lucide-react";

const LS_STATE_KEY = "google_oauth_state";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState("Authenticating...");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError("Authorization code is missing from redirect URL.");
      return;
    }

    // Read the OAuth state echoed by Google and validate it against the one we
    // saved when initiating the flow from this browser tab. If it doesn't match,
    // the redirect was not part of a login this user actually started (CSRF).
    const state = searchParams.get("state");
    const storedState = sessionStorage.getItem(LS_STATE_KEY);
    if (!state || !storedState || state !== storedState) {
      setError("Invalid or missing OAuth state. Please sign in again.");
      return;
    }
    // State was consumed by this login attempt.
    sessionStorage.removeItem(LS_STATE_KEY);

    const exchangeCode = async () => {
      try {
        setStatus("Gimme a sec...");
        const apiUrl =
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/v1/auth/google/callback`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ code, state }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(
            errData?.detail || "OAuth token exchange handshake failed",
          );
        }

        const data = await res.json();

        setStatus("Syncing workspace details...");

        // Save security tokens and profile to browser session cache
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.setItem("user", JSON.stringify(data.user));

        setStatus("Authentication complete!");

        // Redirect to creator dashboard panel
        setTimeout(() => {
          router.push("/dashboard");
        }, 800);
      } catch (err: any) {
        setError(
          err.message || "Failed to process Google sign in redirect callback.",
        );
      }
    };

    exchangeCode();
  }, [searchParams, router]);

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md bg-white border border-error-container rounded-3xl p-8 shadow-xl text-center flex flex-col items-center gap-6"
      >
        <div className="w-16 h-16 rounded-full bg-error-container/20 flex items-center justify-center text-error">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <div className="flex flex-col gap-2">
          <h2 className="font-playfair text-2xl font-bold text-primary">
            Login Failed
          </h2>
          <p className="text-sm text-on-surface-variant font-literata leading-relaxed">
            {error}
          </p>
        </div>
        <Link
          href="/login"
          className="w-full py-3 bg-primary text-on-primary font-literata text-sm font-medium rounded-full hover:bg-primary-container transition-colors duration-150"
        >
          Return to Sign In
        </Link>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-md bg-white border border-outline-variant/20 rounded-3xl p-8 shadow-xl text-center flex flex-col items-center gap-6"
    >
      {/* Premium loader spinner */}
      <div className="relative w-16 h-16 flex items-center justify-center">
        <div className="absolute inset-0 rounded-full border-4 border-primary-container/10 border-t-primary animate-spin" />
      </div>

      <div className="flex flex-col gap-2">
        <h3 className="font-playfair text-xl font-bold text-primary">
          Signing you in
        </h3>
        <div className="flex items-center justify-center gap-2 text-sm text-on-surface-variant font-literata">
          <Sparkles className="w-4 h-4 text-secondary-container" />
          <span>{status}</span>
        </div>
      </div>
    </motion.div>
  );
}

function LoadingFallback() {
  return (
    <div className="w-full max-w-md bg-white border border-outline-variant/20 rounded-3xl p-8 shadow-xl text-center flex flex-col items-center gap-6">
      <div className="relative w-16 h-16 flex items-center justify-center">
        <div className="absolute inset-0 rounded-full border-4 border-primary-container/10 border-t-primary animate-spin" />
      </div>
      <h3 className="font-playfair text-xl font-bold text-primary">
        Signing you in...
      </h3>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 bg-surface bg-[radial-gradient(ellipse_at_top_right,_var(--color-primary-container),_transparent_60%)]">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-primary/5 blur-3xl" />

      <Suspense fallback={<LoadingFallback />}>
        <CallbackHandler />
      </Suspense>
    </div>
  );
}
