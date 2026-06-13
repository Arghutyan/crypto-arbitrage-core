import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Spread+ | Crypto Arbitrage Dashboard",
  description:
    "Real-time cross-exchange crypto arbitrage spreads, funding, and signals.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen font-sans">{children}</body>
    </html>
  );
}
