import Link from "next/link";
import { notFound } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getAllReports, getReport } from "@/lib/reports";

export function generateStaticParams() {
  return getAllReports().map((r) => ({ date: r.date }));
}

export const dynamicParams = false;

export default function ReportPage({ params }: { params: { date: string } }) {
  const report = getReport(params.date);
  if (!report) notFound();

  return (
    <div>
      <Link
        href="/"
        className="inline-block text-sm text-neutral-500 hover:text-neutral-900 mb-6 transition"
      >
        ← 전체 리포트
      </Link>

      <article className="prose prose-neutral max-w-none prose-headings:tracking-tight prose-h1:text-3xl prose-h2:text-xl prose-h2:mt-10 prose-h3:text-base prose-h3:mt-6 prose-a:text-neutral-900 prose-a:underline prose-a:underline-offset-2 hover:prose-a:text-neutral-600 prose-strong:text-neutral-900 prose-li:my-1">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{report.raw}</ReactMarkdown>
      </article>
    </div>
  );
}
