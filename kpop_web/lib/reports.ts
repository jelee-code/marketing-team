import fs from "fs";
import path from "path";

const REPORTS_DIR = path.join(process.cwd(), "..", "kpop_agent", "reports");

export type Report = {
  date: string;
  raw: string;
  top3: string[];
};

function extractTop3(raw: string): string[] {
  const lines = raw.split("\n");
  const items: string[] = [];
  let inTop3 = false;
  for (const line of lines) {
    if (/^##\s+.*핵심 이슈/.test(line)) {
      inTop3 = true;
      continue;
    }
    if (inTop3 && /^##\s/.test(line)) break;
    if (!inTop3) continue;

    const numbered = line.match(/^\s*\d+\.\s+\*\*(.+?)\*\*/);
    if (numbered) {
      items.push(numbered[1]);
      continue;
    }
    const bulleted = line.match(/^\s*-\s+\*\*(.+?)\*\*/);
    if (bulleted) {
      items.push(bulleted[1]);
    }
  }
  return items.slice(0, 3);
}

function isReportFile(name: string): boolean {
  return name.endsWith(".md") && name !== "INDEX.md";
}

export function getAllReports(): Report[] {
  if (!fs.existsSync(REPORTS_DIR)) return [];
  const files = fs.readdirSync(REPORTS_DIR).filter(isReportFile);
  const reports = files.map((file) => {
    const date = file.replace(".md", "");
    const raw = fs.readFileSync(path.join(REPORTS_DIR, file), "utf-8");
    return { date, raw, top3: extractTop3(raw) };
  });
  reports.sort((a, b) => b.date.localeCompare(a.date));
  return reports;
}

export function getReport(date: string): Report | null {
  const filePath = path.join(REPORTS_DIR, `${date}.md`);
  if (!fs.existsSync(filePath)) return null;
  const raw = fs.readFileSync(filePath, "utf-8");
  return { date, raw, top3: extractTop3(raw) };
}
