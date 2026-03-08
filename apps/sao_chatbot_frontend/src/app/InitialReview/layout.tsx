"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { InitialReviewProvider } from "./InitialReview-context";

export default function InitialReviewLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <InitialReviewProvider>
      <div className="flex h-screen w-full flex-col overflow-hidden bg-[#f0f2f5]">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-6 shadow-sm z-10">
          <div className="flex items-center gap-10">
            <Link href="/InitialReview">
                <h1 className="text-xl font-bold text-[#1e293b] hover:text-blue-600 transition-colors">
                  Initial Review Process
                </h1>
            </Link>
            <Link href="/chatbot">
                <div className="cursor-pointer truncate flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 shrink-0">
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                  Chat
                </div>
            </Link>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="cursor-pointer truncate relative h-10 w-10 shrink-0 overflow-hidden rounded-full border border-gray-200 bg-gray-100">
                <Image src="/user-placeholder.jpg" alt="User" width={40} height={40} className="object-cover w-full h-full" />
                <span className="absolute bottom-0 right-0 block h-3 w-3 rounded-full bg-green-500 ring-2 ring-white"></span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-hidden">
            {children}
        </main>
      </div>
    </InitialReviewProvider>
  );
}