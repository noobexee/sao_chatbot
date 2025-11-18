import Image from "next/image";

export default function SpecificChatPage({ params }: { params: { chatId: string } }) {

  return (
    <div className="relative flex h-full flex-col bg-white">
      <div className="flex-1 overflow-y-auto px-4 pt-24 pb-32 scroll-smooth">
        <div className="mx-auto max-w-3xl space-y-6">
          
          <div className="flex w-full gap-3 items-start">
            <div className="relative h-8 w-8 shrink-0 overflow-hidden rounded-full bg-gray-200 border border-gray-100">
               <Image 
                 src="/user-placeholder.jpg"
                 alt="User" 
                 fill 
                 className="object-cover"
               />
            </div>
            <div className="flex flex-col">
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-semibold text-sm">คุณ</span>
                <span className="text-xs text-gray-500">02:22 AM</span>
              </div>
              <p className="leading-relaxed text-gray-800">
                เรื่องที่สำนักงานจะรับไว้ตรวจสอบการปฏิบัติตามกฎหมายจากเรื่องร้องเรียนบ้าง
              </p>
            </div>
          </div>

          <div className="flex w-full gap-3 items-start">
            <div className="h-8 w-8 shrink-0 flex items-center justify-center rounded-full bg-[#a83b3b] text-white text-xs font-semibold">
              SAO
            </div>
            <div className="flex flex-col">
              <div className="flex items-baseline gap-2 mb-1">
                <span className="font-semibold text-sm">SAO bot</span>
                <span className="text-xs text-gray-500">02:22 AM</span>
              </div>
              <div className="prose prose-sm leading-relaxed text-gray-800 break-words">
                <p>
                  ตามระเบียบสำนักงานการตรวจเงินแผ่นดินว่าด้วยการตรวจสอบการปฏิบัติตามกฎหมาย พ.ศ. ๒๕๕๑ ข้อ ๕
                  เรื่องที่สำนักงานที่สำนักงานจะรับพิจารณาตรวจสอบการปฏิบัติตามกฎหมาย ดังต่อไปนี้
                </p>
                <ol className="list-decimal pl-5 space-y-1">
                  <li>เรื่องที่คัดเลือกมาจากการประเมินความเสี่ยงของหน่วยรับตรวจ</li>
                  <li>เรื่องที่มาจากการร้องเรียน</li>
                  <li>เรื่องที่เป็นผลมาจากการตรวจสอบเข้าอื่น</li>
                  <li>เรื่องที่ผู้ว่าการสั่งให้ตรวจสอบเฉพาะกรณี หรือสั่งให้ตรวจสอบตามที่กำหนดไว้ในแผนการตรวจสอบประจำปี</li>
                </ol>
                <p className="mt-4">
                  <strong>อ้างอิง:</strong> ข้อ ๘ เรื่องที่สำนักงานพิจารณารับเรื่องตรวจสอบการปฏิบัติตามกฎหมาย มีดังต่อไปนี้
                </p>
                <ol className="list-decimal pl-5 space-y-1">
                  <li>เรื่องที่คัดเลือกมาจากการประเมินความเสี่ยงของหน่วยรับตรวจ</li>
                  <li>เรื่องที่มาจากการร้องเรียน</li>
                  <li>เรื่องที่เป็นผลมาจากการตรวจสอบงานอื่น</li>
                  <li>เรื่องที่ผู้ว่าการสั่งให้ตรวจสอบเฉพาะกรณี หรือสั่งให้ตรวจสอบตามที่กำหนดไว้ในแผนการตรวจสอบประจำปี</li>
                </ol>
                <p className="mt-4">
                  <strong>คำสำคัญ:</strong> ที่มาของเรื่องที่จะรับไว้ตรวจสอบ
                </p>
              </div>
            </div>
          </div>

        </div>
      </div>

      <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-white via-white to-transparent pt-10 pb-6">
        <div className="mx-auto max-w-3xl px-4">
          <div className="relative flex items-center rounded-[2rem] border border-gray-200 bg-white py-2 pl-6 pr-2 shadow-[0_2px_8px_rgba(0,0,0,0.05)] transition-shadow focus-within:shadow-[0_4px_12px_rgba(0,0,0,0.08)]">
            
            <input
              type="text"
              placeholder="ส่งข้อความให้ SAO bot"
              className="flex-1 border-none bg-transparent text-base text-gray-700 placeholder-gray-400 outline-none focus:ring-0"
            />

            <button className="flex h-10 w-10 items-center justify-center rounded-full bg-[#a83b3b] text-white transition-colors hover:bg-[#8f3232]">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>
              </svg>
            </button>

          </div>
        </div>
      </div>
    </div>
  );
}