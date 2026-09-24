import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const css = readFileSync(path.join(process.cwd(), "src", "app", "globals.css"), "utf8");

function token(name: string) {
  const value = css.match(new RegExp("--" + name + ":\\s*(#[0-9a-fA-F]{6})"))?.[1];
  if (!value) throw new Error("Missing color token: " + name);
  return value;
}

function luminance(hex: string) {
  const channels = [1, 3, 5].map((index) => {
    const normalized = parseInt(hex.slice(index, index + 2), 16) / 255;
    return normalized <= 0.04045 ? normalized / 12.92 : ((normalized + 0.055) / 1.055) ** 2.4;
  });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}

function contrast(foreground: string, background: string) {
  const [lighter, darker] = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

function skipLinkColor(property: "color" | "background") {
  const rule = css.match(/\.skip-link\s*\{([^}]*)\}/)?.[1];
  const value = rule?.match(new RegExp(`(?:^|;)\\s*${property}\\s*:\\s*([^;]+)`))?.[1].trim();
  if (!value) throw new Error(`Missing skip-link ${property}`);
  const variable = value.match(/^var\(--([\w-]+)\)$/)?.[1];
  const hex = variable ? token(variable) : value;
  if (/^#[0-9a-fA-F]{3}$/.test(hex)) return `#${[...hex.slice(1)].map((digit) => digit + digit).join("")}`;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`Unsupported skip-link ${property}: ${value}`);
  return hex;
}

describe("core text contrast", () => {
  it.each([
    ["primary text", "ink", "canvas"],
    ["body text", "muted", "surface"],
    ["secondary text", "subtle", "surface"],
    ["accent labels", "blue-soft", "surface"],
    ["error text", "rose", "surface"],
  ])("%s meets WCAG AA for normal text", (_label, foreground, background) => {
    expect(contrast(token(foreground), token(background))).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps the primary action text readable", () => {
    expect(contrast("#061126", token("blue-soft"))).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps the actual skip-link text and background above 4.5:1", () => {
    expect(contrast(skipLinkColor("color"), skipLinkColor("background"))).toBeGreaterThanOrEqual(4.5);
  });
});
