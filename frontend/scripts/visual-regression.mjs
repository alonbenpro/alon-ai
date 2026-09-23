import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { mkdtemp, mkdir, rm, stat } from "node:fs/promises";
import { createServer as createPortServer } from "node:net";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const baselineDir = path.join(root, "tests", "visual");
const chrome = process.env.CHROME_BIN ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const update = process.env.UPDATE_VISUAL_BASELINES === "1";
const viewport = { width: 1280, height: 800 };
const maxChangedFraction = 0.005;
const maxMeanChannelDifference = 1.5;
const significantChannelDifference = 20;

let mode = "login";
const activity = {
  items: [
    { id: "00000000-0000-4000-8000-000000000001", kind: "Research", state: "running", label: "Offer research is running", occurred_at: "2026-09-23T10:00:00Z" },
    { id: "00000000-0000-4000-8000-000000000002", kind: "Validation", state: "queued", label: "Validation is queued", occurred_at: "2026-09-23T09:58:00Z" },
    { id: "00000000-0000-4000-8000-000000000003", kind: "Review", state: "completed", label: "Operator review completed", occurred_at: "2026-09-23T09:52:00Z" },
  ],
  cursor: null,
};
const status = {
  health: { status: "ok" },
  readiness: { status: "ready" },
  counts: { queued: 2, running: 1, completed: 8, blocked: 0 },
};

function apiResponse(request, response) {
  const pathName = new URL(request.url, "http://localhost").pathname;
  const unauthorized = mode === "login";
  const json = (statusCode, value) => {
    response.writeHead(statusCode, {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    });
    response.end(JSON.stringify(value));
  };
  if (unauthorized) return json(401, { detail: "Unauthorized" });
  if (pathName === "/auth/session") return json(200, { authenticated: true, operator: { id: "00000000-0000-4000-8000-000000000000", display_name: "Alon" } });
  if (pathName === "/operator/status") return json(200, status);
  if (pathName === "/operator/activity") return json(200, activity);
  if (pathName === "/operator/activity/events") {
    response.writeHead(204, { "Cache-Control": "no-store" });
    return response.end();
  }
  return json(404, { detail: "Not found" });
}

async function freePort() {
  const server = createPortServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  assert(address && typeof address !== "string");
  const port = address.port;
  await new Promise((resolve) => server.close(resolve));
  return port;
}

async function waitFor(url, processHandle) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (processHandle.exitCode !== null) throw new Error("Next server exited before readiness");
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // The local server can take a moment to bind.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("Next server did not become ready");
}

async function runChrome(url, output, profile) {
  const child = spawn(chrome, [
      "--headless=new",
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-background-networking",
      "--disable-component-update",
      "--disable-default-apps",
      "--disable-extensions",
      "--disable-features=Translate",
      "--force-color-profile=srgb",
      "--force-device-scale-factor=1",
      "--hide-scrollbars",
      "--window-size=" + viewport.width + "," + viewport.height,
      "--virtual-time-budget=3000",
      "--user-data-dir=" + profile,
      "--screenshot=" + output,
      url,
    ], { stdio: ["ignore", "ignore", "pipe"] });
  let stderr = "";
  let exited = false;
  let spawnError;
  child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
  child.on("error", (error) => { spawnError = error; exited = true; });
  child.on("exit", () => { exited = true; });
  try {
    for (let attempt = 0; attempt < 250; attempt += 1) {
      try {
        const first = await stat(output);
        if (first.size > 0) {
          await new Promise((resolve) => setTimeout(resolve, 150));
          const second = await stat(output);
          if (second.size === first.size) {
            const metadata = await sharp(output).metadata();
            assert.deepEqual([metadata.width, metadata.height], [viewport.width, viewport.height], "Chrome viewport size changed");
            return;
          }
        }
      } catch {
        // Chrome has not written its screenshot yet.
      }
      if (exited) throw new Error("Chrome exited without screenshot: " + (spawnError?.message ?? stderr.slice(-1200)));
      await new Promise((resolve) => setTimeout(resolve, 100));
    }
    throw new Error("Chrome did not write a screenshot: " + stderr.slice(-1200));
  } finally {
    child.kill("SIGTERM");
  }
}

async function compare(baseline, actual) {
  const first = await sharp(baseline).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  const second = await sharp(actual).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  assert.deepEqual(
    [first.info.width, first.info.height, first.info.channels],
    [second.info.width, second.info.height, second.info.channels],
    "Screenshot dimensions changed",
  );
  let changed = 0;
  let totalDifference = 0;
  const pixels = first.info.width * first.info.height;
  for (let index = 0; index < first.data.length; index += 4) {
    let largest = 0;
    for (let channel = 0; channel < 3; channel += 1) {
      const difference = Math.abs(first.data[index + channel] - second.data[index + channel]);
      totalDifference += difference;
      largest = Math.max(largest, difference);
    }
    if (largest > significantChannelDifference) changed += 1;
  }
  const changedFraction = changed / pixels;
  const meanDifference = totalDifference / (pixels * 3);
  assert(changedFraction <= maxChangedFraction && meanDifference <= maxMeanChannelDifference,
    "Visual regression: " + (changedFraction * 100).toFixed(2) + "% changed pixels; mean channel difference " + meanDifference.toFixed(2));
  return { changedFraction, meanDifference };
}

await stat(chrome);
const temporary = await mkdtemp(path.join(os.tmpdir(), "alon-ai-visual-"));
const api = createServer(apiResponse);
await new Promise((resolve) => api.listen(0, "127.0.0.1", resolve));
const apiAddress = api.address();
assert(apiAddress && typeof apiAddress !== "string");
const port = await freePort();
const next = spawn(process.execPath, [path.join(root, "node_modules", "next", "dist", "bin", "next"), "start", "-p", String(port), "-H", "127.0.0.1"], {
  cwd: root,
  env: { ...process.env, API_BASE_URL: "http://127.0.0.1:" + apiAddress.port },
  stdio: ["ignore", "pipe", "pipe"],
});
let nextOutput = "";
next.stdout.on("data", (chunk) => { nextOutput += chunk.toString(); });
next.stderr.on("data", (chunk) => { nextOutput += chunk.toString(); });
let passed = false;

try {
  await waitFor("http://127.0.0.1:" + port + "/login", next);
  if (update) await mkdir(baselineDir, { recursive: true });
  for (const [name, route, activeMode] of [
    ["login", "/login", "login"],
    ["operator-shell", "/", "shell"],
  ]) {
    mode = activeMode;
    const actual = path.join(temporary, name + ".png");
    const profile = path.join(temporary, name + "-profile");
    await runChrome("http://127.0.0.1:" + port + route, actual, profile);
    const baseline = path.join(baselineDir, name + ".png");
    if (update) {
      await sharp(actual).png().toFile(baseline);
      console.log("Updated visual baseline: " + path.relative(root, baseline));
    } else {
      const result = await compare(baseline, actual);
      console.log(name + ": pass (" + (result.changedFraction * 100).toFixed(3) + "% changed pixels, mean difference " + result.meanDifference.toFixed(3) + ")");
    }
  }
  passed = true;
} catch (error) {
  console.error(nextOutput.slice(-2000));
  console.error("Visual artifacts retained at " + temporary);
  throw error;
} finally {
  next.kill("SIGTERM");
  api.close();
  if (passed) await rm(temporary, { recursive: true, force: true });
}
