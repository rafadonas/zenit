import { readFileSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const dashboardRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const sourceRoot = join(dashboardRoot, "src");
const styles = readFileSync(join(sourceRoot, "app/styles.css"), "utf8");

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return entry.name.endsWith(".tsx") ? [path] : [];
  });
}

function cssVariable(name: string): string {
  const match = styles.match(new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`));
  if (!match) throw new Error(`Missing CSS variable --${name}`);
  return match[1];
}

function relativeLuminance(hex: string): number {
  const channels = [1, 3, 5].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16) / 255);
  const linear = channels.map((value) => (
    value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
  ));
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrastRatio(first: string, second: string): number {
  const firstLuminance = relativeLuminance(first);
  const secondLuminance = relativeLuminance(second);
  const light = Math.max(firstLuminance, secondLuminance);
  const dark = Math.min(firstLuminance, secondLuminance);
  return (light + 0.05) / (dark + 0.05);
}

describe("dashboard accessibility baseline", () => {
  it("provides a skip link and one shared target on every main shell", () => {
    const layout = readFileSync(join(sourceRoot, "app/layout.tsx"), "utf8");
    expect(layout).toContain('className="skip-link"');
    expect(layout).toContain('href="#main-content"');

    const mainShells = sourceFiles(sourceRoot)
      .map((path) => ({ path, source: readFileSync(path, "utf8") }))
      .filter(({ source }) => source.includes("<main"));
    expect(mainShells.length).toBeGreaterThanOrEqual(8);
    for (const { path, source } of mainShells) {
      expect(source, path).toContain('id="main-content"');
      expect(source.match(/id="main-content"/g), path).toHaveLength(1);
    }
  });

  it("keeps keyboard focus visible and supports reduced motion", () => {
    expect(styles).toContain(".skip-link:focus-visible");
    expect(styles).toContain('[role="button"]):focus-visible');
    expect(styles).toContain("@media (prefers-reduced-motion: reduce)");
    expect(styles).toContain(".loading-mark { animation: none; }");
  });

  it("keeps normal muted text at WCAG AA contrast on primary surfaces", () => {
    const muted = cssVariable("muted");
    expect(contrastRatio(muted, cssVariable("paper"))).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(muted, cssVariable("card"))).toBeGreaterThanOrEqual(4.5);
  });
});
