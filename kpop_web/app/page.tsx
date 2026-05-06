import Link from "next/link";
import { getAllReports } from "@/lib/reports";

function formatDate(date: string): string {
  const [year, month, day] = date.split("-");
  if (!year || !month || !day) return date;
  return `${year}년 ${parseInt(month)}월 ${parseInt(day)}일`;
}

function dayOfWeek(date: string): string {
  const d = new Date(date);
  return ["일", "월", "화", "수", "목", "금", "토"][d.getDay()];
}

export default function Home() {
  const reports = getAllReports();

  if (reports.length === 0) {
    return (
      <div className="text-center py-24">
        <p className="text-neutral-500">아직 발행된 리포트가 없습니다.</p>
        <p className="text-sm text-neutral-400 mt-2">
          첫 리포트는 다음 평일 오전 8:30 KST에 도착합니다.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-baseline justify-between mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">최근 리포트</h1>
        <span className="text-sm text-neutral-400">
          총 {reports.length}건
        </span>
      </div>

      <ul className="space-y-3">
        {reports.map((report) => (
          <li key={report.date}>
            <Link
              href={`/${report.date}`}
              className="group block p-5 rounded-lg border border-neutral-200 hover:border-neutral-900 hover:shadow-sm transition-all"
            >
              <div className="flex items-baseline justify-between mb-3">
                <div className="flex items-baseline gap-2">
                  <span className="text-base font-medium">
                    {formatDate(report.date)}
                  </span>
                  <span className="text-xs text-neutral-400">
                    ({dayOfWeek(report.date)})
                  </span>
                </div>
                <span className="text-xs text-neutral-400 group-hover:text-neutral-900 transition">
                  열기 →
                </span>
              </div>

              {report.preview.length > 0 ? (
                <ul className="text-sm text-neutral-600 space-y-1.5 list-disc list-inside marker:text-neutral-400">
                  {report.preview.map((title, i) => (
                    <li key={i} className="truncate pl-1">
                      {title}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-neutral-400 italic">
                  미리보기 없음
                </p>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
