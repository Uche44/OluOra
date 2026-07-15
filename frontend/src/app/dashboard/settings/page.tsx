"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { authedFetch } from "@/lib/api";
import { 
  User, 
  Globe, 
  ShieldAlert, 
  Key, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle,
  Eye,
  EyeOff,
  Video,
  UserCheck
} from "lucide-react";

interface ConnectedChannel {
  id: string;
  youtube_channel_id: string;
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
  created_at: string;
  connections: ConnectedAccount[];
  channels: ConnectedChannel[];
}

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Profile update form state
  const [fullName, setFullName] = useState("");
  const [updating, setUpdating] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);

  // Disconnection state
  const [disconnecting, setDisconnecting] = useState(false);
  const [showConfirmDisconnect, setShowConfirmDisconnect] = useState(false);

  // Debug session state
  const [showToken, setShowToken] = useState(false);
  const [sessionToken, setSessionToken] = useState("");

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
      
      // Load current session token for debug
      const token = localStorage.getItem("access_token") || "";
      setSessionToken(token);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred loading your settings.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

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

  const handleDisconnect = async () => {
    setDisconnecting(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await authedFetch(`${apiUrl}/api/v1/users/disconnect/google`, {
        method: "POST"
      });
      if (!res.ok) {
        throw new Error("Failed to disconnect Google connection.");
      }
      
      // Reload profile connections
      await fetchProfile();
      setShowConfirmDisconnect(false);
    } catch (err: any) {
      console.error(err);
      alert(err.message || "Failed to disconnect channel.");
    } finally {
      setDisconnecting(false);
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

  const isConnected = (profile?.connections.length ?? 0) > 0;
  const channel = profile?.channels[0];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="flex flex-col gap-8 text-on-surface"
    >
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="font-playfair text-3xl font-bold text-primary">Creator Settings</h1>
        <p className="text-sm font-literata text-on-surface-variant">
          Manage your personal details, connected channels, and developer credentials.
        </p>
      </div>

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

          {isConnected && channel ? (
            <div className="flex flex-col gap-5">
              <div className="flex items-start gap-4 bg-surface-container-lowest p-5 rounded-2xl border border-outline-variant/10">
                {channel.thumbnail_url ? (
                  <img
                    src={channel.thumbnail_url}
                    alt={channel.title}
                    className="w-14 h-14 rounded-full object-cover border border-outline-variant/10"
                  />
                ) : (
                  <div className="w-14 h-14 rounded-full bg-[#0b3d2e]/10 flex items-center justify-center">
                    <Video className="w-7 h-7 text-[#0b3d2e]" />
                  </div>
                )}
                
                <div className="flex flex-col flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h3 className="font-playfair text-base font-bold text-primary truncate">{channel.title}</h3>
                    <span className="text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full border bg-emerald-100/50 text-emerald-950 border-emerald-200">
                      YouTube Linked
                    </span>
                  </div>
                  
                  <p className="text-xs text-on-surface-variant font-literata truncate mt-1">
                    {channel.description || "No channel description available."}
                  </p>
                  
                  <div className="flex gap-4 mt-3 text-[11px] font-literata text-on-surface-variant font-medium">
                    <div>
                      Subscriber Count: <span className="font-bold text-primary">{formatNumber(channel.subscriber_count)}</span>
                    </div>
                    <div className="border-l border-outline-variant/30 pl-4">
                      Total Uploads: <span className="font-bold text-primary">{channel.video_count}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Google token expiry info */}
              <div className="flex flex-col gap-1 text-[11px] font-literata text-on-surface-variant bg-surface-container/30 p-4 rounded-xl border border-outline-variant/5">
                <span className="font-semibold text-primary">OAuth Connection Information:</span>
                <div>Provider: Google OAuth 2.0 API</div>
                <div>Expires: {new Date(profile!.connections[0].token_expires_at).toLocaleString()}</div>
              </div>

              <div className="border-t border-outline-variant/10 pt-4 mt-2">
                {!showConfirmDisconnect ? (
                  <button
                    onClick={() => setShowConfirmDisconnect(true)}
                    className="px-5 py-2.5 rounded-full border border-red-200 text-red-700 text-xs font-semibold font-literata hover:bg-red-50 transition cursor-pointer"
                  >
                    Disconnect Google Account
                  </button>
                ) : (
                  <div className="bg-red-50/50 border border-red-100 rounded-2xl p-4 flex flex-col gap-3">
                    <div className="flex gap-2 text-red-900 text-xs font-literata">
                      <AlertTriangle className="w-4 h-4 text-red-700 flex-shrink-0" />
                      <p>
                        Are you sure you want to disconnect? This deletes all synced YouTube channel metadata, videos, comments, and analyses immediately.
                      </p>
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={handleDisconnect}
                        disabled={disconnecting}
                        className="px-4 py-2 rounded-full bg-red-700 text-white text-xs font-semibold font-literata hover:bg-red-800 transition cursor-pointer"
                      >
                        {disconnecting ? "Disconnecting..." : "Yes, Disconnect"}
                      </button>
                      <button
                        onClick={() => setShowConfirmDisconnect(false)}
                        className="px-4 py-2 rounded-full border border-outline-variant/20 text-on-surface-variant text-xs font-semibold font-literata hover:bg-surface-container transition cursor-pointer"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4 py-8 text-center">
              <div className="w-12 h-12 rounded-full bg-[#0b3d2e]/10 flex items-center justify-center">
                <Video className="w-6 h-6 text-[#0b3d2e]" />
              </div>
              <div className="flex flex-col gap-1">
                <h3 className="font-playfair text-base font-bold text-primary">No accounts connected</h3>
                <p className="text-xs text-on-surface-variant font-literata max-w-sm leading-relaxed">
                  Connect your Google account to authorize YouTube read-only access.
                </p>
              </div>
              <Link
                href="/dashboard/videos"
                className="px-6 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition shadow-sm"
              >
                Go Link YouTube Channel
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Session Security Details */}
      <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col gap-4">
        <div className="flex items-center gap-3 border-b border-outline-variant/10 pb-4">
          <Key className="w-5 h-5 text-primary" />
          <h2 className="font-playfair text-lg font-bold text-primary">Session Token &amp; Credentials</h2>
        </div>

        <div className="flex flex-col gap-3 font-literata text-xs">
          <div className="flex items-center justify-between">
            <span className="text-on-surface-variant font-medium">Internal Session Type:</span>
            <span className="font-semibold text-primary inline-flex items-center gap-1">
              <UserCheck className="w-3.5 h-3.5 text-emerald-700" />
              OluOra JWT (Bearer)
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-on-surface-variant font-medium">Session Status:</span>
            <span className="font-semibold text-emerald-700">Authenticated &amp; Active</span>
          </div>

          <div className="flex flex-col gap-1.5 mt-2 border-t border-outline-variant/10 pt-4">
            <div className="flex items-center justify-between">
              <span className="text-on-surface-variant font-semibold">Active Access Token (Decrypted Bearer):</span>
              <button
                onClick={() => setShowToken(!showToken)}
                className="flex items-center gap-1.5 text-[11px] font-semibold text-primary hover:underline cursor-pointer"
              >
                {showToken ? (
                  <>
                    <EyeOff className="w-3 h-3" /> Hide Token
                  </>
                ) : (
                  <>
                    <Eye className="w-3 h-3" /> Reveal Token
                  </>
                )}
              </button>
            </div>

            {showToken && (
              <div className="bg-surface-container p-4 rounded-xl border border-outline-variant/20 font-mono text-[10px] break-all select-all leading-normal text-on-surface-variant">
                {sessionToken}
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
