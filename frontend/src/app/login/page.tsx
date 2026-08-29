"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Shield,
  Database,
  Sparkles,
  AlertCircle,
} from "lucide-react";

// Colorful official brand logo SVGs to replace missing lucide-react exports
const GoogleLogo = () => (
  <svg
    className="w-5 h-5 flex-shrink-0"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      fill="#4285F4"
    />
    <path
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      fill="#34A853"
    />
    <path
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
      fill="#FBBC05"
    />
    <path
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
      fill="#EA4335"
    />
  </svg>
);

const YoutubeLogo = ({ className = "w-8 h-8" }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M23.498 6.163a3.003 3.003 0 0 0-2.11-2.107C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.388.511a3.002 3.002 0 0 0-2.11 2.107C0 8.053 0 12 0 12s0 3.947.502 5.837a3.003 3.003 0 0 0 2.11 2.107c1.883.511 9.388.511 9.388.511s7.505 0 9.388-.511a3.002 3.002 0 0 0 2.11-2.107C24 15.947 24 12 24 12s0-3.947-.502-5.837z"
      fill="#FF0000"
    />
    <path
      d="M9.545 15.568V8.432L15.818 12l-6.273 3.568z"
      fill="#FFFFFF"
    />
  </svg>
);

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/v1/auth/google/url`);

      if (!res.ok) {
        throw new Error("Could not fetch Google login URL from backend");
      }

      const data = await res.json();
      if (data.url) {
        // Persist the signed OAuth state token so the callback page can echo it
        // back and prove this login flow was initiated from this browser (CSRF guard).
        if (data.state) {
          sessionStorage.setItem("google_oauth_state", data.state);
        }
        window.location.href = data.url;
      } else {
        throw new Error("No URL returned from backend auth service");
      }
    } catch (err: any) {
      setError(
        err.message ||
          "Failed to connect to authentication server. Please verify backend is running.",
      );
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center px-4 overflow-hidden bg-[radial-gradient(ellipse_at_top_right,_var(--color-primary-container),_transparent_60%)] bg-surface">
      {/* Decorative Blur Spheres */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 rounded-full bg-primary/5 blur-3xl" />
      <div className="absolute bottom-10 right-0 w-80 h-80 rounded-full bg-secondary-container/10 blur-3xl" />

      <div className="w-full max-w-[1040px] grid md:grid-cols-2 gap-8 items-center relative z-10 py-12">
        {/* Left Column: Platform Branding / Teaser */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="flex flex-col gap-6 text-left max-w-md"
        >
          <Link
            href="/"
            className="inline-flex items-center gap-2 group mb-4"
          >
            <Image
              src="/icons/logo.png"
              alt="OluOra logo"
              width={48}
              height={48}
              className="w-8 h-8 object-contain transition-transform group-hover:scale-105"
            />
            <span className="font-playfair text-xl font-bold text-primary tracking-tight">
              OluOra
            </span>
          </Link>

          <h1 className="font-playfair text-4xl font-extrabold text-primary leading-tight">
            Audience Intelligence for Creators
          </h1>

          <p className="text-on-surface-variant text-base leading-relaxed font-literata">
            OluOra syncs your video catalog and comment stream directly from
            YouTube, clustering viewer feedback to extract real, actionable
            ideas.
          </p>

          <div className="flex flex-col gap-4 mt-4 font-literata">
            <div className="flex gap-3 items-start">
              <div className="p-2 rounded-lg bg-primary-container/20 text-primary mt-1">
                <Sparkles className="w-5 h-5 text-primary-container" />
              </div>
              <div>
                <h4 className="font-semibold text-primary text-sm">
                  Semantic Topic Clustering
                </h4>
                <p className="text-xs text-on-surface-variant">
                  Find patterns in thousands of comments instantly.
                </p>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <div className="p-2 rounded-lg bg-primary-container/20 text-primary mt-1">
                <Database className="w-5 h-5 text-primary-container" />
              </div>
              <div>
                <h4 className="font-semibold text-primary text-sm">
                  Direct YouTube Sync
                </h4>
                <p className="text-xs text-on-surface-variant">
                  Fetch and save video assets securely with OAuth credentials.
                </p>
              </div>
            </div>

            <div className="flex gap-3 items-start">
              <div className="p-2 rounded-lg bg-primary-container/20 text-primary mt-1">
                <Shield className="w-5 h-5 text-primary-container" />
              </div>
              <div>
                <h4 className="font-semibold text-primary text-sm">
                  Protected Workspaces
                </h4>
                <p className="text-xs text-on-surface-variant">
                  Secure session layers isolate and protect your data.
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Right Column: Glassmorphic Login Card */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          <div className="w-full bg-white/70 backdrop-blur-lg border border-outline-variant/30 rounded-3xl p-8 md:p-10 shadow-2xl relative">
            <div className="flex flex-col items-center gap-6">
              <div className="w-16 h-16 rounded-2xl bg-primary-container/10 flex items-center justify-center">
                <YoutubeLogo className="w-8 h-8" />
              </div>

              <div className="text-center">
                <h2 className="font-playfair text-2xl font-bold text-primary">
                  Creator Sign In
                </h2>
                <p className="text-sm text-on-surface-variant font-literata mt-1">
                  Authorize read-only access to YouTube channels and video
                  comments
                </p>
              </div>

              {error && (
                <div className="w-full flex gap-3 p-4 bg-error-container/30 border border-error-container text-error rounded-2xl font-literata text-xs items-start">
                  <AlertCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <button
                onClick={handleGoogleLogin}
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

              <div className="w-full flex items-center justify-center gap-2 mt-4 text-[10px] text-on-surface-variant font-literata border-t border-outline-variant/20 pt-6">
                <Shield className="w-3.5 h-3.5" />
                <span>
                  OluOra processes credentials securely. We never modify your
                  videos.
                </span>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
