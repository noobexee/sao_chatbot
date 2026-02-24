import type { Metadata } from "next";
import { Sarabun } from 'next/font/google';
import "./globals.css";

const sarabun = Sarabun({
  weight: ['100', '200', '300', '400', '500', '600', '700', '800'],
  subsets: ['thai', 'latin'],
  variable: '--font-th-sarabun',
  display: 'swap',
});

export const metadata: Metadata = {
  title: "SAO Chatbot",
  description: "Chatbot system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={sarabun.className}>{children}</body>
    </html>
  );
}