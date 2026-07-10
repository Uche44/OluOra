"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

// Map each nav link to the section ID it corresponds to.
// "Home" has no hash — it's active when no other section is intersecting.
const navLinks = [
  { label: "Home", href: "/", sectionId: null },
  { label: "About", href: "#about", sectionId: "about" },
  {
    label: "What OluOra Does",
    href: "#what-oluora-does",
    sectionId: "what-oluora-does",
  },
  { label: "Early Access", href: "#waitlist", sectionId: "waitlist" },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  // Track which section is currently in view; null = top of page (Home active)
  const [activeSection, setActiveSection] = useState<string | null>(null);

  // Scroll-aware navbar background
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

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
          {/* these two  buttons should only appear if there's an authenticated user. keep commented for now */}
          {/* <button
            aria-label="Notifications"
            className="p-2 rounded-full text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
          >
            <Bell className="w-5 h-5" />
          </button>
          <button
            aria-label="Account"
            className="p-2 rounded-full text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
          >
            <User className="w-5 h-5" />
          </button> */}
          <Link
            href="#waitlist"
            id="nav-get-started"
            className="inline-flex items-center gap-2 bg-primary text-on-primary font-literata text-sm font-medium px-5 py-2.5 rounded-full hover:bg-primary-container transition-all duration-200 shadow-sm hover:shadow-md"
          >
            Join Waitlist
          </Link>
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
            <Link
              href="#waitlist"
              onClick={() => setMobileOpen(false)}
              className="flex justify-center items-center bg-primary text-on-primary font-literata text-sm font-medium px-5 py-3 rounded-full hover:bg-primary-container transition-colors"
            >
              Join Waitlist
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
