"use client";

import Link from "next/link";
import { ArrowLeft, Shield, Eye, Database, Trash2 } from "lucide-react";

export default function PrivacyPolicyPage() {
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
          Privacy Policy
        </h1>
        <p className="text-sm text-zinc-400 mb-8">
          Effective Date: July 16, 2026
        </p>

        <div className="prose prose-invert max-w-none space-y-8 text-zinc-300 leading-relaxed">
          <section className="bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-6 lg:p-8 space-y-4">
            <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-3">
              <Shield className="w-5 h-5 text-teal-400" />
              Our Commitment
            </h2>
            <p className="text-sm text-zinc-400">
              OluOra is built specifically for creators. We respect your privacy, your account safety, and your viewers&apos; comments data. We never sell, lease, or distribute your data to third-party ad networks or brokers.
            </p>
          </section>

          {/* Section 1 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <Eye className="w-5 h-5 text-emerald-400" />
              1. Information We Collect
            </h2>
            <p>
              When you authenticate with Google to connect your YouTube Channel, we collect and store:
            </p>
            <ul className="list-disc list-inside space-y-2 text-zinc-400 text-sm pl-2">
              <li>
                <strong className="text-zinc-200">Google OAuth Credentials:</strong> Access tokens and refresh tokens to fetch channel metadata and video comments.
              </li>
              <li>
                <strong className="text-zinc-200">YouTube Channel Stats:</strong> Channel title, custom description, subscriber count, total video count, and upload playlist IDs.
              </li>
              <li>
                <strong className="text-zinc-200">YouTube Video Metadata:</strong> Title, description, upload date, views, likes, and comment counts.
              </li>
              <li>
                <strong className="text-zinc-200">Viewer Comments:</strong> Comment texts, author display names, profile image URLs, like counts, and published dates.
              </li>
            </ul>
          </section>

          {/* Section 2 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <Database className="w-5 h-5 text-teal-400" />
              2. How We Use and Process Your Information
            </h2>
            <p>
              We process comment data to generate analytical metrics for your creator dashboard:
            </p>
            <ul className="list-disc list-inside space-y-2 text-zinc-400 text-sm pl-2">
              <li>Grouping comments into key themes and topics using semantic text embeddings.</li>
              <li>Synthesizing recurring audience questions, pain points, and ideas.</li>
              <li>Running NLP sentiment analyzers to highlight overall video polarity.</li>
              <li>Optimizing API efficiency: We use ETags (HTTP 304) and delta sync to prevent redundant fetching, respecting YouTube API limits.</li>
            </ul>
          </section>

          {/* Section 3 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <Shield className="w-5 h-5 text-emerald-400" />
              3. Data Sharing, Transfer, and Disclosure
            </h2>
            <p className="text-zinc-400 text-sm">
              We do not transfer or disclose your information to third parties for purposes other than the ones provided. We do not sell, rent, or trade your Google user data or YouTube channel information to any third-party advertising networks, data brokers, or commercial entities.
            </p>
            <p className="text-zinc-400 text-sm">
              Google user data is only accessed and processed internally to provide the creator analytics and insight features explicitly requested by you.
            </p>
          </section>

          {/* Section 4 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <Database className="w-5 h-5 text-teal-400" />
              4. Data Protection and Security Safeguards
            </h2>
            <p className="text-zinc-400 text-sm">
              Security procedures are in place to protect the confidentiality of your data. We use encryption to protect your information both in transit (via HTTPS and TLS 1.3 protocols) and at rest within our secure server infrastructure.
            </p>
            <p className="text-zinc-400 text-sm">
              Access to system databases and OAuth tokens is strictly restricted to authorized system processes to prevent unauthorized access, alteration, or disclosure.
            </p>
          </section>

          {/* Section 5 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <Trash2 className="w-5 h-5 text-red-400" />
              5. Data Retention and Deletion
            </h2>
            <p>
              You maintain absolute control over your synced creator data:
            </p>
            <p className="text-zinc-400 text-sm">
              You can revoke permissions at any time from your YouTube/Google Account settings. Additionally, clicking <strong className="text-zinc-200">&quot;Disconnect Account&quot;</strong> in the OluOra settings interface immediately triggers a cascading delete, wiping your stored Google OAuth credentials, channel metadata, videos, comments, and AI cluster logs permanently from our database.
            </p>
          </section>

          {/* Section 6 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100">
              6. Google API Services User Data Policy Compliance
            </h2>
            <p className="text-sm text-zinc-400">
              OluOra&apos;s use and transfer of information received from Google APIs will adhere to the{" "}
              <a
                href="https://developers.google.com/terms/api-services-user-data-policy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-teal-400 hover:underline inline-flex items-center"
              >
                Google API Services User Data Policy
              </a>
              , including the Limited Use requirements.
            </p>
          </section>

          {/* Section 7 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100">
              7. Third-Party Links
            </h2>
            <p className="text-sm text-zinc-400">
              Our site interacts with Google and YouTube services. By using OluOra, you agree to be bound by the{" "}
              <a
                href="https://www.youtube.com/t/terms"
                target="_blank"
                rel="noopener noreferrer"
                className="text-teal-400 hover:underline"
              >
                YouTube Terms of Service
              </a>{" "}
              and the{" "}
              <a
                href="https://policies.google.com/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-teal-400 hover:underline"
              >
                Google Privacy Policy
              </a>.
            </p>
          </section>

          {/* Section 8 */}
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-zinc-100">
              8. Contact Support
            </h2>
            <p className="text-sm text-zinc-400">
              If you have any questions about this Privacy Policy or wish to request data purging, please reach out to us at <a href="mailto:perp@ijuaalkiez.resend.app" className="text-teal-400 hover:underline">contact email</a>.
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
