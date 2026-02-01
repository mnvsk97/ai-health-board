import "dotenv/config";

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
  if (!url) {
    throw new Error("Usage: node scripts/stagehand_discover_chat.mjs --url <url>");
  }

  const provider = process.env.STAGEHAND_PROVIDER || "openai";
  const modelName = resolveModelName(process.env.STAGEHAND_MODEL, provider);
  console.log(
    JSON.stringify(
      {
        stagehand_provider: provider,
        stagehand_model: modelName,
        has_model_key: Boolean(process.env.STAGEHAND_MODEL_API_KEY),
        has_anthropic_key: Boolean(process.env.ANTHROPIC_API_KEY),
        has_openai_key: Boolean(process.env.OPENAI_API_KEY),
      },
      null,
      2
    )
  );
  const stagehand = new Stagehand({
    env: "BROWSERBASE",
    apiKey: requireEnv("BROWSERBASE_API_KEY"),
    projectId: requireEnv("BROWSERBASE_PROJECT_ID"),
    model: buildStagehandModelConfig(provider),
  });

  try {
    await stagehand.init();
    const page = stagehand.context.pages()[0];
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });

    await stagehand.act(
      "Close any modal, cookie banner, or popup blocking interaction if present."
    );
    await stagehand.act(
      "If there is a primary button to start chat (e.g., Get Started), click it."
    );
    await stagehand.act(
      "Type the message 'Hello' into the chat input and send it."
    );

    const schema = z.object({
      input_selector: z.string(),
      send_selector: z.string().optional(),
      response_selector: z.string(),
      transcript_selector: z.string().optional(),
      notes: z.string().optional(),
    });

    const result = await stagehand.extract({
      instruction:
        "Identify the chat UI selectors for this page. " +
        "Return CSS selectors for: input box where a user types, send button (optional), " +
        "assistant response message blocks, and the transcript container (optional). " +
        "Prefer stable selectors (data-testid, aria-label, role, or placeholder).",
      schema,
    });

    if (!result || result.pageText) {
      const fallback = await stagehand.observe(
        "Find the chat input box, send button, assistant message blocks, and transcript container. " +
          "Return concise CSS selectors for each."
      );
      console.log(JSON.stringify({ fallback_observe: fallback }, null, 2));
    }

    console.log(JSON.stringify(result, null, 2));
  } finally {
    await stagehand.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
