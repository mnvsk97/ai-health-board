import "dotenv/config";
import { Stagehand } from "@browserbasehq/stagehand";

const url = process.argv[2];
if (!url) {
  process.stderr.write(JSON.stringify({ error: "Usage: node stagehand_raw_extract.mjs <url>" }));
  process.exit(1);
}

function requireEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing env: ${name}`);
  return value;
}

const provider = process.env.STAGEHAND_PROVIDER || "anthropic";
const modelName = process.env.STAGEHAND_MODEL || "anthropic/claude-3-5-sonnet";
const apiKey = process.env.STAGEHAND_MODEL_API_KEY || process.env.ANTHROPIC_API_KEY;

async function main() {
  const stagehand = new Stagehand({
    env: "BROWSERBASE",
    apiKey: requireEnv("BROWSERBASE_API_KEY"),
    projectId: requireEnv("BROWSERBASE_PROJECT_ID"),
    model: { modelName, apiKey },
    verbose: 0,  // Disable logging
    logger: () => {},  // Suppress all logs
  });

  try {
    await stagehand.init();
    const page = stagehand.context.pages()[0];

    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });

    // Wait a bit for dynamic content
    await page.waitForTimeout(2000);

    // Get text content
    const textContent = await page.evaluate(() => {
      // Remove script and style elements
      const clone = document.body.cloneNode(true);
      clone.querySelectorAll("script, style, nav, footer, header").forEach(el => el.remove());
      return clone.innerText || clone.textContent || "";
    });

    // Get page title
    const title = await page.title();

    console.log(JSON.stringify({
      url,
      title,
      content: textContent.trim(),
      content_length: textContent.length,
    }));

  } catch (err) {
    console.log(JSON.stringify({
      url,
      error: err.message,
      content: "",
      content_length: 0,
    }));
  } finally {
    await stagehand.close();
  }
}

main();
