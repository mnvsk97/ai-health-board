# Data Storage Architecture

This document describes how raw data and guidelines are stored in the AI Health Board system.

## Overview

The system uses **Redis** as the primary data store for:
- Extracted clinical guidelines
- Generated test scenarios
- Test run data and transcripts
- Vector embeddings for semantic search
- Compliance tracking

## Storage Backend

### Redis Configuration

```python
# Environment variables
REDIS_CLOUD_HOST=<hostname>
REDIS_CLOUD_PORT=<port>
REDIS_CLOUD_PASSWORD=<password>

# Fallback to in-memory storage for testing
REDIS_FALLBACK=1
```

### Two Client Modes

1. **String Client** (`decode_responses=True`) - For JSON data storage
2. **Binary Client** (`decode_responses=False`) - For vector embeddings

---

## Data Models

### ExtractedGuideline

Raw guideline data extracted from clinical sources (CDC, HHS, etc.).

```python
class ExtractedGuideline(BaseModel):
    source_url: str                    # Original URL
    title: str                         # Guideline title
    condition: str                     # Medical condition covered
    urgency: Literal["emergent", "conditionally_emergent", "non_emergent"]
    red_flags: list[str]               # Warning signs requiring immediate care
    recommendations: list[str]         # Clinical recommendations
    last_updated: str | None           # Source's last update date
    hash: str                          # SHA-256 hash for change detection
    extracted_at: float                # Unix timestamp of extraction
```

**Example:**
```json
{
  "source_url": "https://www.cdc.gov/vaccines-children/about/index.html",
  "title": "About Vaccines for Your Children",
  "condition": "childhood immunization",
  "urgency": "non_emergent",
  "red_flags": [
    "serious allergic reaction",
    "severe chronic medical condition"
  ],
  "recommendations": [
    "vaccinate children according to the recommended schedule",
    "get vaccinated even if sick with a mild illness"
  ],
  "last_updated": "August 9, 2024",
  "hash": "a1b2c3d4e5f6...",
  "extracted_at": 1706745600.0
}
```

### Scenario

Generated test scenario based on extracted guidelines.

```python
class Scenario(BaseModel):
    scenario_id: str                   # Unique ID (e.g., "sc_abc123")
    title: str                         # Scenario title
    description: str                   # Full scenario description
    source_type: Literal["bench", "web", "trace", "performance"]
    source_url: str | None             # Source guideline URL
    state: str | None                  # US state if applicable
    specialty: str | None              # Medical specialty
    rubric_criteria: list[RubricCriterion]  # Evaluation criteria
    clinician_approved: bool           # Approval status
```

### Guideline (Compliance Tracking)

Metadata for compliance monitoring.

```python
class Guideline(BaseModel):
    guideline_id: str
    source_url: str
    state: str | None
    specialty: str | None
    version: str
    hash: str                          # Content hash for change detection
    last_checked: float                # Last verification timestamp
```

---

## Redis Key Patterns

### Guidelines Storage

| Key Pattern | Type | Description |
|-------------|------|-------------|
| `guideline:extracted:<url_hash>` | String (JSON) | Extracted guideline content |
| `guideline:url_index:<url_hash>` | String (JSON) | URL to key mapping |
| `compliance:guideline:<id>` | String (JSON) | Compliance metadata |

**URL Hashing:**
```python
def _url_to_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]
```

### Scenarios Storage

| Key Pattern | Type | Description |
|-------------|------|-------------|
| `scenario:<scenario_id>` | String (JSON) | Basic scenario data |
| `scenario:<scenario_id>` | Hash | Scenario with vector embedding |

**Note:** Scenarios can be stored in two formats:
- **String (JSON)**: Simple storage via `save_scenario()`
- **Hash**: With embeddings via `save_scenario_with_embedding()`

### Run & Transcript Storage

| Key Pattern | Type | Description |
|-------------|------|-------------|
| `run:<run_id>` | String (JSON) | Test run metadata |
| `transcript:<run_id>` | List | Ordered transcript entries |
| `transcript_entry:<run_id>:<idx>` | Hash | Entry with embedding |
| `grading:<run_id>` | String (JSON) | Grading results |
| `checkpoint:<run_id>` | String (JSON) | Run checkpoint (TTL: 1 hour) |

### Attack & Vector Stats

| Key Pattern | Type | Description |
|-------------|------|-------------|
| `attack_plan:<scenario_id>:<rubric_hash>` | String (JSON) | Cached attack plans |
| `vector_stats:<vector>` | Hash | Attack vector effectiveness stats |

### Compliance Status

| Key Pattern | Type | Description |
|-------------|------|-------------|
| `compliance:status:<target_id>` | String (JSON) | Target compliance status |

### Pub/Sub & Audit

| Key Pattern | Type | Description |
|-------------|------|-------------|
| `run_events:<run_id>` | Pub/Sub Channel | Real-time run events |
| `audit:<run_id>` | Stream | Audit log entries |

---

## Vector Search Indexes

Two RediSearch indexes are created for semantic search:

### scenario_idx

```python
VectorField("embedding", "HNSW", {
    "TYPE": "FLOAT32",
    "DIM": 3072,  # Configurable via EMBEDDING_DIMENSIONS
    "DISTANCE_METRIC": "COSINE"
})
TagField("scenario_id")
TagField("source_type")
NumericField("created_at")
```

### transcript_idx

```python
VectorField("embedding", "HNSW", {...})
TagField("run_id")
TagField("role")
NumericField("timestamp")
```

---

## Storage Functions

### Extracted Guidelines

```python
# Save an extracted guideline
save_extracted_guideline(guideline: dict) -> None

# Retrieve by URL
get_extracted_guideline_by_url(url: str) -> dict | None

# List all extracted guidelines
list_extracted_guidelines() -> list[dict]
```

### Scenarios

```python
# Basic save (JSON string)
save_scenario(scenario: Scenario) -> None

# Save with embedding (Hash with vector)
save_scenario_with_embedding(scenario: Scenario) -> None

# List all scenarios
list_scenarios() -> list[Scenario]

# Semantic search
search_similar_scenarios(query: str, k: int = 5) -> list[tuple[Scenario, float]]
```

### Compliance

```python
# Save guideline metadata
save_guideline(guideline: Guideline) -> None

# Get guideline metadata
get_guideline(guideline_id: str) -> Guideline | None

# Set compliance status
set_compliance_status(status: ComplianceStatus) -> None

# Get compliance status
get_compliance_status(target_id: str) -> ComplianceStatus | None
```

---

## Change Detection

The system uses content hashing to detect new or updated guidelines:

```python
class ChangeDetector:
    def compute_hash(self, guideline: dict) -> str:
        """SHA-256 hash of title + recommendations."""
        title = guideline.get("title", "")
        recommendations = guideline.get("recommendations", [])
        content = f"{title}|{'|'.join(recommendations)}"
        return hashlib.sha256(content.encode()).hexdigest()

    def is_new_or_updated(self, guideline: dict) -> tuple[bool, str]:
        """Returns (is_changed, reason: 'new'|'updated'|'unchanged')"""
        existing = get_extracted_guideline_by_url(guideline["source_url"])
        if not existing:
            return True, "new"
        if existing.get("hash") != self.compute_hash(guideline):
            return True, "updated"
        return False, "unchanged"
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Source URL (CDC, HHS, etc.)                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  HTTP Fetch + LLM Extraction                                    │
│  - Fetch HTML content                                           │
│  - Convert to plain text                                        │
│  - Extract structured data via LLM                              │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Change Detection                                               │
│  - Compute content hash                                         │
│  - Compare with stored version                                  │
│  - Determine: new / updated / unchanged                         │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Redis Storage                                                  │
│  - guideline:extracted:<hash> → ExtractedGuideline              │
│  - guideline:url_index:<hash> → URL mapping                     │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Scenario Generation                                            │
│  - LLM generates test scenario from guideline                   │
│  - Creates rubric criteria                                      │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Redis Storage                                                  │
│  - scenario:<id> → Scenario                                     │
│  - (optional) scenario:<id> → Hash with embedding               │
└─────────────────────────────────────────────────────────────────┘
```

---

## CLI Commands

```bash
# Extract a guideline and generate scenario
uv run python scripts/discover_guidelines.py --url "https://..."

# Dry run (no storage)
uv run python scripts/discover_guidelines.py --url "https://..." --dry-run

# Verify stored data
uv run python -c "
from ai_health_board import redis_store
for g in redis_store.list_extracted_guidelines():
    print(g['title'])
"
```

---

## Testing Mode

Set `REDIS_FALLBACK=1` to use in-memory storage instead of Redis:

```bash
REDIS_FALLBACK=1 uv run python scripts/discover_guidelines.py --url "..."
```

This uses a Python dictionary (`_MEM_STORE`) for all storage operations, useful for testing without a Redis connection.
