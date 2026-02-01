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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForStableText(locator, settleMs, timeoutMs) {
  const start = Date.now();
  let lastText = "";
  let stableFor = 0;
  while (Date.now() - start < timeoutMs) {
    const text = (await locator.innerText()).trim();
    if (text === lastText) {
      stableFor += 250;
      if (stableFor >= settleMs) {
        return text;
      }
    } else {
      lastText = text;
      stableFor = 0;
    }
    await locator.page().waitForTimeout(250);
  }
  return (await locator.innerText()).trim();
}

async function main() {
  const args = parseArgs(process.argv);
  const url = args.url;
  const message = args.message;
  const inputSelector = args["input-selector"];
  const sendSelector = args["send-selector"];
  const responseSelector = args["response-selector"];
  const transcriptSelector = args["transcript-selector"];
  const timeoutMs = Number(args["timeout-ms"] || 45000);
  const settleMs = Number(args["settle-ms"] || 1500);

  if (!url || !message || !inputSelector || !responseSelector) {
    throw new Error(
      "Usage: node scripts/stagehand_chat_turn.mjs --url <url> --message <msg> " +
        "--input-selector <selector> --response-selector <selector> " +
        "[--send-selector <selector>] [--transcript-selector <selector>] " +
        "[--timeout-ms <ms>] [--settle-ms <ms>]"
    );
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
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: timeoutMs });
    await page.waitForSelector(inputSelector, { timeout: timeoutMs });

    await page.locator(inputSelector).fill(message);
    if (sendSelector) {
      await page.locator(sendSelector).click();
    } else {
      await page.keyboard.press("Enter");
    }

    await sleep(5000);

    let responseText = "";
    try {
      await page.waitForSelector(responseSelector, { timeout: timeoutMs });
      const responseLocator = page.locator(responseSelector).last();
      responseText = await waitForStableText(responseLocator, settleMs, timeoutMs);
    } catch (err) {
      const ResponseSchema = z.object({
        response_text: z.string(),
      });
      const responseResult = await stagehand.extract(
        "Extract the latest assistant response text from the chat UI.",
        ResponseSchema,
        { selector: transcriptSelector || undefined, timeout: timeoutMs }
      );
      responseText = responseResult.response_text || "";
    }

    const MessageSchema = z.object({
      role: z.string(),
      content: z.string(),
    });
    const TranscriptSchema = z.array(MessageSchema);

    const extractArgs = {
      instruction:
        "Extract the full chat transcript from the page. Return an array of messages " +
        "with role ('user' or 'assistant') and content (string).",
      schema: TranscriptSchema,
    };
    if (transcriptSelector) {
      extractArgs.selector = transcriptSelector;
    }
    const transcript = await stagehand.extract(
      extractArgs.instruction,
      extractArgs.schema,
      { selector: extractArgs.selector, timeout: timeoutMs }
    );

    const payload = {
      response_text: responseText,
      messages: transcript,
      timestamp: Date.now() / 1000,
    };
    console.log(JSON.stringify(payload));
  } finally {
    await stagehand.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
