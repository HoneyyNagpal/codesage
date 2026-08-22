#!/usr/bin/env node
/**
 * Reads source code from stdin, parses it with @babel/parser (which supports
 * JSX, TypeScript, optional chaining, nullish coalescing, decorators, and
 * every other modern syntax feature esprima does not), and prints the
 * resulting AST as JSON to stdout. Python calls this via subprocess.
 */
const parser = require("@babel/parser");

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => { input += chunk; });
process.stdin.on("end", () => {
  try {
    const ast = parser.parse(input, {
      sourceType: "unambiguous",
      allowReturnOutsideFunction: true,
      errorRecovery: true,
      plugins: [
        "jsx",
        "typescript",
        "classProperties",
        "classPrivateProperties",
        "classPrivateMethods",
        "decorators-legacy",
        "objectRestSpread",
        "optionalChaining",
        "nullishCoalescingOperator",
        "dynamicImport",
        "topLevelAwait",
      ],
    });

    // errorRecovery:true means parse errors land in ast.errors instead of throwing
    if (ast.errors && ast.errors.length > 0) {
      process.stdout.write(JSON.stringify({
        error: ast.errors.map(e => e.reasonCode + ": " + (e.message || "")).join("; "),
      }));
      return;
    }

    process.stdout.write(JSON.stringify({ ast: ast.program }));
  } catch (e) {
    process.stdout.write(JSON.stringify({ error: e.message }));
  }
});