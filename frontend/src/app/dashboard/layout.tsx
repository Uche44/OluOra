"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  LayoutGrid,
  Film,
  Sparkles,
  Calendar,
  Settings,
  Crown,
  HelpCircle,
  LogOut,
  Bell,
  Search,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { logout } from "@/lib/api";
import FeedbackProvider from "@/components/feedback/FeedbackProvider";
import FeedbackLauncher from "@/components/feedback/FeedbackLauncher";
import FeedbackSidebarButton from "@/components/feedback/FeedbackSidebarButton";

interface UserSession {
  email: string;
  full_name?: string;
  profile_picture?: string;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Authenticate creator on mount (client-side route guard)
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const storedUser = localStorage.getItem("user");
    if (!token) {
      router.push("/login");
    } else {
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch (e) {
          console.error(e);
        }
      }
      setLoading(false);
    }
  }, [router]);

  const handleSignOut = async () => {
    // Revoke the refresh token server-side, then clear local auth state.
    await logout();
    router.push("/login");
  };

  const navItems = [
    { label: "Dashboard", href: "/dashboard", icon: LayoutGrid },
    { label: "Videos", href: "/dashboard/videos", icon: Film },
    { label: "Opportunities", href: "/dashboard/opportunities", icon: Sparkles },
    { label: "Calendar", href: "/dashboard/calendar", icon: Calendar },
    { label: "Settings", href: "/dashboard/settings", icon: Settings },
  ];

  const searchPlaceholder = pathname.endsWith("/videos")
    ? "Search your video library..."
    : "Search videos or opportunities...";

  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 border-4 border-primary/10 border-t-primary rounded-full animate-spin" />
          <span className="font-literata text-sm text-on-surface-variant">
            Loading workspace...
          </span>
        </div>
      </div>
    );
  }

  const SidebarContent = () => (
    <div className="h-full flex flex-col justify-between py-6 px-4">
      <div className="flex flex-col gap-8">
        {/* Brand Header */}
        <Link
          href="/dashboard"
          className="flex items-center gap-2.5 px-3 select-none group"
        >
          <Image
            src="/icons/logo.png"
            alt="OluOra Logo"
            width={40}
            height={40}
            className="w-8 h-8 object-contain flex-shrink-0 transition-transform group-hover:scale-105"
          />
          <div className="flex flex-col">
            <span className="font-playfair text-xl font-bold text-primary leading-tight">
              OluOra
            </span>
            <span className="text-[9px] text-on-surface-variant font-medium tracking-widest uppercase mt-0.5">
              Creator Intelligence
            </span>
          </div>
        </Link>

        {/* Navigation list */}
        <nav className="flex flex-col gap-1.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.label}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl font-literata text-sm font-medium transition-all duration-150",
                  isActive
                    ? "bg-surface-container text-primary font-semibold shadow-sm"
                    : "text-on-surface-variant hover:text-primary hover:bg-surface-container/50",
                )}
              >
                <Icon
                  className={cn(
                    "w-4 h-4",
                    isActive ? "text-primary" : "text-on-surface-variant",
                  )}
                />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex flex-col gap-4 mt-auto">
        {/* Upgrade Card */}
        <div className="px-1">
          <button className="w-full bg-primary hover:bg-primary-container text-on-primary font-literata text-xs font-semibold py-3 px-4 rounded-xl transition-all duration-150 flex items-center justify-center gap-2 shadow-sm cursor-pointer">
            <Crown className="w-4 h-4 text-secondary-container" />
            <span>Upgrade to Pro</span>
          </button>
        </div>

        {/* Bottom utility links */}
        <div className="flex flex-col gap-1 border-t border-outline-variant/20 pt-4">
          <Link
            href="/dashboard/help"
            onClick={() => setMobileOpen(false)}
            className="flex items-center gap-3 px-4 py-2.5 rounded-xl font-literata text-sm text-on-surface-variant hover:text-primary hover:bg-surface-container/50 transition-colors"
          >
            <HelpCircle className="w-4 h-4" />
            <span>Help</span>
          </Link>
          <FeedbackSidebarButton onBeforeOpen={() => setMobileOpen(false)} />
          <button
            onClick={() => {
              setMobileOpen(false);
              handleSignOut();
            }}
            className="flex items-center gap-3 px-4 py-2.5 rounded-xl font-literata text-sm text-on-surface-variant hover:text-error hover:bg-error-container/10 transition-colors w-full text-left cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <FeedbackProvider>
      <div className="min-h-screen flex bg-surface text-on-surface overflow-x-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden md:block w-64 border-r border-outline-variant/20 bg-surface-container-lowest flex-shrink-0 h-screen sticky top-0">
        <SidebarContent />
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col min-h-screen relative overflow-y-auto">
        {/* Top Header Bar */}
        <header className="h-16 border-b border-outline-variant/10 bg-surface/80 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
          <div className="flex items-center gap-4 flex-1">
            {/* Mobile menu trigger */}
            <button
              onClick={() => setMobileOpen(true)}
              className="md:hidden p-2 rounded-lg text-on-surface-variant hover:bg-surface-container transition-colors"
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>

            {/* Search Input Bar */}
            <div className="relative max-w-md w-full hidden sm:block">
              <Search className="w-4 h-4 text-on-surface-variant/60 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder={searchPlaceholder}
                className="w-full bg-surface-container-low border border-outline-variant/20 rounded-full py-2 pl-10 pr-4 font-literata text-sm focus:outline-none focus:border-primary/40 focus:bg-surface-container-lowest transition-colors"
              />
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              aria-label="Notifications"
              className="p-2 rounded-full text-on-surface-variant hover:text-primary hover:bg-surface-container transition-colors relative"
            >
              <Bell className="w-4.5 h-4.5" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-secondary" />
            </button>

            {/* User Session Profile Picture */}
            <div className="flex items-center gap-3 border-l border-outline-variant/20 pl-4">
              <div className="flex flex-col text-right hidden sm:flex">
                <span className="font-literata text-xs font-semibold text-primary">
                  {user?.full_name || "Alex Rivera"}
                </span>
                <span className="text-[9px] text-on-surface-variant font-medium">
                  Lead Creator
                </span>
              </div>
              {user?.profile_picture ? (
                <Image
                  src={user.profile_picture}
                  alt="Profile picture"
                  width={36}
                  height={36}
                  className="rounded-full border border-primary/20 object-cover w-9 h-9"
                />
              ) : (
                <div className="w-9 h-9 rounded-full bg-surface-container-high flex items-center justify-center border border-outline-variant/30">
                  <UserIcon className="w-4 h-4 text-on-surface-variant" />
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Content Wrapper */}
        <main className="flex-1 p-6 md:p-8 max-w-[1200px] w-full mx-auto">
          {children}
        </main>
      </div>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          {/* Backdrop click closer */}
          <div
            className="fixed inset-0 bg-primary/20 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative w-64 bg-surface-container-lowest h-full shadow-2xl flex flex-col z-50">
            <button
              onClick={() => setMobileOpen(false)}
              className="absolute top-4 right-4 p-2 rounded-lg text-on-surface-variant hover:bg-surface-container"
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
            <SidebarContent />
          </aside>
        </div>
      )}

      <FeedbackLauncher />
      </div>
    </FeedbackProvider>
  );
}

// Simple fallback user icon
function UserIcon({ className = "" }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
      />
    </svg>
  );
}
