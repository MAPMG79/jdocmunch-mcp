# Token Savings: jDocMunch MCP

## Why This Exists

AI agents waste tokens when they must read entire documentation files to find a specific section, answer a question, or locate a configuration reference.
jDocMunch indexes documentation once and allows agents to retrieve **exact sections on demand**, eliminating unnecessary context loading.

---

## Example Scenario

**Documentation set:** Framework docs (50+ Markdown files, hundreds of sections)
**Task:** Find the authentication configuration section

| Approach         | Tokens Consumed | Process                                      |
| ---------------- | --------------- | -------------------------------------------- |
| Raw file loading | ~12,000 tokens  | Open multiple files, scan for relevant parts |
| jDocMunch MCP    | ~400 tokens     | `search_sections` → `get_section`            |

**Savings:** ~96.7%

---

## Typical Savings by Task

| Task                          | Raw Approach    | With jDocMunch  | Savings |
| ----------------------------- | --------------- | --------------- | ------- |
| Find a specific topic         | ~12,000 tokens  | ~400 tokens     | ~97%    |
| Browse doc structure          | ~40,000 tokens  | ~800 tokens     | ~98%    |
| Read one section              | ~12,000 tokens  | ~300 tokens     | ~97.5%  |
| Explore a doc set             | ~100,000 tokens | ~2,000 tokens   | ~98%    |

---

## Scaling Impact

| Queries | Raw Tokens  | Indexed Tokens | Savings |
| ------- | ----------- | -------------- | ------- |
| 10      | 120,000     | ~4k            | ~97%    |
| 100     | 1,200,000   | ~40k           | ~97%    |
| 1,000   | 12,000,000  | ~400k          | ~97%    |

---

## Key Insight

jDocMunch shifts the workflow from:

**"Read all docs to find a section"**
to
**"Find the section, then read only that."**

---

## Live Token Savings Counter

Every retrieval and search tool response includes real-time savings data in the `_meta` field:

```json
"_meta": {
  "tokens_saved": 1840,
  "total_tokens_saved": 94320,
  "cost_avoided": {
    "claude_opus": 0.0276,
    "gpt5_latest": 0.0184
  },
  "total_cost_avoided": {
    "claude_opus": 1.4148,
    "gpt5_latest": 0.9432
  }
}
```

- **`tokens_saved`**: Tokens saved by the current call (raw doc bytes of matched documents vs summary-only response bytes ÷ 4)
- **`total_tokens_saved`**: Cumulative total across all calls, persisted to `~/.doc-index/_savings.json`
- **`cost_avoided`**: Dollar value of tokens saved this call (Claude Opus 4.6 at $15/1M, GPT-5 at $10/1M)
- **`total_cost_avoided`**: Cumulative cost avoided across all calls

Network failures during telemetry reporting are silent and never affect tool performance.

---
