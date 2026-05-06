import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "영등포 타임스퀘어 일일 행사",
  description: "영등포 타임스퀘어 진행/예정/종료 행사 일일 업데이트 — 마케팅팀 내부 공유용",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="bg-white text-neutral-900 font-sans antialiased min-h-screen flex flex-col">
        <header className="border-b border-neutral-200">
          <div className="max-w-3xl mx-auto px-6 py-5 flex items-center justify-between">
            <Link
              href="/"
              className="text-base font-semibold tracking-tight hover:text-neutral-700 transition"
            >
              영등포 타임스퀘어 일일 행사
            </Link>
            <span className="text-xs uppercase tracking-wider text-neutral-400">
              marketing team
            </span>
          </div>
        </header>
        <main className="flex-1 max-w-3xl w-full mx-auto px-6 py-10">
          {children}
        </main>
        <footer className="border-t border-neutral-100">
          <div className="max-w-3xl mx-auto px-6 py-6 text-xs text-neutral-400">
            매일 평일 오전 7:00 KST 자동 발행 · 월요일 리포트는 금·토·일 통합
          </div>
        </footer>
      </body>
    </html>
  );
}
