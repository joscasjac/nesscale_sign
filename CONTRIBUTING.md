# Contributing

Use a feature branch and a disposable local Frappe 16 site. Keep the app name `nesscale_sign` and existing DocType names stable. Preserve AGPL-3.0 notices and upstream attribution.

Frontend source is in `frontend/src`; run `npm ci`, `npm test`, and `npm run build` from `frontend`. Commit the generated assets with their matching HTML entrypoint. The preview server is development-only and must never be deployed.

Backend logic belongs in services; public endpoints enforce authentication, ownership and input validation. Every security fix needs a regression test. Run `bench --site TEST_SITE run-tests --app nesscale_sign` on an isolated test site. Test migrations and document recovery before releasing.

Do not commit credentials, PKCS#12 files, real signing links, or customer data. Screenshots must use visibly fictional data. Deployment requires separate review and approval. Avoid unsupported compliance claims.
