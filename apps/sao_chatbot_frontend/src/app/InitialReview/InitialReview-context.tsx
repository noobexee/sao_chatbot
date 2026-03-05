"use client";

import React, { createContext, useContext, useState } from "react";

interface InitialReviewFile {
  id: string;
  fileObj: File;
  previewUrl: string;
  type: 'image' | 'pdf' | 'other';
  name: string;
}

interface InitialReviewContextType {
  currentFile: InitialReviewFile | null;
  setCurrentFile: (file: InitialReviewFile | null) => void;
}

const InitialReviewContext = createContext<InitialReviewContextType | undefined>(undefined);

export function InitialReviewProvider({ children }: { children: React.ReactNode }) {
  const [currentFile, setCurrentFile] = useState<InitialReviewFile | null>(null);

  return (
    <InitialReviewContext.Provider value={{ currentFile, setCurrentFile }}>
      {children}
    </InitialReviewContext.Provider>
  );
}

export function useInitialReview() {
  const context = useContext(InitialReviewContext);
  if (!context) {
    throw new Error("useInitialReview must be used within an InitialReviewProvider");
  }
  return context;
}