# Legacy vs Rebuild

This file tracks the functional comparison between the old `Ai_nl2sql/` app and the rebuilt app.

## Now Matched

1. Web homepage for asking NL2SQL questions
2. HTML form endpoint at `/ask`
3. JSON endpoint at `/analyze`
4. History page at `/logs`
5. Domain classification endpoint at `/classify_domain`
6. Enterprise-style query endpoint at `/wecom_query`
7. CSV download endpoint at `/download_csv`
8. Legacy schema and join-rule assets loaded into the new runtime

## Intentionally Improved

1. Core workflow is modular instead of versioned `v2/v6/v7` wrappers
2. Logs are file-backed and local by default instead of requiring a MySQL log table
3. Cache routing, prompt building, schema retrieval, and execution policy are separate components
4. The rebuilt app can be tested end-to-end without a live DB or live LLM

## Still Not Yet Equivalent

1. Real LLM, DB, and WeCom integrations are now optional adapters, but they still depend on your local legacy config and reachable external services
2. The default runtime still uses safe local adapters unless the legacy integration env vars are enabled
3. No old experimental scripts are reattached to the runtime app, by design
