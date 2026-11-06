"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { authedFetch, startConnectFlow, type DataProvider } from "@/lib/api";
import {
  User,
  Globe,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Video,
  Music2,
  Palette,
} from "lucide-react";

interface ConnectedChannel {
  id: string;
  platform: string;
  external_id: string;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  subscriber_count: number;
  video_count: number;
}

interface ConnectedAccount {
  provider: string;
  provider_user_id: string;
  token_expires_at: string;
}

interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  profile_picture: string | null;
  is_active: boolean;
  auth_provider: string;
  can_connect_tiktok: boolean;
  created_at: string;
  connections: ConnectedAccount[];
  channels: ConnectedChannel[];
}

const PROVIDERS: {
  id: DataProvider;
  label: string;
  badgeClass: string;
  description: string;
}[] = [
  {
    id: "youtube",
    label: "YouTube",
    badgeClass: "bg-emerald-100/50 text-emerald-950 border-emerald-200",
    description: "Sync your channel, videos and comments for full AI analysis.",
  },
  {
    id: "tiktok",
    label: "TikTok",
    badgeClass: "bg-slate-900/5 text-slate-900 border-slate-300",
    description: "Sync your public video catalog and comments for AI analysis.",
  },
];

interface StyleProfile {
  tone: string;
  language: string;
  audience_description: string;
  technical_depth: string;
  preferred_structures: string[];
  avoid: string[];
  posting_cadence: number;
  preferred_formats: string[];
  preferred_platforms: string[];
  reference_notes: string;
  updated_at: string | null;
}

const DEFAULT_STYLE: StyleProfile = {
  tone: "",
  language: "",
  audience_description: "",
  technical_depth: "intermediate",
  preferred_structures: [],
  avoid: [],
  posting_cadence: 3,
  preferred_formats: [],
  preferred_platforms: ["youtube"],
  reference_notes: "",
  updated_at: null,
};

const TECHNICAL_DEPTHS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

const STYLE_STRUCTURES = [
  { value: "hook_first", label: "Hook first" },
  { value: "story", label: "Story" },
  { value: "tutorial", label: "Tutorial" },
  { value: "listicle", label: "Listicle" },
  { value: "case_study", label: "Case study" },
  { value: "problem_solution", label: "Problem → solution" },
  { value: "comparison", label: "Comparison" },
];

const STYLE_FORMATS = ["tutorial", "explainer", "comparison", "faq", "demo", "opinion"];
const STYLE_PLATFORMS = [{ value: "youtube", label: "YouTube" }];


export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);

  // Profile update form state
  const [fullName, setFullName] = useState("");
  const [updating, setUpdating] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);

  // Connection state
  const [connecting, setConnecting] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [confirmDisconnect, setConfirmDisconnect] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Creator style state
  const [styleForm, setStyleForm] = useState<StyleProfile>(DEFAULT_STYLE);
  const [avoidText, setAvoidText] = useState("");
  const [savingStyle, setSavingStyle] = useState(false);
  const [styleSaved, setStyleSaved] = useState(false);
  const [styleError, setStyleError] = useState<string | null>(null);

  const fetchStyle = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await authedFetch(`${apiUrl}/api/v1/content/style`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail?.message || "Failed to load style preferences.");
      }
      setStyleForm({ ...DEFAULT_STYLE, ...data });
      setAvoidText((data.avoid || []).join("\n"));
    } catch (err) {
      setStyleError(
        err instanceof Error ? err.message : "Failed to load style preferences.",
      );
    }
  };

  const fetchProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await authedFetch(`${apiUrl}/api/v1/users/me`);
      if (!res.ok) {
        throw new Error("Failed to load user profile settings.");
      }
      const data = await res.json();
      setProfile(data);
      setFullName(data.full_name || "");
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred loading your settings.");
    } finally {
      setLoading(false);
    }
  };

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    // Surface a message left by the OAuth connect callback.
    const pending = sessionStorage.getItem("connect_flash");
    if (pending) {
      sessionStorage.removeItem("connect_flash");
      setFlash(pending);
      setTimeout(() => setFlash(null), 5000);
    }
    fetchProfile();
    fetchStyle();
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setUpdating(true);
    setUpdateSuccess(false);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await authedFetch(`${apiUrl}/api/v1/users/me`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name: fullName })
      });
      if (!res.ok) {
        throw new Error("Failed to update profile details.");
      }
      const data = await res.json();
      setProfile(data);

      // Update local storage user details to keep layout synced
      localStorage.setItem("user", JSON.stringify({
        email: data.email,
        full_name: data.full_name,
        profile_picture: data.profile_picture
      }));

      setUpdateSuccess(true);
      setTimeout(() => setUpdateSuccess(false), 3000);
    } catch (err: any) {
      console.error(err);
      alert(err.message || "Failed to update profile.");
    } finally {
      setUpdating(false);
    }
  };

  const handleConnect = async (provider: DataProvider) => {
    setConnecting(provider);
    setActionError(null);
    try {
      await startConnectFlow(provider);
    } catch (err: any) {
      console.error(err);
      setActionError(err.message || `Failed to start the ${provider} connection.`);
      setConnecting(null);
    }
  };

  const handleDisconnect = async (provider: string) => {
    setDisconnecting(provider);
    setActionError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await authedFetch(`${apiUrl}/api/v1/users/disconnect/${provider}`, {
        method: "POST"
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = data?.detail;
        throw new Error(
          (typeof detail === "string" ? detail : detail?.message) ||
            `Failed to disconnect ${provider}.`
        );
      }
      setConfirmDisconnect(null);
      await fetchProfile();
    } catch (err: any) {
      console.error(err);
      setActionError(err.message || "Failed to disconnect channel.");
    } finally {
      setDisconnecting(null);
    }
  };

  const updateStyle = (field: keyof StyleProfile, value: string | number) => {
    setStyleForm((current) => ({ ...current, [field]: value }));
  };

  const toggleStyleList = (
    field: "preferred_structures" | "preferred_formats" | "preferred_platforms",
    value: string,
  ) => {
    setStyleForm((current) => {
      const values = current[field];
      return {
        ...current,
        [field]: values.includes(value)
          ? values.filter((item) => item !== value)
          : [...values, value],
      };
    });
  };

  const handleStyleSave = async (
    event?: React.FormEvent | React.MouseEvent,
  ) => {
    event?.preventDefault();
    setSavingStyle(true);
    setStyleError(null);
    setStyleSaved(false);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const payload = {
        tone: styleForm.tone,
        language: styleForm.language,
        audience_description: styleForm.audience_description,
        technical_depth: styleForm.technical_depth,
        preferred_structures: styleForm.preferred_structures,
        avoid: avoidText
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
        posting_cadence: styleForm.posting_cadence,
        preferred_formats: styleForm.preferred_formats,
        preferred_platforms: styleForm.preferred_platforms,
        reference_notes: styleForm.reference_notes,
      };
      const res = await authedFetch(`${apiUrl}/api/v1/content/style`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data?.detail;
        const detailMessage = Array.isArray(detail)
          ? detail
              .map((item: { msg?: string }) => item?.msg)
              .filter(Boolean)
              .join(", ")
          : typeof detail === "string"
            ? detail
            : detail?.message;
        throw new Error(detailMessage || "Failed to save style preferences.");
      }
      setStyleForm({ ...DEFAULT_STYLE, ...data });
      setAvoidText((data.avoid || []).join("\n"));
      setStyleSaved(true);
      setTimeout(() => setStyleSaved(false), 3000);
    } catch (err) {
      setStyleError(
        err instanceof Error ? err.message : "Failed to save style preferences.",
      );
    } finally {
      setSavingStyle(false);
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "K";
    return num.toString();
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-6 animate-pulse text-on-surface p-2">
        <div className="h-8 bg-surface-container rounded-lg w-1/4" />
        <div className="grid md:grid-cols-2 gap-8">
          <div className="h-64 bg-surface-container rounded-3xl" />
          <div className="h-64 bg-surface-container rounded-3xl" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 text-red-900 rounded-3xl flex flex-col gap-4 font-literata text-sm max-w-xl mx-auto my-12">
        <div className="flex items-center gap-2 text-red-700 font-bold">
          <AlertTriangle className="w-5 h-5" />
          <span>Error Loading Settings</span>
        </div>
        <p>{error}</p>
        <button onClick={fetchProfile} className="px-5 py-2 rounded-full bg-red-700 text-white font-semibold self-start hover:bg-red-800 transition">
          Retry
        </button>
      </div>
    );
  }

  const visibleProviders = PROVIDERS.filter(
    (p) => p.id !== "tiktok" || profile?.can_connect_tiktok === true,
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="flex flex-col gap-8 text-on-surface pb-28"
    >
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="font-playfair text-3xl font-bold text-primary">Creator Settings</h1>
        <p className="text-sm font-literata text-on-surface-variant">
          Manage your personal details and connected creator channels.
        </p>
      </div>

      <AnimatePresence>
        {flash && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl flex items-center gap-2 font-literata text-xs shadow-sm"
          >
            <CheckCircle className="w-4 h-4" />
            <span>{flash}</span>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {actionError && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-4 bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl flex items-center justify-between font-literata text-xs shadow-sm"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              <span>{actionError}</span>
            </div>
            <button onClick={() => setActionError(null)} className="font-bold p-1 cursor-pointer">
              Dismiss
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid lg:grid-cols-2 gap-8 items-start">
        {/* Profile Card */}
        <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col gap-6">
          <div className="flex items-center gap-3 border-b border-outline-variant/10 pb-4">
            <User className="w-5 h-5 text-primary" />
            <h2 className="font-playfair text-lg font-bold text-primary">Profile Information</h2>
          </div>

          <form onSubmit={handleUpdateProfile} className="flex flex-col gap-4">
            <div className="flex items-center gap-4">
              {profile?.profile_picture ? (
                <img
                  src={profile.profile_picture}
                  alt={profile.full_name || "Avatar"}
                  className="w-16 h-16 rounded-full object-cover border border-outline-variant/20"
                />
              ) : (
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center border border-outline-variant/20">
                  <User className="w-8 h-8 text-primary" />
                </div>
              )}
              <div className="flex flex-col">
                <span className="font-literata text-xs text-on-surface-variant">Account Email</span>
                <span className="font-literata text-sm font-semibold text-primary">{profile?.email}</span>
                <span className="font-literata text-[11px] text-on-surface-variant mt-1">
                  Signed in with {profile?.auth_provider === "google" ? "Google" : profile?.auth_provider}
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label className="font-literata text-xs font-semibold text-on-surface-variant">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your name"
                className="px-4 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata focus:ring-1 focus:ring-primary focus:outline-none bg-surface-container-lowest"
                required
              />
            </div>

            <div className="flex items-center justify-between gap-4 mt-2">
              <AnimatePresence>
                {updateSuccess && (
                  <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0 }}
                    className="flex items-center gap-1.5 text-xs text-emerald-700 font-semibold font-literata"
                  >
                    <CheckCircle className="w-4 h-4" />
                    <span>Profile updated!</span>
                  </motion.div>
                )}
              </AnimatePresence>

              <button
                type="submit"
                disabled={updating}
                className="px-6 py-2 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition-all shadow-sm ml-auto disabled:opacity-50 cursor-pointer"
              >
                {updating ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </form>
        </div>

        {/* Connections Card */}
        <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col gap-6">
          <div className="flex items-center gap-3 border-b border-outline-variant/10 pb-4">
            <Globe className="w-5 h-5 text-primary" />
            <h2 className="font-playfair text-lg font-bold text-primary">Linked Creator Channels</h2>
          </div>

          <div className="flex flex-col gap-5">
            {visibleProviders.map((provider) => {
              const account = profile?.connections.find((c) => c.provider === provider.id);
              const channel = profile?.channels.find((c) => c.platform === provider.id);
              const isConfirming = confirmDisconnect === provider.id;

              return (
                <div
                  key={provider.id}
                  className="flex flex-col gap-4 bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/10"
                >
                  <div className="flex items-start gap-4">
                    {channel?.thumbnail_url ? (
                      <img
                        src={channel.thumbnail_url}
                        alt={channel.title}
                        className="w-14 h-14 rounded-full object-cover border border-outline-variant/10"
                      />
                    ) : (
                      <div className="w-14 h-14 rounded-full bg-[#0b3d2e]/10 flex items-center justify-center">
                        {provider.id === "youtube" ? (
                          <Video className="w-7 h-7 text-[#0b3d2e]" />
                        ) : (
                          <Music2 className="w-7 h-7 text-[#0b3d2e]" />
                        )}
                      </div>
                    )}

                    <div className="flex flex-col flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-playfair text-base font-bold text-primary truncate">
                          {channel?.title || `Connect ${provider.label}`}
                        </h3>
                        <span className={`text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full border ${provider.badgeClass}`}>
                          {account ? `${provider.label} Linked` : "Not Linked"}
                        </span>
                      </div>

                      <p className="text-xs text-on-surface-variant font-literata truncate mt-1">
                        {channel?.description || provider.description}
                      </p>

                      {channel && (
                        <div className="flex gap-4 mt-3 text-[11px] font-literata text-on-surface-variant font-medium">
                          <div>
                            Followers:{" "}
                            <span className="font-bold text-primary">
                              {formatNumber(channel.subscriber_count)}
                            </span>
                          </div>
                          <div className="border-l border-outline-variant/30 pl-4">
                            Total Uploads:{" "}
                            <span className="font-bold text-primary">{channel.video_count}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {account ? (
                    <div className="flex flex-col gap-3 border-t border-outline-variant/10 pt-4">
                      {!isConfirming ? (
                        <div className="flex flex-wrap items-center gap-3">
                          <button
                            onClick={() => handleConnect(provider.id)}
                            disabled={connecting === provider.id}
                            title="Re-run consent to refresh permissions, then re-sync"
                            className="px-5 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition cursor-pointer disabled:opacity-50 flex items-center gap-2"
                          >
                            {connecting === provider.id && (
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            )}
                            {connecting === provider.id ? "Redirecting..." : "Reconnect"}
                          </button>
                          <button
                            onClick={() => setConfirmDisconnect(provider.id)}
                            className="px-5 py-2.5 rounded-full border border-red-200 text-red-700 text-xs font-semibold font-literata hover:bg-red-50 transition cursor-pointer"
                          >
                            Disconnect {provider.label}
                          </button>
                        </div>
                      ) : (
                        <div className="bg-red-50/50 border border-red-100 rounded-2xl p-4 flex flex-col gap-3">
                          <div className="flex gap-2 text-red-900 text-xs font-literata">
                            <AlertTriangle className="w-4 h-4 text-red-700 flex-shrink-0" />
                            <p>
                              Disconnecting removes all synced {provider.label} channels, videos,
                              comments, and analyses. This cannot be undone.
                            </p>
                          </div>
                          <div className="flex gap-3">
                            <button
                              onClick={() => handleDisconnect(provider.id)}
                              disabled={disconnecting === provider.id}
                              className="px-4 py-2 rounded-full bg-red-700 text-white text-xs font-semibold font-literata hover:bg-red-800 transition cursor-pointer disabled:opacity-50"
                            >
                              {disconnecting === provider.id ? "Disconnecting..." : "Yes, Disconnect"}
                            </button>
                            <button
                              onClick={() => setConfirmDisconnect(null)}
                              className="px-4 py-2 rounded-full border border-outline-variant/20 text-on-surface-variant text-xs font-semibold font-literata hover:bg-surface-container transition cursor-pointer"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="border-t border-outline-variant/10 pt-4">
                      <button
                        onClick={() => handleConnect(provider.id)}
                        disabled={connecting === provider.id}
                        className="px-6 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition shadow-sm flex items-center gap-2 disabled:opacity-50 cursor-pointer"
                      >
                        {connecting === provider.id && (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        )}
                        {connecting === provider.id ? "Redirecting..." : `Connect ${provider.label}`}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Creator Style */}
      <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col gap-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-outline-variant/10 pb-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#0b3d2e]/10 flex items-center justify-center flex-shrink-0">
              <Palette className="w-5 h-5 text-primary" />
            </div>
            <div className="flex flex-col">
              <h2 className="font-playfair text-lg font-bold text-primary">
                Creator Style
              </h2>
              <p className="text-xs font-literata text-on-surface-variant mt-0.5">
                Manual preferences used when generating scripts and briefs.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <AnimatePresence>
              {styleSaved && (
                <motion.span
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-1.5 text-xs text-emerald-700 font-semibold font-literata"
                >
                  <CheckCircle className="w-4 h-4" />
                  Style saved
                </motion.span>
              )}
            </AnimatePresence>
            <button
              type="button"
              onClick={handleStyleSave}
              disabled={savingStyle}
              className="px-5 py-2 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition shadow-sm disabled:opacity-50 cursor-pointer whitespace-nowrap"
            >
              {savingStyle ? "Saving..." : "Save style preferences"}
            </button>
          </div>
        </div>

        {styleError && (
          <div className="p-4 bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl flex items-center justify-between font-literata text-xs">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              <span>{styleError}</span>
            </div>
            <button
              onClick={() => setStyleError(null)}
              className="font-bold p-1 cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        <form onSubmit={handleStyleSave} className="grid md:grid-cols-2 gap-5">
          <label className="flex flex-col gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Tone
            </span>
            <input
              value={styleForm.tone}
              onChange={(event) => updateStyle("tone", event.target.value)}
              placeholder="e.g. warm, direct, practical"
              className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Language
            </span>
            <input
              value={styleForm.language}
              onChange={(event) => updateStyle("language", event.target.value)}
              placeholder="e.g. English"
              className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </label>

          <label className="md:col-span-2 flex flex-col gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Audience description
            </span>
            <textarea
              value={styleForm.audience_description}
              onChange={(event) =>
                updateStyle("audience_description", event.target.value)
              }
              rows={2}
              placeholder="Who the content is for, and what they already know"
              className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary resize-y"
            />
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Technical depth
            </span>
            <select
              value={styleForm.technical_depth}
              onChange={(event) =>
                updateStyle("technical_depth", event.target.value)
              }
              className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {TECHNICAL_DEPTHS.map((depth) => (
                <option key={depth.value} value={depth.value}>
                  {depth.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Posting cadence (per week)
            </span>
            <input
              type="number"
              min={1}
              max={14}
              value={styleForm.posting_cadence}
              onChange={(event) =>
                updateStyle(
                  "posting_cadence",
                  Math.max(1, Number(event.target.value) || 1),
                )
              }
              className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </label>

          <div className="md:col-span-2 flex flex-col gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Preferred structures
            </span>
            <div className="flex flex-wrap gap-2">
              {STYLE_STRUCTURES.map((structure) => {
                const active = styleForm.preferred_structures.includes(
                  structure.value,
                );
                return (
                  <button
                    key={structure.value}
                    type="button"
                    onClick={() =>
                      toggleStyleList("preferred_structures", structure.value)
                    }
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold font-literata border transition cursor-pointer ${
                      active
                        ? "bg-primary text-on-primary border-primary"
                        : "border-outline-variant/20 text-on-surface-variant hover:bg-surface-container"
                    }`}
                  >
                    {structure.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="md:col-span-2 flex flex-col gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Preferred formats
            </span>
            <div className="flex flex-wrap gap-2">
              {STYLE_FORMATS.map((format) => {
                const active = styleForm.preferred_formats.includes(format);
                return (
                  <button
                    key={format}
                    type="button"
                    onClick={() => toggleStyleList("preferred_formats", format)}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold font-literata border transition capitalize cursor-pointer ${
                      active
                        ? "bg-primary text-on-primary border-primary"
                        : "border-outline-variant/20 text-on-surface-variant hover:bg-surface-container"
                    }`}
                  >
                    {format}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="md:col-span-2 flex flex-col gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Preferred platforms
            </span>
            <div className="flex flex-wrap gap-2">
              {STYLE_PLATFORMS.map((platform) => {
                const active = styleForm.preferred_platforms.includes(
                  platform.value,
                );
                return (
                  <button
                    key={platform.value}
                    type="button"
                    onClick={() =>
                      toggleStyleList("preferred_platforms", platform.value)
                    }
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold font-literata border transition cursor-pointer ${
                      active
                        ? "bg-primary text-on-primary border-primary"
                        : "border-outline-variant/20 text-on-surface-variant hover:bg-surface-container"
                    }`}
                  >
                    {platform.label}
                  </button>
                );
              })}
            </div>
          </div>

          <label className="md:col-span-2 flex flex-col gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Things to avoid
            </span>
            <textarea
              value={avoidText}
              onChange={(event) => setAvoidText(event.target.value)}
              rows={2}
              placeholder={"One per line, e.g. jargon\nlong intros"}
              className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary resize-y"
            />
          </label>

          <label className="md:col-span-2 flex flex-col gap-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
              Additional style notes
            </span>
            <textarea
              value={styleForm.reference_notes}
              onChange={(event) =>
                updateStyle("reference_notes", event.target.value)
              }
              rows={2}
              placeholder="Anything else the scriptwriter should know"
              className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary resize-y"
            />
          </label>

          <div className="md:col-span-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-outline-variant/10 pt-4">
            <p className="text-[10px] font-literata text-on-surface-variant/70 max-w-lg">
              These are explicit preferences. Style learning from transcripts or
              reference content is not enabled yet. Changes apply the next time
              you generate a script; existing versions are kept.
            </p>
            <div className="flex items-center gap-3 self-end sm:self-auto">
              {styleSaved && (
                <span className="flex items-center gap-1 text-xs font-semibold font-literata text-emerald-700">
                  <CheckCircle className="w-4 h-4" />
                  Saved
                </span>
              )}
              {styleError && (
                <span className="max-w-[220px] text-[10px] font-literata text-amber-700">
                  {styleError}
                </span>
              )}
              <button
                type="button"
                onClick={handleStyleSave}
                disabled={savingStyle}
                className="px-6 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition shadow-sm disabled:opacity-50 cursor-pointer whitespace-nowrap"
              >
                {savingStyle
                  ? "Saving..."
                  : styleSaved
                    ? "Saved"
                    : "Save style preferences"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </motion.div>
  );
}
