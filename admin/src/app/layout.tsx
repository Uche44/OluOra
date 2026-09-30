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
  title: "OluOra Admin",
  description: "Internal operations and growth dashboard for OluOra.",
  robots: { index: false, follow: false },
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
