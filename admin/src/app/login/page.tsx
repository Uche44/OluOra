"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { ArrowRight, AlertCircle, ShieldCheck, Lock } from "lucide-react";
import { startGoogleLogin, hasSession, getStoredUser } from "@/lib/api";

const GoogleLogo = () => (
  <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
  </svg>
);

export default function AdminLoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      setDenied(params.get("denied") === "1");
    }
    // Already signed in as an admin? Skip the login screen.
    if (hasSession() && getStoredUser()) {
      window.location.href = "/";
    }
  }, []);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      await startGoogleLogin();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to reach the authentication server.",
      );
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 overflow-hidden bg-surface bg-[radial-gradient(ellipse_at_top_right,_var(--color-primary-container),_transparent_60%)]">
      <div className="absolute top-1/4 -left-32 w-96 h-96 rounded-full bg-primary/5 blur-3xl" />
      <div className="absolute bottom-10 right-0 w-80 h-80 rounded-full bg-secondary-container/10 blur-3xl" />

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="bg-white/80 backdrop-blur-lg border border-outline-variant/30 rounded-3xl p-10 shadow-2xl">
          <div className="flex flex-col items-center gap-6">
            <div className="flex flex-col items-center gap-3">
              <div className="flex items-center gap-2.5">
                <Image
                  src="/icons/logo.png"
                  alt="OluOra"
                  width={40}
                  height={40}
                  className="w-9 h-9 object-contain"
                />
                <span className="font-playfair text-2xl font-bold text-primary">
                  OluOra
                </span>
              </div>
              <span className="ai-badge">Internal Admin</span>
            </div>

            <div className="text-center">
              <h2 className="font-playfair text-2xl font-bold text-primary">
                Admin sign in
              </h2>
              <p className="text-sm text-on-surface-variant font-literata mt-1 leading-relaxed">
                Restricted to allowlisted OluOra staff accounts.
              </p>
            </div>

            {denied && (
              <div className="w-full flex gap-3 p-4 bg-error-container/30 border border-error-container text-error rounded-2xl font-literata text-xs items-start">
                <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span>
                  Access denied. This account is not on the admin allowlist.
                </span>
              </div>
            )}

            {error && (
              <div className="w-full flex gap-3 p-4 bg-error-container/30 border border-error-container text-error rounded-2xl font-literata text-xs items-start">
                <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={handleLogin}
              disabled={loading}
              className="w-full flex items-center justify-center gap-3 bg-primary text-on-primary font-literata text-sm font-medium py-3.5 px-6 rounded-full hover:bg-primary-container hover:shadow-lg transition-all duration-200 disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-on-primary border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <GoogleLogo />
                  <span>Continue with Google</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </>
              )}
            </button>

            <div className="w-full flex flex-col gap-2 border-t border-outline-variant/20 pt-6 text-[10px] text-on-surface-variant font-literata">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-primary" />
                <span>Every admin API call is authorized server-side.</span>
              </div>
              <div className="flex items-center gap-2">
                <Lock className="w-3.5 h-3.5 text-primary" />
                <span>Session is tab-scoped and cleared on close.</span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
