import type { Metadata } from "next";
import { Playfair_Display, Literata } from "next/font/google";
import "./globals.css";

const playfair = Playfair_Display({
  variable: "--font-playfair",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const literata = Literata({
  variable: "--font-literata",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "OluOra - Audience Intelligence for Creators",
  description:
    "OluOra transforms your comments into actionable audience intelligence. Discover what your viewers are asking, what content to create next, and which topics are gaining momentum.",
  keywords: [
    "YouTube analytics",
    "audience intelligence",
    "creator tools",
    "comment analysis",
    "content strategy",
  ],
  authors: [{ name: "OluOra" }],
  openGraph: {
    title: "OluOra - Audience Intelligence for Creators",
    description:
      "Transform thousands of comments into actionable insights. Know exactly what your audience wants.",
    type: "website",
    siteName: "OluOra",
  },
  twitter: {
    card: "summary_large_image",
    title: "OluOra - Audience Intelligence for Creators",
    description: "Transform thousands of comments into actionable insights.",
  },
  icons: {
    icon: "/icons/logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${playfair.variable} ${literata.variable} h-full`}
    >
      <body className="min-h-full flex flex-col bg-surface antialiased">
        {children}
      </body>
    </html>
  );
}
