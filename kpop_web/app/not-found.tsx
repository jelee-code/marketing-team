import Link from "next/link";

export default function NotFound() {
  return (
    <div className="text-center py-24">
      <p className="text-2xl font-semibold mb-3">404</p>
      <p className="text-neutral-500 mb-6">해당 날짜의 리포트가 없습니다.</p>
      <Link
        href="/"
        className="inline-block text-sm text-neutral-900 underline underline-offset-4 hover:text-neutral-600 transition"
      >
        전체 리포트로 돌아가기
      </Link>
    </div>
  );
}
