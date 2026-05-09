# AI News Agent Extended MVP Design

## Goal

Build an extended MVP for a local AI-news card-news agent. The agent should collect AI-related news, rank and deduplicate it, extract evidence-backed facts, generate Korean card-news copy, render PNG cards, and export review-friendly HTML artifacts.

## Scope

This design extends the existing script-based pipeline instead of replacing it. The current stages remain:

- `collect.py`: collect raw source items into `data/items.json`
- `cluster_rank.py`: cluster and rank items into `data/top_news.json`
- `card_writer.py`: generate card copy into `data/cards.json`
- `card_renderer.py`: render PNG images into `output/`
- `card_exporter.py`: export HTML into `output/cards.html`

The extended MVP adds execution orchestration, schema validation, source normalization, fact extraction, review output, and richer visual rendering.

Out of scope for this MVP:

- Hosted web application
- Database persistence
- Scheduled cloud deployment
- User account management
- Automatic social-media publishing

## Recommended Approach

Use a gradual extension approach. Keep the root scripts as user-facing entry points, add focused helper modules, and avoid a full package restructure until the pipeline is stable.

Create these new modules:

- `run_pipeline.py`: single command entry point for running pipeline stages
- `schemas.py`: validation helpers for item, ranked-news, fact, and card JSON shapes
- `source_utils.py`: URL/domain normalization and source trust helpers
- `fact_extractor.py`: evidence-backed fact extraction from ranked news
- `review_exporter.py`: human review HTML output with card text, facts, sources, and image previews
- `tests/`: network-free tests for validation, normalization, and card preparation

## Data Flow

The extended pipeline produces these artifacts:

1. `data/items.json`: raw collected items
2. `data/top_news.json`: selected ranked news clusters
3. `data/news_facts.json`: structured fact records for each selected news item
4. `data/cards.json`: generated card-news copy
5. `output/01.png` to `output/NN.png`: rendered card images
6. `output/cards.html`: shareable card gallery and text export
7. `output/review.html`: internal review page showing facts, sources, card copy, and images

`card_writer.py` should prefer `data/news_facts.json` when present. If facts are missing, it may fall back to the current top-news enrichment flow, but it should warn the user.

## Validation Rules

`schemas.py` should provide validation functions that raise `ValueError` with actionable messages:

- `validate_item(item)`: required raw item fields are present
- `validate_top_news_item(item)`: ranked news has score, title, summary, category, URL, and cluster
- `validate_fact_record(record)`: fact record has title, URL, fact list, evidence list, and confidence
- `validate_cards(data)`: card output has top-level metadata and valid card entries

Validation should run after each stage in `run_pipeline.py`.

## Source Quality

`source_utils.py` should normalize source URLs and classify domains:

- Resolve Google News redirect/RSS URLs when possible
- Extract clean domains for display
- Mark official sources, research sources, code sources, social sources, and media sources
- Provide a small trust score used by ranking

The first MVP implementation may use deterministic domain rules. It should not add network calls to tests.

## Fact Extraction

`fact_extractor.py` should read `data/top_news.json` and write `data/news_facts.json`.

Each record should include:

- `rank`
- `title`
- `url`
- `source_domain`
- `category`
- `summary`
- `facts`: short factual claims grounded in source text
- `evidence`: source snippets used to support the facts
- `entities`: companies, products, models, or projects
- `numbers`: performance, price, date, model size, benchmark, or usage numbers when present
- `confidence`

The fact extractor should use Ollama when available. If Ollama fails, it should write a conservative fallback record from existing title, summary, reason, and cluster text.

## Card Writing

`card_writer.py` should be updated to use fact records as the primary input. It should:

- Generate 8 to 10 cards
- Keep slide 1 as the fixed cover
- Make each news card traceable to at least one `source_urls` entry
- Avoid unsupported claims
- Avoid hype language
- Preserve Korean output
- Fail or warn clearly when card fields are missing

## Rendering

`card_renderer.py` should support visual templates based on `visual_type`:

- `abstract`: current general card layout
- `diagram`: simple flow or layered structure
- `timeline`: date/event sequence layout
- `comparison`: two-column comparison layout
- `chart`: metric-forward layout

Rendering should remain PIL-based for this MVP. The renderer should improve text fitting so long Korean/English mixed text does not overflow.

## Review Output

`review_exporter.py` should create `output/review.html` with:

- Card image preview
- Generated card text
- Source links
- Fact records used for each card
- Warnings for missing source URLs or low-confidence facts

The review page is an internal quality-control artifact, not a public landing page.

## Error Handling

The pipeline should fail early for missing required files and missing required dependencies. Network and Ollama failures should be handled per stage:

- Collection source failure: warn and continue
- Ranking LLM failure: skip that cluster and continue
- Fact extraction LLM failure: write fallback facts
- Card generation failure: fail the stage
- Rendering failure: fail the stage with slide number

## Testing

Add lightweight tests that do not require network access:

- Schema validation accepts valid examples and rejects invalid ones
- Google News URL/domain helpers handle representative URLs
- History pruning keeps recent items
- Card normalization preserves required fields
- Renderer input validation catches invalid cards

Use `pytest` for tests and keep fixtures small.

## Acceptance Criteria

The extended MVP is complete when:

- `run_pipeline.py --all` can run the full local pipeline
- `run_pipeline.py --render-only` can regenerate PNG and HTML from existing `data/cards.json`
- JSON schema validation runs after each pipeline stage
- `data/news_facts.json` is generated before card writing
- `output/review.html` is generated
- `visual_type` affects card rendering
- Network-free tests cover the new helper modules

