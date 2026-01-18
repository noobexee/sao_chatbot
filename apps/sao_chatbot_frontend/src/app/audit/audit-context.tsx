"use client";

import React, { createContext, useContext, useState } from "react";

interface AuditFile {
  id: string;
  fileObj: File;
  previewUrl: string;
  type: 'image' | 'pdf' | 'other';
  name: string;
}

interface AuditContextType {
  currentFile: AuditFile | null;
  setCurrentFile: (file: AuditFile | null) => void;
}

const AuditContext = createContext<AuditContextType | undefined>(undefined);

export function AuditProvider({ children }: { children: React.ReactNode }) {
  const [currentFile, setCurrentFile] = useState<AuditFile | null>(null);

  return (
    <AuditContext.Provider value={{ currentFile, setCurrentFile }}>
      {children}
    </AuditContext.Provider>
  );
}

export function useAudit() {
  const context = useContext(AuditContext);
  if (!context) {
    throw new Error("useAudit must be used within an AuditProvider");
  }
  return context;
}