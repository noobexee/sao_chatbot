import type { Metadata } from "next";
import { Kanit } from "next/font/google"; // Assuming you added the font here too
import "./globals.css";

const kanit = Kanit({
  subsets: ["thai", "latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-kanit",
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
      <body className={kanit.className}>{children}</body>
    </html>
  );
}