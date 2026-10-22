"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  LayoutGrid,
  TrendingUp,
  Users,
  ClipboardList,
  Activity,
  Server,
  MessageSquare,
  Mail,
  LogOut,
  Menu,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { getStoredUser, hasSession, logout, type AdminSessionUser } from "@/lib/api";

const navItems = [
  { label: "Overview", href: "/", icon: LayoutGrid },
  { label: "Funnel", href: "/funnel", icon: TrendingUp },
  { label: "Users", href: "/users", icon: Users },
  { label: "Waitlist", href: "/waitlist", icon: ClipboardList },
  { label: "Feedback", href: "/feedback", icon: MessageSquare },
  { label: "Email", href: "/email", icon: Mail },
  { label: "API Usage", href: "/usage", icon: Activity },
  { label: "Job Health", href: "/jobs", icon: Server },
];

export default function AdminDashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<AdminSessionUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    // Cosmetic guard only — the backend rejects any non-admin token regardless.
    if (!hasSession()) {
      router.replace("/login");
      return;
    }
    setUser(getStoredUser());
    setLoading(false);
  }, [router]);

  const handleSignOut = async () => {
    await logout();
    router.replace("/login");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 border-4 border-primary/10 border-t-primary rounded-full animate-spin" />
          <span className="font-literata text-sm text-on-surface-variant">
            Loading admin console...
          </span>
        </div>
      </div>
    );
  }

  const SidebarContent = () => (
    <div className="h-full flex flex-col justify-between py-6 px-4">
      <div className="flex flex-col gap-8">
        <Link href="/" className="flex items-center gap-2.5 px-3 select-none group">
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
              Admin Console
            </span>
          </div>
        </Link>

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
                <Icon className={cn("w-4 h-4", isActive ? "text-primary" : "text-on-surface-variant")} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex flex-col gap-1 border-t border-outline-variant/20 pt-4">
        <button
          onClick={() => {
            setMobileOpen(false);
            handleSignOut();
          }}
          className="flex items-center gap-3 px-4 py-2.5 rounded-xl font-literata text-sm text-on-surface-variant hover:text-error hover:bg-error-container/10 transition-colors w-full text-left cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign out</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex bg-surface text-on-surface overflow-x-hidden">
      <aside className="hidden md:block w-64 border-r border-outline-variant/20 bg-surface-container-lowest flex-shrink-0 h-screen sticky top-0">
        <SidebarContent />
      </aside>

      <div className="flex-1 flex flex-col min-h-screen relative overflow-y-auto">
        <header className="h-16 border-b border-outline-variant/10 bg-surface/80 backdrop-blur-md sticky top-0 z-40 px-6 flex items-center justify-between">
          <div className="flex items-center gap-4 flex-1">
            <button
              onClick={() => setMobileOpen(true)}
              className="md:hidden p-2 rounded-lg text-on-surface-variant hover:bg-surface-container transition-colors"
              aria-label="Open sidebar"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <span className="ai-badge">Admin</span>
              <span className="hidden sm:inline font-literata text-xs text-on-surface-variant">
                Internal metrics — not customer-facing
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex flex-col text-right">
              <span className="font-literata text-xs font-semibold text-primary">
                {user?.full_name || "Admin"}
              </span>
              <span className="text-[10px] text-on-surface-variant font-medium">
                {user?.email}
              </span>
            </div>
            {user?.profile_picture ? (
              <Image
                src={user.profile_picture}
                alt="Admin"
                width={36}
                height={36}
                className="rounded-full border border-primary/20 object-cover w-9 h-9"
              />
            ) : (
              <div className="w-9 h-9 rounded-full bg-surface-container-high flex items-center justify-center border border-outline-variant/30 font-literata text-xs font-semibold text-on-surface-variant">
                {(user?.email || "A").charAt(0).toUpperCase()}
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 p-6 md:p-8 max-w-[1200px] w-full mx-auto">
          {children}
        </main>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
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
    </div>
  );
}
