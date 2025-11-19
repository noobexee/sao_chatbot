import Link from "next/link";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-white p-4">
      <div className="w-full max-w-md rounded-2xl border border-gray-100 bg-white p-8 shadow-xl">
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-bold text-[#1e293b]">เข้าสู่ระบบ</h2>
          <p className="text-gray-500">SAO Chatbot System</p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Username</label>
            <input 
              type="text" 
              className="w-full rounded-lg border border-gray-300 p-3 outline-none focus:border-[#a83b3b] focus:ring-1 focus:ring-[#a83b3b]"
              placeholder="Enter username"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Password</label>
            <input 
              type="password" 
              className="w-full rounded-lg border border-gray-300 p-3 outline-none focus:border-[#a83b3b] focus:ring-1 focus:ring-[#a83b3b]"
              placeholder="••••••••"
            />
          </div>
          
          <Link href="/chatbot" className="block pt-2">
            <button className="w-full rounded-lg bg-[#a83b3b] p-3 font-medium text-white transition-colors hover:bg-[#8a2f2f]">
              เข้าใช้งาน (Login)
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}