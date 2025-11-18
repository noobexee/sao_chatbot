import Image from "next/image";
import Link from "next/link";
import { Kanit } from "next/font/google";

const kanit = Kanit({
  subsets: ["thai", "latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-kanit",
});

export default function Home() {
  return (
    <main
      className={`flex min-h-screen flex-col items-center justify-center bg-white p-4 ${kanit.className}`}>
      <div className="flex flex-col items-center space-y-8 text-center">
        <div className="relative mb-4">
          <Image
            src="/logo.png"
            alt="SAO Logo"
            width={1200}
            height={1200}
            className="h-auto w-32 md:w-40"
            priority
          />
        </div>
        <div className="space-y-4">
          <h1 className="text-2xl font-semibold text-[#1e293b] md:text-3xl">
            ยินดีต้อนรับสู่ SAO Chatbot
          </h1>
          <p className="text-lg font-medium text-[#1e293b] md:text-xl">
            ลงทะเบียนเข้าใช้เพื่อเข้าใช้งาน
          </p>
        </div>

        <div className="pt-12">
          <Link href="/chatbot"> 
            <button className="cursor-pointer truncate group relative flex items-center justify-center rounded-full border border-gray-200 bg-white px-16 py-4 text-[#a83b3b] shadow-[0_4px_14px_0_rgba(0,0,0,0.05)] transition-all hover:-translate-y-0.5 hover:shadow-[0_6px_20px_rgba(0,0,0,0.1)] active:translate-y-0">
              <span className="text-lg font-medium">ลงชื่อเข้าใช้</span>
            </button>
          </Link>
        </div>
        
      </div>
      <footer className="absolute bottom-4 text-xs text-gray-400">
        © 2025 SAO Chatbot
      </footer>
    </main>
  );
}
