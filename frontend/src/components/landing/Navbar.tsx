"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, User, LogOut, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

// Map each nav link to the section ID it corresponds to.
// "Home" has no hash — it's active when no other section is intersecting.
const navLinks = [
  { label: "Home", href: "/", sectionId: null },
  { label: "About", href: "#about", sectionId: "about" },
  { label: "Solution", href: "#solution", sectionId: "solution" },
  { label: "Early Access", href: "#waitlist", sectionId: "waitlist" },
];

interface UserSession {
  email: string;
  full_name?: string;
  profile_picture?: string;
}

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  // Track which section is currently in view; null = top of page (Home active)
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [user, setUser] = useState<UserSession | null>(null);

  // Scroll-aware navbar background
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  // Fetch logged in session from localStorage safely (client-only)
  useEffect(() => {
    try {
      const stored = localStorage.getItem("user");
      if (stored) {
        setUser(JSON.parse(stored));
      }
    } catch (e) {
      console.error("Failed to parse user details from local storage", e);
    }
  }, []);

  // Sign out helper
  const handleSignOut = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    setUser(null);
    window.location.reload();
  };

  // IntersectionObserver — watches all hash-linked sections
  useEffect(() => {
    const sectionIds = navLinks
      .map((l) => l.sectionId)
      .filter(Boolean) as string[];

    const observers: IntersectionObserver[] = [];

    sectionIds.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;

      const obs = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setActiveSection(id);
          } else {
            // If this section is leaving and it was the active one, fall back
            setActiveSection((prev) => (prev === id ? null : prev));
          }
        },
        {
          // Trigger when the section occupies ≥ 30% of the viewport
          threshold: 0.3,
          rootMargin: "-64px 0px 0px 0px", // offset for fixed navbar height
        },
      );

      obs.observe(el);
      observers.push(obs);
    });

    return () => observers.forEach((obs) => obs.disconnect());
  }, []);

  // Determine if a given nav link is active
  const isActive = (link: (typeof navLinks)[number]) => {
    if (link.sectionId === null) {
      // "Home" is active when no section is in view
      return activeSection === null;
    }
    return activeSection === link.sectionId;
  };

  return (
    <header
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        scrolled
          ? "bg-surface/95 backdrop-blur-md border-b border-outline-variant/30 shadow-sm"
          : "bg-transparent",
      )}
    >
      <nav className="max-w-[1280px] mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 select-none group"
        >
          <Image
            src="/icons/logo.png"
            alt="OluOra logo"
            width={48}
            height={48}
            className="w-7 h-7 object-contain flex-shrink-0"
          />
          <span className="font-playfair text-[1.4rem] font-bold text-primary tracking-tight leading-none">
            OluOra
          </span>
        </Link>

        {/* Desktop nav links */}
        <ul className="hidden md:flex items-center gap-1">
          {navLinks.map((link) => (
            <li key={link.label}>
              <Link
                href={link.href}
                className={cn(
                  "font-literata text-sm font-medium px-4 py-2 rounded-full transition-colors duration-150",
                  isActive(link)
                    ? "text-primary border-b-2 border-primary"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container",
                )}
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Desktop right actions */}
        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <>
              <Link
                href="/dashboard"
                className="font-literata text-sm font-medium px-4 py-2.5 hover:bg-surface-container rounded-full text-primary transition-colors"
              >
                Dashboard
              </Link>
              
              {user.profile_picture ? (
                <Image
                  src={user.profile_picture}
                  alt={user.full_name || "Profile avatar"}
                  width={32}
                  height={32}
                  className="rounded-full border border-primary/20 object-cover w-8 h-8"
                />
              ) : (
                <div className="p-2 bg-surface-container-high rounded-full">
                  <User className="w-4 h-4 text-on-surface-variant" />
                </div>
              )}
              
              <button
                onClick={handleSignOut}
                aria-label="Sign Out"
                className="p-2 rounded-full text-on-surface-variant hover:text-error hover:bg-error-container/15 transition-colors cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="font-literata text-sm font-medium px-4 py-2 rounded-full text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="#waitlist"
                id="nav-get-started"
                className="inline-flex items-center gap-2 bg-primary text-on-primary font-literata text-sm font-medium px-5 py-2.5 rounded-full hover:bg-primary-container transition-all duration-200 shadow-sm hover:shadow-md"
              >
                Get Started
              </Link>
            </>
          )}
        </div>

        {/* Mobile menu button */}
        <button
          className="md:hidden p-2 rounded-full text-on-surface-variant hover:bg-surface-container transition-colors"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? (
            <X className="w-5 h-5" />
          ) : (
            <Menu className="w-5 h-5" />
          )}
        </button>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
            className="md:hidden bg-surface/98 backdrop-blur-md border-b border-outline-variant/30 px-6 pb-5 pt-2"
          >
            <ul className="flex flex-col gap-1 mb-4">
              {navLinks.map((link) => (
                <li key={link.label}>
                  <Link
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      "block font-literata text-sm font-medium px-3 py-2.5 rounded-lg transition-colors",
                      isActive(link)
                        ? "text-primary bg-surface-container"
                        : "text-on-surface-variant hover:text-primary hover:bg-surface-container",
                    )}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
            
            {user ? (
              <div className="flex flex-col gap-3 pt-4 border-t border-outline-variant/20">
                <div className="flex items-center gap-3 px-3">
                  {user.profile_picture && (
                    <Image
                      src={user.profile_picture}
                      alt="User avatar"
                      width={36}
                      height={36}
                      className="rounded-full border border-primary/20 object-cover w-9 h-9"
                    />
                  )}
                  <div className="flex flex-col">
                    <span className="font-literata text-sm font-semibold text-primary">{user.full_name}</span>
                    <span className="font-literata text-xs text-on-surface-variant">{user.email}</span>
                  </div>
                </div>
                <Link
                  href="/dashboard"
                  onClick={() => setMobileOpen(false)}
                  className="flex justify-center items-center bg-surface-container text-primary font-literata text-sm font-medium px-5 py-2.5 rounded-full border border-primary/10 transition-colors"
                >
                  Go to Dashboard
                </Link>
                <button
                  onClick={() => {
                    setMobileOpen(false);
                    handleSignOut();
                  }}
                  className="flex justify-center items-center bg-error-container/10 text-error font-literata text-sm font-medium px-5 py-2.5 rounded-full hover:bg-error-container/20 transition-colors cursor-pointer"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-2 pt-2 border-t border-outline-variant/20">
                <Link
                  href="/login"
                  onClick={() => setMobileOpen(false)}
                  className="flex justify-center items-center border border-outline-variant/30 text-on-surface-variant font-literata text-sm font-medium px-5 py-2.5 rounded-full hover:bg-surface-container transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="#waitlist"
                  onClick={() => setMobileOpen(false)}
                  className="flex justify-center items-center bg-primary text-on-primary font-literata text-sm font-medium px-5 py-2.5 rounded-full hover:bg-primary-container transition-colors"
                >
                  Get Started
                </Link>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}

