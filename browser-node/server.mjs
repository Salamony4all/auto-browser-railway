import { mkdir, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { chromium } from "playwright";

const width = Number.parseInt(process.env.BROWSER_WIDTH || "1280", 10);
const height = Number.parseInt(process.env.BROWSER_HEIGHT || "800", 10);
const endpointFile = process.env.BROWSER_WS_ENDPOINT_FILE || "/data/profile/browser-ws-endpoint.txt";
const host = process.env.PLAYWRIGHT_SERVER_HOST || "0.0.0.0";
const port = Number.parseInt(process.env.PLAYWRIGHT_SERVER_PORT || "9223", 10);
const advertisedHost = process.env.PLAYWRIGHT_SERVER_ADVERTISED_HOST || "browser-node";

const browserServer = await chromium.launchServer({
  headless: false,
  chromiumSandbox: false,
  host,
  port,
  wsPath: "playwright",
  downloadsPath: "/data/downloads",
  args: [
    `--window-size=${width},${height}`,
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-software-rasterizer",
    "--disable-background-networking",
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--lang=en-US,en",
    "--disable-notifications",
    "--remote-debugging-port=9222",
    "--remote-debugging-address=0.0.0.0",
  ],
});

const rawEndpoint = new URL(browserServer.wsEndpoint());
rawEndpoint.hostname = advertisedHost;
rawEndpoint.port = String(port);
const advertisedEndpoint = rawEndpoint.toString();

await mkdir(dirname(endpointFile), { recursive: true });
const tmpFile = `${endpointFile}.tmp`;
await writeFile(tmpFile, advertisedEndpoint, "utf-8");
await rename(tmpFile, endpointFile);
console.log(`wrote ${endpointFile}: ${advertisedEndpoint}`);

try {
  const cdpRes = await fetch("http://127.0.0.1:9222/json/version");
  const cdpData = await cdpRes.json();
  let cdpUrl = cdpData.webSocketDebuggerUrl;
  const cdpFile = "/data/profile/cdp-endpoint.txt";
  const cdpTmp = `${cdpFile}.tmp`;
  // Replace 127.0.0.1 with advertisedHost so the controller can reach it via Railway internal network
  cdpUrl = cdpUrl.replace("127.0.0.1", advertisedHost).replace("localhost", advertisedHost);
  await writeFile(cdpTmp, cdpUrl, "utf-8");
  await rename(cdpTmp, cdpFile);
  console.log(`wrote ${cdpFile}: ${cdpUrl}`);
} catch (err) {
  console.error("Failed to write cdp-endpoint.txt:", err);
}

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, async () => {
    await browserServer.close();
    process.exit(0);
  });
}

await new Promise((resolve) => browserServer.on("close", resolve));
