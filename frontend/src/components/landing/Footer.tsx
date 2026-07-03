import Link from "next/link";

const footerLinks = {
  Product: [
    { label: "Features", href: "#solutions" },
    { label: "Methodology", href: "#methodology" },
    { label: "Pricing", href: "#pricing" },
  ],
  Company: [
    { label: "About Us", href: "#about" },
    { label: "Journal", href: "#journal" },
    { label: "Careers", href: "#careers" },
  ],
  Resources: [
    { label: "Intelligence Report", href: "#report" },
    { label: "Help Center", href: "#help" },
    // { label: "API Docs", href: "#api" },
  ],
};

export default function Footer() {
  return (
    <footer className="bg-surface-container-low border-t border-outline-variant/30 py-16 lg:py-20">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <div className="grid grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr] gap-10 mb-12">
          {/* Brand */}
          <div className="col-span-2 lg:col-span-1">
            <Link
              href="/"
              className="inline-block mb-4"
            >
              <span className="font-playfair text-[1.5rem] font-bold text-primary tracking-tight">
                OluOra
              </span>
            </Link>
            <p className="font-literata text-sm text-on-surface-variant leading-[1.7] max-w-[240px]">
              Sophisticated intelligence for the world&apos;s leading
              professional creators.
            </p>
          </div>

          {/* Links */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <h3 className="font-literata text-xs font-semibold tracking-[0.08em] uppercase text-on-surface mb-4">
                {category}
              </h3>
              <ul className="space-y-3">
                {links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="font-literata text-sm text-on-surface-variant hover:text-on-surface transition-colors duration-150"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="border-t border-outline-variant/30 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="font-literata text-xs text-on-surface-variant">
            © 2024 OluOra. All rights reserved.
          </p>
          <div className="flex items-center gap-5">
            {[
              { label: "Privacy Policy", href: "#privacy" },
              { label: "Terms of Service", href: "#terms" },
              { label: "Contact Support", href: "#contact" },
            ].map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className="font-literata text-xs text-on-surface-variant hover:text-on-surface transition-colors duration-150"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
