"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/libs/auth/login";

export default function LoginPage() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await login(username, password);
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("role", data.user.role);

      if (data.user.role === "admin") {
        router.push("/admin");
      } else if (data.user.role === "document_manager") {
        router.push("/merger");
      } else {
        router.push("/chatbot");
      }
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-white p-4 text-gray-800">
      
      <div className="w-full max-w-md rounded-2xl border border-gray-100 bg-white p-8 shadow-xl">
        
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-bold text-[#1e293b]">เข้าสู่ระบบ</h2>
          <p className="text-gray-500">SAO Chatbot System</p>
        </div>

        <div className="space-y-4">
          
          {/* Username */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Username
            </label>
            <input 
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-gray-300 p-3 text-gray-800 outline-none focus:border-[#a83b3b] focus:ring-1 focus:ring-[#a83b3b]"
              placeholder="Enter username"
            />
          </div>

          {/* Password */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Password
            </label>
            <input 
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 p-3 text-gray-800 outline-none focus:border-[#a83b3b] focus:ring-1 focus:ring-[#a83b3b]"
              placeholder="••••••••"
            />
          </div>

          {/* Error */}
          {error && (
            <p className="text-sm text-red-500">{error}</p>
          )}

          {/* Button */}
          <button
            onClick={handleLogin}
            disabled={loading}
            className="w-full rounded-lg bg-[#a83b3b] p-3 font-medium text-white transition-colors hover:bg-[#8a2f2f] disabled:opacity-50"
          >
            {loading ? "กำลังเข้าสู่ระบบ..." : "เข้าใช้งาน (Login)"}
          </button>

        </div>
      </div>
    </div>
  );
}