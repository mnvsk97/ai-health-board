# Hackathon Implementation Plan: Sponsor-Enhanced Scenario Pipeline

> Automatic scenario generation + self-evolving AI pen-testing with full sponsor integration

## Sponsor Products & Their Roles

| Sponsor | Product | Integration Point |
|---------|---------|-------------------|
| **Redis** | Redis Cloud + Agent Skills MCP | Attack plan cache, turn state, vector effectiveness, pub/sub |
| **W&B** | Weave + W&B Inference API | LLM calls via inference API, full observability via Weave |
| **Browserbase** | Stagehand | AI-powered discovery with act/extract/observe |
| **Pipecat** | Pipecat + Pipecat Cloud | Voice-to-voice testing, managed deployment |

---

## Key Decisions

- **Redis**: Use **Redis Cloud** (not Upstash) + install **redis/agent-skills** MCP for development assistance
- **W&B**: Use **W&B Inference API** for all LLM calls + **Weave** for tracing
- **Pipecat**: Deploy voice worker to **Pipecat Cloud** (managed platform)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  1. DISCOVERY (Browserbase + Stagehand)                         │
│     CDC, NIH → act(), extract() → Guidelines                   │
│     Traced with Weave                                           │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. SCENARIO GENERATION (W&B Inference + Weave)                 │
│     Guidelines → Scenarios with Rubrics                         │
│     Redis Cloud: Semantic cache for LLM calls                   │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. ATTACK PLANNING (core-agents + Redis + Weave)               │
│     Scenario → AttackPlan with vectors + phases                 │
│     Redis Cloud: Sub-ms cache, vector effectiveness             │
│     W&B Inference: Model serving for plan generation            │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. ADAPTIVE TESTING (Pipecat Cloud + Redis + Weave)            │
│     Voice-to-voice with real-time pivots                        │
│     Redis Cloud: Turn state checkpoints, pub/sub progress       │
│     Weave: Trace every turn decision                            │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. GRADING (W&B Inference + Weave Evaluation)                  │
│     Transcript → Rubric evaluation                              │
│     Weave: Evaluation framework for quality metrics             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup: Redis Agent Skills MCP

Install Redis agent-skills for development assistance:

```bash
# Install Redis agent skills for Claude Code
npx @anthropic/skills add redis/agent-skills

# This provides:
# - Redis development best practices
# - Data structure recommendations
# - Query engine patterns
# - Vector search guidance
# - Caching strategies
# - Performance optimization
```

The MCP skills will help the coding agent build Redis integrations correctly.

---

## Project Structure

```
hackathon/
├── packages/
│   ├── redis-client/                  # Redis Cloud integration
│   │   └── src/
│   │       ├── client.ts              # Redis Cloud client (ioredis)
│   │       ├── attack-plan-cache.ts   # Plan caching (sub-ms)
│   │       ├── turn-state-store.ts    # Checkpoint persistence
│   │       ├── vector-effectiveness.ts # Cross-run learning
│   │       ├── semantic-cache.ts      # LLM response cache
│   │       └── pubsub.ts              # Real-time progress
│   │
│   ├── wandb-inference/               # W&B Inference + Weave
│   │   └── src/
│   │       ├── client.ts              # W&B Inference API client
│   │       ├── weave-init.ts          # Weave initialization
│   │       ├── traced-llm.ts          # Weave-traced LLM wrapper
│   │       └── evaluation.ts          # Weave evaluation framework
│   │
│   ├── stagehand-discovery/           # Web discovery agent
│   │   └── src/
│   │       ├── browser.ts             # Browserbase setup
│   │       ├── agent.ts               # Discovery orchestrator
│   │       └── extractors/
│   │           ├── cdc.ts             # CDC guidelines (Zod schemas)
│   │           └── nih.ts             # NIH clinical tables
│   │
│   └── pipecat-tester/                # Voice-to-voice tester
│       └── src/
│           ├── pipeline.ts            # Pipecat pipeline definition
│           ├── cloud-deploy.ts        # Pipecat Cloud deployment
│           └── processors/
│               ├── adaptive-pen-tester.ts  # Frame processor
│               └── transcript-logger.ts    # Weave-traced logging
│
├── supabase/functions/
│   ├── discover-guidelines/           # Stagehand discovery endpoint
│   └── generate-scenarios/            # Knowledge → Scenarios
│
└── pipecat-cloud/                     # Pipecat Cloud worker config
    ├── agent.py                       # Voice agent definition
    ├── requirements.txt
    └── pipecat.toml                   # Cloud config
```

---

## Redis Cloud Integration

### Client Setup (ioredis)

```typescript
// packages/redis-client/src/client.ts
import Redis from 'ioredis';

export const redis = new Redis({
  host: process.env.REDIS_CLOUD_HOST,
  port: parseInt(process.env.REDIS_CLOUD_PORT || '6379'),
  password: process.env.REDIS_CLOUD_PASSWORD,
  tls: {}, // Required for Redis Cloud
});
```

### Attack Plan Cache

```typescript
// packages/redis-client/src/attack-plan-cache.ts
import { redis } from './client';

export class AttackPlanCache {
  private prefix = 'attack_plan:';
  private ttl = 86400; // 24 hours

  async get(scenarioId: string, rubricHash: string): Promise<AttackPlan | null> {
    const key = `${this.prefix}${scenarioId}:${rubricHash}`;
    const cached = await redis.get(key);

    if (cached) {
      // Track cache hit for analytics
      await redis.hincrby('cache_stats', 'attack_plan_hits', 1);
      return JSON.parse(cached);
    }

    await redis.hincrby('cache_stats', 'attack_plan_misses', 1);
    return null;
  }

  async set(scenarioId: string, plan: AttackPlan): Promise<void> {
    const key = `${this.prefix}${scenarioId}:${plan.rubric_hash}`;
    await redis.setex(key, this.ttl, JSON.stringify(plan));
  }
}
```

### Turn State Persistence (Checkpoints)

```typescript
// packages/redis-client/src/turn-state-store.ts
export class TurnStateStore {
  private prefix = 'checkpoint:';
  private ttl = 3600; // 1 hour

  async checkpoint(
    scenarioRunId: string,
    turnState: TurnState,
    transcript: TranscriptEntry[]
  ): Promise<void> {
    const key = `${this.prefix}${scenarioRunId}`;
    await redis.setex(key, this.ttl, JSON.stringify({
      turnState,
      transcript,
      checkpointedAt: Date.now(),
    }));
  }

  async restore(scenarioRunId: string): Promise<{
    turnState: TurnState;
    transcript: TranscriptEntry[];
  } | null> {
    const data = await redis.get(`${this.prefix}${scenarioRunId}`);
    return data ? JSON.parse(data) : null;
  }
}
```

### Vector Effectiveness (Cross-Run Learning)

```typescript
// packages/redis-client/src/vector-effectiveness.ts
export class VectorEffectivenessTracker {
  async recordAttempt(vectorCategory: string, wasEffective: boolean): Promise<void> {
    const key = `vector_stats:${vectorCategory}`;
    await redis.hincrby(key, 'attempted', 1);
    if (wasEffective) {
      await redis.hincrby(key, 'effective', 1);
    }
  }

  async getEffectivenessRate(vectorCategory: string): Promise<number> {
    const key = `vector_stats:${vectorCategory}`;
    const [attempted, effective] = await Promise.all([
      redis.hget(key, 'attempted'),
      redis.hget(key, 'effective'),
    ]);

    const a = parseInt(attempted || '0');
    const e = parseInt(effective || '0');
    return a > 0 ? e / a : 0.5; // Default 50% if no data
  }

  // Prioritize vectors by effectiveness for attack planning
  async getRankedVectors(): Promise<string[]> {
    const vectors = [
      'symptom_minimization', 'symptom_escalation', 'emotional_manipulation',
      'urgency_manipulation', 'authority_challenge', 'social_engineering',
    ];

    const rates = await Promise.all(
      vectors.map(async (v) => ({ vector: v, rate: await this.getEffectivenessRate(v) }))
    );

    return rates.sort((a, b) => b.rate - a.rate).map(r => r.vector);
  }
}
```

### Real-time Pub/Sub

```typescript
// packages/redis-client/src/pubsub.ts
export class TestProgressPubSub {
  private publisher = redis.duplicate();

  async publishProgress(testRunId: string, event: TestEvent): Promise<void> {
    await this.publisher.publish(
      `test_progress:${testRunId}`,
      JSON.stringify({ ...event, timestamp: Date.now() })
    );
  }
}
```

---

## W&B Inference + Weave Integration

### Inference API Client

```typescript
// packages/wandb-inference/src/client.ts
import * as weave from 'weave';

const WANDB_INFERENCE_URL = 'https://api.wandb.ai/v1/inference';

export class WandBInferenceClient {
  private apiKey: string;

  constructor() {
    this.apiKey = process.env.WANDB_API_KEY!;
  }

  @weave.op({ name: 'wandb_inference.chat' })
  async chat(
    model: string,
    messages: Array<{ role: string; content: string }>,
    options: { temperature?: number; maxTokens?: number } = {}
  ): Promise<string> {
    const response = await fetch(`${WANDB_INFERENCE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        messages,
        temperature: options.temperature ?? 0.7,
        max_tokens: options.maxTokens ?? 1000,
      }),
    });

    const data = await response.json();
    return data.choices[0].message.content;
  }

  @weave.op({ name: 'wandb_inference.chat_json' })
  async chatJson<T>(
    model: string,
    messages: Array<{ role: string; content: string }>,
    options: { temperature?: number; maxTokens?: number } = {}
  ): Promise<T> {
    const response = await this.chat(model, messages, options);
    return JSON.parse(response) as T;
  }
}
```

### Weave Initialization

```typescript
// packages/wandb-inference/src/weave-init.ts
import * as weave from 'weave';

export function initWeave() {
  weave.init('preclinical-hackathon');
}

// Decorator for tracing functions
export const traced = weave.op;
```

### Traced LLM Wrapper for Core-Agents

```typescript
// packages/wandb-inference/src/traced-llm.ts
import * as weave from 'weave';
import { WandBInferenceClient } from './client';
import type { LLMClient } from '@preclinical/core-agents';

const wandb = new WandBInferenceClient();

// LLMClient adapter for core-agents that uses W&B Inference
export const tracedLLMClient: LLMClient = {
  @weave.op({ name: 'llm_client.chat_completion' })
  async chatCompletion(
    model: string,
    messages: Array<{ role: string; content: string }>,
    options?: { maxTokens?: number; temperature?: number; responseFormat?: { type: string } }
  ): Promise<string> {
    weave.setAttributes({
      'llm.model': model,
      'llm.message_count': messages.length,
      'llm.provider': 'wandb_inference',
    });

    return await wandb.chat(model, messages, {
      temperature: options?.temperature,
      maxTokens: options?.maxTokens,
    });
  }
};
```

### Weave Evaluation Framework

```typescript
// packages/wandb-inference/src/evaluation.ts
import * as weave from 'weave';

// Scorer for grading accuracy
export const gradingAccuracy = weave.scorer(
  function gradingAccuracy(output: GradingOutput, expected: Record<string, boolean>): number {
    let correct = 0;
    let total = 0;

    for (const evaluation of output.evaluations) {
      const key = `criterion_${evaluation.criterion_index}`;
      if (key in expected) {
        const expectedMet = expected[key];
        const actualMet = evaluation.decision === 'MET';
        if (expectedMet === actualMet) correct++;
        total++;
      }
    }

    return total > 0 ? correct / total : 0;
  }
);

// Run evaluation on a dataset
export async function runEvaluation(
  dataset: Array<{ scenario: Scenario; transcript: TranscriptEntry[]; expected: Record<string, boolean> }>,
  graderFn: (scenario: Scenario, transcript: TranscriptEntry[]) => Promise<GradingOutput>
) {
  const evaluation = new weave.Evaluation({
    name: 'grading_evaluation',
    dataset,
    scorers: [gradingAccuracy],
  });

  return await evaluation.evaluate(async (input) => {
    return await graderFn(input.scenario, input.transcript);
  });
}
```

---

## Stagehand Discovery Agent

### CDC Guidelines Extractor

```typescript
// packages/stagehand-discovery/src/extractors/cdc.ts
import { Stagehand } from '@browserbasehq/stagehand';
import { z } from 'zod';
import * as weave from 'weave';

const GuidelineSchema = z.object({
  title: z.string(),
  condition: z.string(),
  urgency: z.enum(['emergent', 'conditionally_emergent', 'non_emergent']),
  keyRecommendations: z.array(z.string()),
  redFlags: z.array(z.string()),
  referralCriteria: z.string(),
  lastUpdated: z.string().optional(),
  sourceUrl: z.string(),
});

export const extractCDCGuidelines = weave.op(
  async function extractCDCGuidelines(stagehand: Stagehand): Promise<z.infer<typeof GuidelineSchema>[]> {
    const guidelines: z.infer<typeof GuidelineSchema>[] = [];

    // Navigate to CDC clinical guidance
    await stagehand.page.goto('https://www.cdc.gov/clinical-guidance/index.html');

    // Use observe() to understand page structure
    const pageInfo = await stagehand.observe({
      instruction: 'Describe the layout and find clinical guideline links',
    });

    weave.setAttributes({ 'page.observation': pageInfo });

    // Use act() to navigate to a specific guideline
    await stagehand.act({
      action: 'Click on the first clinical guideline link about emergency care',
    });

    await stagehand.page.waitForLoadState('networkidle');

    // Use extract() with Zod schema
    const extracted = await stagehand.extract({
      instruction: `
        Extract clinical guideline information:
        1. Condition name
        2. When to refer to emergency care (red flags)
        3. Key recommendations
        4. Urgency level (emergent if life-threatening)
      `,
      schema: GuidelineSchema,
    });

    if (extracted) {
      guidelines.push({ ...extracted, sourceUrl: stagehand.page.url() });
    }

    return guidelines;
  },
  { name: 'stagehand.extract_cdc' }
);
```

---

## Pipecat Cloud Deployment

### Voice Agent Definition

```python
# pipecat-cloud/agent.py
from pipecat.pipeline import Pipeline
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.transports.services.daily import DailyTransport
from pipecat.processors.frame_processor import FrameProcessor
import os
import aiohttp
import weave

weave.init('preclinical-hackathon')

class AdaptivePenTesterProcessor(FrameProcessor):
    """Adaptive pen tester that evolves attack strategy based on target responses."""

    def __init__(self, attack_plan: dict, scenario: dict, redis_url: str):
        super().__init__()
        self.attack_plan = attack_plan
        self.scenario = scenario
        self.turn_state = self._init_turn_state()
        self.redis_url = redis_url

    def _init_turn_state(self):
        return {
            'current_turn': 0,
            'current_vector_index': 0,
            'vectors_attempted': [],
            'vectors_effective': [],
            'pivot_history': [],
        }

    @weave.op()
    async def process_frame(self, frame):
        if frame.type == 'transcription':
            target_response = frame.text

            # Generate next attack message via W&B Inference
            next_message = await self._generate_attack_message(target_response)

            # Checkpoint state to Redis
            await self._checkpoint_state()

            return TextFrame(next_message)

        return frame

    async def _generate_attack_message(self, target_response: str) -> str:
        # Call W&B Inference API for next attack
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.wandb.ai/v1/inference/chat/completions',
                headers={'Authorization': f'Bearer {os.environ["WANDB_API_KEY"]}'},
                json={
                    'model': 'gpt-4o-mini',
                    'messages': self._build_messages(target_response),
                }
            ) as resp:
                data = await resp.json()
                return data['choices'][0]['message']['content']

    async def _checkpoint_state(self):
        # Save to Redis Cloud
        import redis
        r = redis.from_url(self.redis_url)
        r.setex(
            f'checkpoint:{self.scenario["run_id"]}',
            3600,
            json.dumps(self.turn_state)
        )


def create_pipeline(attack_plan: dict, scenario: dict) -> Pipeline:
    transport = DailyTransport(
        room_url=os.environ['DAILY_ROOM_URL'],
        token=os.environ['DAILY_TOKEN'],
        bot_name='PenTester',
    )

    stt = DeepgramSTTService(api_key=os.environ['DEEPGRAM_API_KEY'])
    tts = ElevenLabsTTSService(
        api_key=os.environ['ELEVENLABS_API_KEY'],
        voice_id='Rachel',
    )
    pen_tester = AdaptivePenTesterProcessor(
        attack_plan,
        scenario,
        os.environ['REDIS_CLOUD_URL'],
    )

    return Pipeline([
        transport.input(),
        stt,
        pen_tester,
        tts,
        transport.output(),
    ])
```

### Pipecat Cloud Config

```toml
# pipecat-cloud/pipecat.toml
[agent]
name = "preclinical-pen-tester"
entrypoint = "agent:create_pipeline"

[resources]
cpu = "1"
memory = "2Gi"

[scaling]
min_instances = 0
max_instances = 10

[secrets]
WANDB_API_KEY = { from = "env" }
DEEPGRAM_API_KEY = { from = "env" }
ELEVENLABS_API_KEY = { from = "env" }
REDIS_CLOUD_URL = { from = "env" }
```

---

## Environment Variables

```bash
# Redis Cloud
REDIS_CLOUD_HOST=redis-xxxxx.c1.us-east-1-2.ec2.cloud.redislabs.com
REDIS_CLOUD_PORT=xxxxx
REDIS_CLOUD_PASSWORD=your-password

# W&B (Inference + Weave)
WANDB_API_KEY=your-wandb-key
WEAVE_PROJECT=preclinical-hackathon

# Browserbase + Stagehand
BROWSERBASE_API_KEY=your-browserbase-key
BROWSERBASE_PROJECT_ID=your-project-id

# Pipecat Voice
DEEPGRAM_API_KEY=your-deepgram-key
ELEVENLABS_API_KEY=your-elevenlabs-key
ELEVENLABS_VOICE_ID=Rachel

# Pipecat Cloud
PIPECAT_CLOUD_API_KEY=your-pipecat-cloud-key
DAILY_ROOM_URL=https://your-domain.daily.co/room
DAILY_TOKEN=your-daily-token
```

---

## Three-Day Schedule

### Day 1: Foundation & Core Integrations

**Morning**
- [ ] Set up Redis Cloud account, get connection details
- [ ] Install Redis agent-skills MCP: `npx @anthropic/skills add redis/agent-skills`
- [ ] Create `redis-client` package with ioredis
- [ ] Set up W&B account, get API key
- [ ] Create `wandb-inference` package with client + Weave init

**Afternoon**
- [ ] Implement attack plan cache with Redis
- [ ] Implement W&B Inference client with Weave tracing
- [ ] Add tracing to existing attack planner in core-agents
- [ ] Create `stagehand-discovery` package
- [ ] Implement CDC extractor

**Deliverables:** Redis cache working, W&B traces visible, CDC discovery functional

### Day 2: Voice & Learning

**Morning**
- [ ] Implement turn state checkpoints in Redis
- [ ] Implement vector effectiveness tracking
- [ ] Add cross-run learning to attack planner
- [ ] Create `pipecat-tester` package

**Afternoon**
- [ ] Build AdaptivePenTesterProcessor for Pipecat
- [ ] Set up Pipecat Cloud deployment
- [ ] Test voice-to-voice conversation end-to-end
- [ ] Add Redis pub/sub for real-time progress

**Deliverables:** Conversation checkpoints, cross-run learning, voice testing on Pipecat Cloud

### Day 3: Integration & Demo

**Morning**
- [ ] Create discovery → scenario generation flow
- [ ] Add Weave evaluation framework
- [ ] End-to-end integration testing
- [ ] Fix any bugs

**Afternoon**
- [ ] Build demo script
- [ ] Practice demo
- [ ] Record backup video
- [ ] Prepare slides

**Deliverables:** Complete demo flow, all sponsors meaningfully integrated

---

## Demo Script (10 min)

1. **Discovery (2 min)**
   - Show Stagehand navigating CDC in Browserbase dashboard
   - Show extracted guidelines in Weave trace

2. **Scenario Generation (2 min)**
   - Show W&B Inference call generating scenario
   - Show Redis semantic cache (hit on similar prompt)

3. **Attack Planning (2 min)**
   - Show Redis cache lookup (sub-ms)
   - Show vector prioritization from cross-run learning
   - Show attack plan in Weave trace

4. **Voice Test (3 min)**
   - Start Pipecat Cloud session
   - Show real-time transcript via Redis pub/sub
   - Point out pivot decision in Weave trace
   - Show turn state checkpoint in Redis

5. **Results (1 min)**
   - Show complete Weave trace tree
   - Show Weave evaluation metrics
   - Highlight all sponsor integrations

---

## Verification

### Success Criteria
- [ ] Redis: Attack plan cache <5ms lookup
- [ ] Redis: Turn checkpoints persist, can resume after restart
- [ ] Redis: Vector effectiveness updates across runs
- [ ] W&B Inference: All LLM calls go through W&B API
- [ ] Weave: Full trace tree with pivots visible
- [ ] Stagehand: Extracts 3+ guidelines from CDC
- [ ] Pipecat Cloud: Completes 4-turn voice conversation
