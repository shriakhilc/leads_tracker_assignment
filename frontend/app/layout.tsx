import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Leads Tracker",
  description: "Public lead intake + internal lead management",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
