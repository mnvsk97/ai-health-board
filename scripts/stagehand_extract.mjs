import "dotenv/config";

import crypto from "node:crypto";
import fs from "node:fs/promises";

import { Stagehand } from "@browserbasehq/stagehand";
import { z } from "zod";

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    const value = argv[i + 1];
    if (key?.startsWith("--")) {
      args[key.slice(2)] = value;
      i += 1;
    }
  }
  return args;
}

function requireEnv(name, fallback = []) {
  const value = process.env[name] || fallback.map((key) => process.env[key]).find(Boolean);
  if (!value) {
    const tried = [name, ...fallback].join(", ");
    throw new Error(`Missing required env var (tried: ${tried})`);
  }
  return value;
}

function computeHash(title, recommendations) {
  const payload = `${title || ""}|${(recommendations || []).join("|")}`;
  return crypto.createHash("sha256").update(payload).digest("hex");
}

function resolveModelName(rawModelName, provider) {
  if (rawModelName) {
    if (rawModelName.startsWith("openai-main/")) {
      return `openai/${rawModelName.replace("openai-main/", "")}`;
    }
    if (rawModelName.includes("/")) {
      return rawModelName;
    }
    return `${provider}/${rawModelName}`;
  }
  if (provider === "anthropic") {
    return "anthropic/claude-3-5-sonnet";
  }
  return "openai/gpt-4o-mini";
}

function resolveBaseURL(baseURL) {
  if (!baseURL) {
    return undefined;
  }
  const trimmed = baseURL.replace(/\/+$/, "");
  if (trimmed.endsWith("/v1")) {
    return trimmed;
  }
  return `${trimmed}/v1`;
}

function buildStagehandModelConfig(provider) {
  const modelName = resolveModelName(process.env.STAGEHAND_MODEL, provider);
  if (provider === "anthropic") {
    return {
      modelName,
      apiKey: requireEnv("STAGEHAND_MODEL_API_KEY", ["ANTHROPIC_API_KEY"]),
      baseURL: resolveBaseURL(
        process.env.STAGEHAND_MODEL_BASE_URL || process.env.ANTHROPIC_BASE_URL
      ),
    };
  }
  return {
    modelName,
    apiKey: requireEnv(
      "STAGEHAND_MODEL_API_KEY",
      provider === "anthropic" ? ["ANTHROPIC_API_KEY"] : ["OPENAI_API_KEY"]
    ),
    baseURL: resolveBaseURL(
      process.env.STAGEHAND_MODEL_BASE_URL ||
        (provider === "anthropic" ? process.env.ANTHROPIC_BASE_URL : process.env.OPENAI_BASE_URL)
    ),
  };
}

async function main() {
  const args = parseArgs(process.argv);
  const url = args.url;
  const outputPath = args.out || "data/extracted_guidelines.json";
  if (!url) {
    throw new Error("Usage: node scripts/stagehand_extract.mjs --url <url> --out <path>");
  }

  const provider = process.env.STAGEHAND_PROVIDER || "openai";
  const stagehand = new Stagehand({
    env: "BROWSERBASE",
    apiKey: requireEnv("BROWSERBASE_API_KEY"),
    projectId: requireEnv("BROWSERBASE_PROJECT_ID"),
    model: buildStagehandModelConfig(provider),
  });

  try {
    await stagehand.init();
    const page = stagehand.context.pages()[0];
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });

    // Wait for content to render
    await page.waitForTimeout(2000);

    // Get page title as fallback
    const pageTitle = await page.title();

    const GuidelineSchema = z.object({
      title: z.string().default(""),
      condition: z.string().default(""),
      urgency: z.enum(["emergent", "conditionally_emergent", "non_emergent"]).default("non_emergent"),
      red_flags: z.array(z.string()).default([]),
      recommendations: z.array(z.string()).default([]),
      last_updated: z.string().nullable().optional(),
    });

    const result = await stagehand.extract({
      instruction: `Extract healthcare/clinical information from this page.
        - title: The main heading or title of the page/guideline
        - condition: The medical condition, disease, or health topic covered
        - urgency: How urgent is this condition - emergent (life-threatening), conditionally_emergent (may need quick attention), or non_emergent (routine)
        - red_flags: List of warning signs, symptoms, or situations that need immediate attention
        - recommendations: Key recommendations, guidelines, or action items from the content
        - last_updated: When the content was last updated (if visible)

        If information is not available, use empty values.`,
      schema: GuidelineSchema,
    });

    // Use page title as fallback if extraction got empty title
    const title = result.title || pageTitle || "Untitled";

    // Also get raw text content for the ADK pipeline's LLM to process
    const rawContent = await page.evaluate(() => {
      const clone = document.body.cloneNode(true);
      clone.querySelectorAll("script, style, nav, footer, header, aside").forEach(el => el.remove());
      return (clone.innerText || clone.textContent || "").trim().substring(0, 50000);
    });

    const guideline = {
      ...result,
      title,
      raw_content: rawContent,
      source_url: url,
      hash: computeHash(title, result.recommendations),
      extracted_at: Date.now() / 1000,
    };

    await fs.writeFile(outputPath, JSON.stringify([guideline], null, 2), "utf-8");
    console.log(`Wrote guideline to ${outputPath}`);
  } finally {
    await stagehand.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
