import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __filename = fileURLToPath(import.meta.url);
const repoRoot = dirname(dirname(__filename));
const webRequire = createRequire(join(repoRoot, "apps/web/package.json"));
const ts = webRequire("typescript");

const files = [
  "apps/web/app/page.tsx",
  "apps/web/app/layout.tsx",
  "apps/web/app/ui/dashboard.tsx",
];

const diagnostics = [];

for (const relativePath of files) {
  const fileName = join(repoRoot, relativePath);
  const source = readFileSync(fileName, "utf8");
  const result = ts.transpileModule(source, {
    fileName,
    reportDiagnostics: true,
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  });
  diagnostics.push(...(result.diagnostics ?? []));
}

if (diagnostics.length > 0) {
  const formatted = diagnostics
    .map((diagnostic) => ts.flattenDiagnosticMessageText(diagnostic.messageText, "\n"))
    .join("\n");
  console.error(formatted);
  process.exit(1);
}

console.log(`web dashboard transpile ok (${files.length} files)`);
