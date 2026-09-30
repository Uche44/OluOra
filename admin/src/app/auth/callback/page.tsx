"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { ShieldAlert, Sparkles } from "lucide-react";
import { apiUrl, clearAuthStorage, saveSession } from "@/lib/api";

const STATE_KEY = "google_oauth_state";

function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState("Authenticating...");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError("Authorization code is missing from the redirect URL.");
      return;
    }

    const state = searchParams.get("state");
    const storedState = sessionStorage.getItem(STATE_KEY);
    if (!state || !storedState || state !== storedState) {
      setError("Invalid or missing OAuth state. Please sign in again.");
      return;
    }
    sessionStorage.removeItem(STATE_KEY);

    const exchangeCode = async () => {
      try {
        setStatus("Exchanging credentials...");
        const res = await fetch(`${apiUrl}/api/v1/auth/google/callback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code, state }),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(
            typeof errData?.detail === "string"
              ? errData.detail
              : "OAuth token exchange failed.",
          );
        }

        const data = await res.json();
        saveSession(data.access_token, data.refresh_token, data.user);

        // Verify admin access before letting the session continue. A 403 means
        // the account is valid but not on the admin allowlist.
        setStatus("Verifying admin access...");
        const meRes = await fetch(`${apiUrl}/api/v1/admin/me`, {
          headers: { Authorization: `Bearer ${data.access_token}` },
        });

        if (meRes.status === 403) {
          clearAuthStorage();
          router.replace("/login?denied=1");
          return;
        }
        if (!meRes.ok) {
          throw new Error("Could not verify admin access. Please try again.");
        }

        const me = await meRes.json();
        saveSession(data.access_token, data.refresh_token, {
          id: me.id,
          email: me.email,
          full_name: me.full_name ?? data.user?.full_name,
          profile_picture: data.user?.profile_picture,
        });

        setStatus("Access granted.");
        setTimeout(() => router.replace("/"), 500);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to complete sign in.",
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
            Sign in failed
          </h2>
          <p className="text-sm text-on-surface-variant font-literata leading-relaxed">
            {error}
          </p>
        </div>
        <Link
          href="/login"
          className="w-full py-3 bg-primary text-on-primary font-literata text-sm font-medium rounded-full hover:bg-primary-container transition-colors"
        >
          Return to sign in
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

export default function CallbackPage() {
  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 bg-surface bg-[radial-gradient(ellipse_at_top_right,_var(--color-primary-container),_transparent_60%)]">
      <Suspense fallback={<div className="font-literata text-sm text-on-surface-variant">Loading...</div>}>
        <CallbackHandler />
      </Suspense>
    </div>
  );
}
