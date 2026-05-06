import fs from "fs";
import path from "path";

const REPORTS_DIR = path.join(
  process.cwd(),
  "..",
  "timessquare_agent",
  "reports",
);

export type Report = {
  date: string;
  raw: string;
  preview: string[];
};

function extractPreview(raw: string): string[] {
  const lines = raw.split("\n");
  const items: string[] = [];
  let pastTitle = false;

  for (const line of lines) {
    if (/^#\s/.test(line)) {
      pastTitle = true;
      continue;
    }
    if (!pastTitle) continue;

    // Stop at sources section
    if (/^##\s+출처/.test(line)) break;

    const match = line.match(/^\s*-\s+\*\*(.+?)\*\*/);
    if (match && items.length < 3) {
      items.push(match[1]);
    }
    if (items.length >= 3) break;
  }
  return items;
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
    return { date, raw, preview: extractPreview(raw) };
  });
  reports.sort((a, b) => b.date.localeCompare(a.date));
  return reports;
}

export function getReport(date: string): Report | null {
  const filePath = path.join(REPORTS_DIR, `${date}.md`);
  if (!fs.existsSync(filePath)) return null;
  const raw = fs.readFileSync(filePath, "utf-8");
  return { date, raw, preview: extractPreview(raw) };
}
