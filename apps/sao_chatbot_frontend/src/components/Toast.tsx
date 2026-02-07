"use client";

import { useEffect } from "react";

type ToastProps = {
  message: string;
  show: boolean;
  onClose: () => void;
};

export default function Toast({ message, show, onClose }: ToastProps) {
  useEffect(() => {
    if (!show) return;
    const timer = setTimeout(onClose, 2500);
    return () => clearTimeout(timer);
  }, [show, onClose]);

  if (!show) return null;

  return (
    <div className="fixed top-6 right-6 z-50 animate-fade-in-out">
      <div className="rounded-xl bg-black text-white px-5 py-3 shadow-lg">
        {message}
      </div>
    </div>
  );
}
