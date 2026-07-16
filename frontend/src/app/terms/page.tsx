"use client";

import Link from "next/link";
import { ArrowLeft, BookOpen, AlertTriangle, ShieldCheck, Scale } from "lucide-react";

export default function TermsOfServicePage() {
  return (
    <div className="bg-zinc-950 text-zinc-100 min-h-screen font-sans selection:bg-primary/30 selection:text-white">
      {/* Header */}
      <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-zinc-400 hover:text-zinc-100 transition-colors text-sm font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Home
          </Link>
          <span className="font-semibold text-lg tracking-tight bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">
            OluOra
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-6 py-12 lg:py-16">
        <h1 className="text-3xl lg:text-4xl font-extrabold tracking-tight mb-3">
          Terms of Service
        </h1>
        <p className="text-sm text-zinc-400 mb-8">
          Last Updated: July 16, 2026
        </p>

        <div className="prose prose-invert max-w-none space-y-8 text-zinc-300 leading-relaxed">
          <section className="bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-6 lg:p-8 space-y-4">
            <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-3">
              <BookOpen className="w-5 h-5 text-teal-400" />
              1. Acceptance of Terms
            </h2>
            <p className="text-sm text-zinc-400">
              By accessing and using OluOra (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;), you agree to comply with and be bound by these Terms of Service. If you do not agree to these terms, please do not use our services.
            </p>
          </section>

          {/* Section 2 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              2. Google & YouTube Terms Integration
            </h2>
            <p>
              OluOra accesses YouTube API Services to retrieve channel metrics and comments. By using our platform, you acknowledge and agree that you are also bound by:
            </p>
            <ul className="list-disc list-inside space-y-2 text-zinc-400 text-sm pl-2">
              <li>
                <a
                  href="https://www.youtube.com/t/terms"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-teal-400 hover:underline"
                >
                  YouTube Terms of Service (ToS)
                </a>
              </li>
              <li>
                <a
                  href="https://policies.google.com/privacy"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-teal-400 hover:underline"
                >
                  Google Privacy Policy
                </a>
              </li>
            </ul>
            <p className="text-sm text-zinc-400">
              You can manage and revoke your connected Google account permissions at any time via the{" "}
              <a
                href="https://myaccount.google.com/permissions"
                target="_blank"
                rel="noopener noreferrer"
                className="text-teal-400 hover:underline"
              >
                Google Security Settings
              </a>{" "}
              page.
            </p>
          </section>

          {/* Section 3 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <Scale className="w-5 h-5 text-teal-400" />
              3. User Responsibilities & Acceptable Use
            </h2>
            <p>
              When utilizing OluOra to analyze comment feeds, you agree not to:
            </p>
            <ul className="list-disc list-inside space-y-2 text-zinc-400 text-sm pl-2">
              <li>Use the tool to spam, overload, or exhaust the global YouTube API limits.</li>
              <li>Reverse engineer or systematically scrape the platform metadata.</li>
              <li>Circumvent plan limits, quota trackers, or user restrictions set on your account.</li>
            </ul>
          </section>

          {/* Section 4 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              4. Disclaimer of Warranties & Limitation of Liability
            </h2>
            <p className="text-sm text-zinc-400">
              OluOra is provided on an &quot;AS IS&quot; and &quot;AS AVAILABLE&quot; basis. We make no representations or warranties of any kind regarding connection stability, uninterrupted YouTube API access, or AI model accuracy.
            </p>
            <p className="text-sm text-zinc-400">
              In no event shall OluOra, its founders, or affiliates be liable for any direct, indirect, incidental, or consequential damages resulting from connection failure, API key revocation, quota starvation, or account suspensions by third-party services.
            </p>
          </section>

          {/* Section 5 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100">
              5. Modification of Terms
            </h2>
            <p className="text-sm text-zinc-400">
              We reserve the right to revise or modify these terms at any time. Changes will be immediately effective upon posting. Your continued use of the platform constitutes agreement to the updated terms.
            </p>
          </section>

          {/* Section 6 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100">
              6. Contact Support
            </h2>
            <p className="text-sm text-zinc-400">
              If you have any questions regarding these Terms of Service, please contact us at <a href="mailto:perp@ijuaalkiez.resend.app" className="text-teal-400 hover:underline">contact email</a>.
            </p>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-900 bg-zinc-950 py-8 text-center text-xs text-zinc-600">
        <p>© {new Date().getFullYear()} OluOra. All rights reserved.</p>
      </footer>
    </div>
  );
}
