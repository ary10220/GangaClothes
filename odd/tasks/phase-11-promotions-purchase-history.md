# ODD Tasks: Phase 11 Promotions and Purchase History

**Status:** WU-1 through WU-3 implementation and WU-4 automated closeout complete; visual/API/device parity pending
**Task count:** 12 implementation tasks (`P11-01` through `P11-12`)
**Route declaration:** delegated direct
**Mapping trigger:** fired — the work spans catalog, catalog detail, cart, purchase history, web parity references, backend response contracts, and tests.

## Objective

Extend the existing Flutter commerce surfaces so customer-visible promotions and purchase history faithfully consume the backend responses already used by the web. Preserve one purchase-history feature while adding backend-sourced promotion values, delivery and payment summaries, and authenticated comprobante actions where the existing API client supports them.

## Problem

The current mobile catalog, detail, cart, and purchase-history flows do not yet expose the full promotion and purchase data available from the backend. Without this phase, mobile can show incomplete prices, omit promotion context, and fail to explain delivery, payment, or comprobante information already available through the customer APIs.

## Why

The mobile customer experience must remain visually and behaviorally consistent with the web without creating a second purchase-history implementation or deriving financial values locally. The backend is the source of truth for final prices, discounts, totals, delivery charges, payment state, and purchase details.

## Authorized scope

- Consume and display backend-sourced promotion data in the catalog, catalog detail, cart, and purchase-history views, including final amount, list/previous amount when supplied, promotion label, saving, and discount fields.
- Preserve response monetary values unchanged; Flutter must not recalculate discounts or replace backend prices with locally derived values.
- Extend the existing purchase-history feature to consume `GET /ventas/mias` and display item detail, totals, `tipo_entrega`, `costo_envio`, `envio`, payment method/status/reference, and related optional fields.
- Add customer-facing authenticated JSON comprobante and PDF comprobante actions only if the existing API client already supports the required authenticated response handling. Confirm the capability before implementing the action.
- Add or update focused model, service, controller, and widget tests with promotion, pickup, delivery, payment-reference, comprobante, and missing-optional-field fixtures.
- Compare Flutter catalog, detail, cart, and purchase-history presentation with the corresponding web views for visual parity and responsive behavior.

## Explicit exclusions

The following work is not authorized in Phase 11:

- Phase 12 dynamic Stripe/QR behavior, payment-method discovery, pending/retry gateway behavior, or payment-flow replacement.
- Phase 13 delivery checkout configuration or delivery selection before payment.
- Phase 14 shipment tracking or new shipment-management behavior.
- Phase 15 AI assistant, recommendations, or conversational purchase-history behavior.
- Backend endpoint changes, database changes, Angular/web source changes, or changes to `PLAN_MOBILE_FLUTTER.md`.
- A duplicate purchase-history route, model, service, controller, or screen.
- New dependencies solely to provide PDF viewing, downloading, payment, delivery, or tracking behavior.

## Constraints

- Planning started with this ODD document only. After implementation began, WU-1 through WU-3 edits were limited to existing mobile catalog/detail, cart, and purchase-history source and test files listed in the delivery evidence below; no backend, web, `PLAN_MOBILE_FLUTTER.md`, or dependency changes were authorized.
- Reuse the existing Flutter `ApiClient`, session/authentication boundary, routes, theme, shared widgets, and `purchase_history` feature.
- Treat missing or `null` optional backend fields as valid states; do not invent values or hide a valid zero amount.
- Keep customer authorization and session-expiration behavior enforced by the existing authenticated request path.
- Preserve existing Spanish customer-facing copy where the application already uses it, while keeping this planning artifact in professional English.
- Verify API field names and response shapes against the current backend before changing models or fixtures.
- Do not infer Phase 12, 13, 14, or 15 behavior from this phase's comprobante or delivery summary requirements.
- Preserve unrelated pre-existing worktree changes. At planning time, the worktree already contains unrelated changes in `web/src/environments/api-url.ts`, `.atl/`, `.codegraph/`, and `PLAN_MOBILE_FLUTTER.md`.

## Resolved verification mode

**Standard Mode.** No `strict_tdd` capability was found in Engram. Implementation should therefore use the repository's normal focused-test-first feedback loop, followed by analysis, the complete Flutter test suite, and visual/API parity evidence. This resolution does not authorize skipping tests or verification.

## Exact actionable checklist

- [x] **P11-01 — Freeze the implementation baseline and confirm contracts.** Record the current behavior and inspect the backend response shapes for catalog/detail, cart, `GET /ventas/mias`, `GET /ventas/{id}/comprobante`, and `GET /ventas/{id}/comprobante.pdf`; identify which comprobante response handling is already supported by `ApiClient`. WU-1 evidence is limited to the public catalog contract and generic `ApiClient` capability described below.
- [x] **P11-02 — Define the fixture matrix before model changes.** Add a written implementation fixture matrix covering active promotion, no promotion, zero discount, pickup, delivery with `envio`, payment reference, missing payment reference, missing delivery object, and missing optional promotion fields; map every fixture field to its backend key. WU-1 verifies the catalog/detail promotion subset; the remaining Phase 11 fixtures are pending in later work units.
- [x] **P11-03 — Extend catalog and detail models without financial derivation.** Update the existing catalog/detail model and parsing boundaries to retain backend final/list/previous amounts, discount, promotion label, saving, and optional metadata exactly as supplied; preserve compatibility with responses that omit optional fields. WU-1 implements the catalog boundary.
- [x] **P11-04 — Render catalog and detail promotion parity.** Update the existing catalog cards and detail presentation to show the backend promotion state, previous/list amount, final amount, saving, and discount when present; preserve existing stock, variant, reservation, and cart-entry behavior. WU-1 verifies this with focused widget tests.
- [x] **P11-05 — Extend cart response/state mapping.** Update the existing cart models, service, and state/controller paths to retain line-level promotion data and backend subtotal, discount, shipping, and total values without recalculation or rounding drift.
- [x] **P11-06 — Render cart promotion and total parity.** Update the existing cart screen to display backend-sourced promotion context and totals, including optional values and zero-discount states, while keeping existing stock warnings, branch behavior, confirmation, and Phase 8 test-mode payment boundary unchanged.
- [x] **P11-07 — Extend purchase-history domain models for `GET /ventas/mias`.** Added backend-preserving parsing for promotion metadata, list/final prices, line discounts, `tipo_entrega`, `costo_envio`, `envio`, payment method/status/reference, receipt number, item detail, and totals. Missing details, payments, shipment, and promotion objects are safe; delivery defaults to pickup and the display receipt falls back to `#V-{id}` without deriving totals.
- [x] **P11-08 — Extend purchase-history service, controller, and screen in place.** The existing authenticated history route now exposes promotion, delivery, shipment, payment, and reference summaries while retaining loading/empty/error/retry behavior. JSON receipt viewing is an in-app dialog attached to the existing purchase card; no parallel history route or screen was added.
- [x] **P11-09 — Add conditional authenticated comprobante actions.** The existing `ApiClient` already supplies bearer-authenticated JSON requests, so `/ventas/{id}/comprobante` is wired through the existing service/controller boundary with customer-facing success and error handling. PDF bytes can be requested by Dio options, but there is no existing viewer, persistence, or file-opening capability; the PDF endpoint is intentionally not exposed in the UI and no dependency was added.
- [x] **P11-10 — Add focused automated coverage with the fixture matrix.** Completed for catalog/detail, cart, and purchase history; model, service, controller, and widget coverage asserts backend values remain unchanged, optional fields are safe, customer authorization is preserved, and no duplicate route/feature is introduced.
- [ ] **P11-11 — Perform visual and payload parity verification.** Partial/pending: implementation and automated checks are complete, but the authorized visual comparison, API/live-payload comparison, screenshots, and device run remain outstanding. No PDF UI comparison is claimed because the existing mobile capability gap remains documented.
- [x] **P11-12 — Run final verification and close the ODD work units.** Completed with the exact formatting, analysis, full-test, and coverage results below, the four real implementation commit identities, and rollback boundaries. Visual/API/device parity remains pending under P11-11.

## Acceptance criteria

- **AC-01:** Catalog and catalog-detail views display backend-provided final/list or previous amount, promotion label, saving, and discount fields when supplied, including a correct no-promotion state.
- **AC-02:** Cart line and summary views display backend-provided promotion, subtotal, discount, shipping, and total values without locally recalculating or substituting monetary values.
- **AC-03:** Purchase history consumes `GET /ventas/mias` through the existing authenticated service boundary and retains its current route and feature ownership.
- **AC-04:** Purchase history displays item detail, totals, delivery type, shipping cost, shipment summary when present, payment method/status/reference, and comprobante number without crashing when optional fields are absent.
- **AC-05:** Customer-facing JSON and PDF comprobante actions are authenticated and connected only when the existing API client supports their required response handling; unsupported capability is documented rather than expanded into a new dependency or payment feature.
- **AC-06:** Existing stock, branch, reservation, cart confirmation, session expiration, loading, empty, retry, and error behaviors remain intact.
- **AC-07:** Tests cover promotion, no-promotion, pickup, delivery, payment-reference, missing-optional-field, and comprobante capability states across models, services/controllers, and widgets.
- **AC-08:** Visual comparison shows parity with the web for the authorized catalog, detail, cart, and purchase-history states at the tested responsive sizes.
- **AC-09:** No Phase 12 dynamic Stripe/QR behavior, Phase 13 delivery checkout, Phase 14 tracking, or Phase 15 AI behavior is present in the implementation diff.
- **AC-10:** The final evidence names the exact test commands, results, changed files, authored-line count, work-unit commits, and rollback boundaries.

## Applicable Flutter commands

Run from `/Users/ilseromero/Documents/projects/GangaClothes/mobile` during implementation:

```bash
fvm flutter pub get
fvm dart format --output=none --set-exit-if-changed lib test
fvm flutter analyze
fvm flutter test test/catalog_service_test.dart test/catalog_detail_service_test.dart test/cart_service_test.dart test/purchase_history_models_test.dart test/purchase_history_service_test.dart test/purchase_history_controller_test.dart test/catalog_widget_test.dart test/cart_widget_test.dart test/purchase_history_widget_test.dart
fvm flutter test
fvm flutter test --coverage
fvm flutter run -d <authorized-device-or-simulator>
```

The `flutter run` command is for the manual visual-parity pass and requires an explicitly selected local device or simulator. Do not use it as a substitute for automated tests. No backend test command is required by this planning task because backend source changes are explicitly excluded.

## Progress

- [x] **P11-00 — Create this ODD task document.** The authorized scope, exclusions, verification mode, checklist, acceptance criteria, commands, evidence placeholders, and delivery boundaries are recorded.
- [x] **P11-01 — Freeze the implementation baseline and confirm contracts.** Verified the public catalog contract in `backend/app/modules/prendas/service.py` and `router.py`: `precio_venta` is the list price and the backend supplies `precio_final`, `descuento`, and nullable `promocion`; the generic authenticated `ApiClient.request` has no JSON/PDF-specific comprobante handling relevant to WU-1.
- [x] **P11-02 — Define the fixture matrix before model changes.** Implemented focused fixtures for active promotion, no promotion with legacy missing `precio_final`, zero discount, a promotion object with missing optional fields, and intentionally non-derived backend amounts; each maps to the backend keys `precio_venta`, `precio_final`, `descuento`, and `promocion.{id,nombre,tipo_descuento,valor,etiqueta,fecha_fin}`.
- [x] **P11-03 — Extend catalog and detail models without financial derivation.** `Product` now retains backend list/final prices, discount, and optional promotion metadata. Missing `precio_final` falls back only to `precio_venta`; no discount or final-price calculation is performed locally.
- [x] **P11-04 — Render catalog and detail promotion parity.** Catalog cards and detail sheets now render the backend final price, list price struck through only when `promocion` is present, promotion badge/label/name, and backend discount as savings while preserving stock, variants, reservation, cart, and existing loading/error/empty behavior. Focused widgets also cover no promotion, zero discount, and missing promotion metadata.
- [x] **P11-05 — Extend cart response/state mapping.** Cart models now retain backend list/final unit prices, line discount, promotion metadata, subtotal, total discount, delivery type, optional shipping cost, and optional shipment address/reference. Missing `precio_final` falls back only to `precio_unitario`; no financial values are recalculated. Existing service, controller, stock, branch, confirmation, and payment boundaries remain unchanged.
- [x] **P11-06 — Render cart promotion and total parity.** The cart screen now shows promotion context, final/list prices, supplied line savings, backend discount, pickup/delivery label, optional shipping cost/address summary, subtotal, and total while preserving existing stock and payment behavior.
- [x] **P11-07 — Purchase-history model extension.** Focused model coverage verifies promotion metadata, final/list values, line discount, delivery shipment, payment reference, receipt fallback, missing optional fields, and backend monetary values without local derivation.
- [x] **P11-08 — Existing purchase-history flow extension.** Focused widget coverage verifies delivery/payment/promotion rendering, JSON receipt dialog presentation, and preserved empty/error/retry states.
- [x] **P11-09 — Conditional comprobante actions.** Focused service/controller coverage verifies authenticated JSON receipt success/error handling and the documented PDF capability gap; PDF remains out of the UI.
- [x] **P11-10 — Automated fixture-matrix coverage.** Completed across catalog/detail, cart, and purchase history; the complete suite and preceding focused suites passed without introducing a duplicate route or feature.
- [ ] **P11-11 — Visual and payload parity verification.** Partial/pending: no screenshots, `flutter run`, device comparison, or live backend payload comparison was performed; authorized visual/API/device evidence is still required.
- [x] **P11-12 — Final verification and ODD closeout.** Completed with the repository-wide mobile format, analysis, full test, coverage, commit, and rollback evidence recorded below. This does not claim P11-11 parity evidence.

## Verification evidence placeholder

This section records only commands that have run; pending items remain explicitly unverified.

```text
Baseline contract evidence:
- Backend payloads/endpoints inspected: `backend/app/modules/prendas/router.py` and `backend/app/modules/prendas/service.py`; public catalog emits list/final/discount/promotion values from the promotion service.
- Existing ApiClient JSON/PDF capability: generic authenticated `ApiClient.request` only; comprobante handling is outside WU-1.

Automated evidence:
- Format command/result: `fvm dart format lib/features/catalog/catalog_models.dart lib/features/catalog/catalog_screen.dart lib/features/catalog/catalog_detail_sheet.dart test/catalog_service_test.dart test/catalog_widget_test.dart test/catalog_controller_test.dart test/catalog_detail_controller_test.dart` followed by the same command with `--output=none --set-exit-if-changed` — passed; 7 files checked, 0 changes required on the final check.
- Analyze command/result: `fvm flutter analyze lib/features/catalog/catalog_models.dart lib/features/catalog/catalog_screen.dart lib/features/catalog/catalog_detail_sheet.dart test/catalog_service_test.dart test/catalog_widget_test.dart test/catalog_controller_test.dart test/catalog_detail_controller_test.dart` — passed, no issues.
- Focused test command/result: `fvm flutter test test/catalog_service_test.dart test/catalog_detail_service_test.dart test/catalog_detail_controller_test.dart test/catalog_controller_test.dart test/catalog_widget_test.dart` — passed, 22 tests.
- WU-2 format command/result: `fvm dart format lib/features/cart/cart_models.dart lib/features/cart/cart_screen.dart test/cart_models_test.dart test/cart_service_test.dart test/cart_controller_test.dart test/cart_widget_test.dart` — passed; 4 files changed by formatting. Final check with `fvm dart format --output=none --set-exit-if-changed` over the same 6 files — passed; 0 changes required.
- WU-2 analyze command/result: `fvm flutter analyze --no-pub lib/features/cart/cart_models.dart lib/features/cart/cart_screen.dart lib/features/cart/cart_controller.dart lib/features/cart/cart_service.dart test/cart_models_test.dart test/cart_service_test.dart test/cart_controller_test.dart test/cart_widget_test.dart` — passed; no issues found. The initial pub-enabled attempt was blocked by Flutter's ephemeral iOS `.packages` deletion/read-only-volume error; the focused `--no-pub` rerun passed.
- WU-2 focused test command/result: `fvm flutter test test/cart_models_test.dart test/cart_service_test.dart test/cart_controller_test.dart test/cart_widget_test.dart` — passed, 15 tests.
- WU-3 format command/result: `fvm dart format lib/features/purchase_history/purchase_history_models.dart lib/features/purchase_history/purchase_history_service.dart lib/features/purchase_history/purchase_history_controller.dart lib/features/purchase_history/purchase_history_screen.dart test/purchase_history_models_test.dart test/purchase_history_service_test.dart test/purchase_history_controller_test.dart test/purchase_history_widget_test.dart` followed by `fvm dart format --output=none --set-exit-if-changed` over the same 8 files — passed; 4 files were initially formatted, and the final check reported 0 changes required.
- WU-3 analyze command/result: `fvm flutter analyze --no-pub lib/features/purchase_history test/purchase_history_models_test.dart test/purchase_history_service_test.dart test/purchase_history_controller_test.dart test/purchase_history_widget_test.dart` — passed; no issues found.
- WU-3 focused test command/result: `fvm flutter test test/purchase_history_models_test.dart test/purchase_history_service_test.dart test/purchase_history_controller_test.dart test/purchase_history_widget_test.dart` — passed, 17 tests.
- WU-3 PDF capability result: existing `ApiClient.request` accepts Dio `Options`, including a bytes response type, and applies the authenticated bearer interceptor; there is no existing viewer, persistence, or file-opening capability. The exact decision is to document the gap, keep `/ventas/{id}/comprobante.pdf` out of the UI, and add no dependency.
- WU-4 format command/result: from `mobile/`, `fvm dart format --output=none --set-exit-if-changed lib test` — passed; 73 files checked, 0 changes required.
- WU-4 analyze command/result: from `mobile/`, `fvm flutter analyze` — passed, no issues.
- Full test command/result: from `mobile/`, `fvm flutter test` — passed, 98 tests.
- Coverage command/result: from `mobile/`, `fvm flutter test --coverage` — passed, 98 tests; generated `mobile/coverage/lcov.info`, which is ignored by git.

Parity evidence:
- Catalog/detail visual and API payload comparison: [pending] — no screenshots, `flutter run`, or live backend payload comparison was performed.
- Cart visual and API payload comparison: [pending] — no screenshots, `flutter run`, or live backend payload comparison was performed.
- Purchase-history visual and API payload comparison: [pending] — no screenshots, `flutter run`, or live backend payload comparison was performed.
- Responsive/device states checked: [pending] — authorized device/simulator evidence remains outstanding.
- PDF UI comparison: not performed and not applicable to an existing capability; there is no existing viewer, persistence, or file-opening capability, and no dependency was added.

Delivery evidence:
- `4d00d99` (`feat(mobile): preserve backend promotions in catalog`) — catalog promotion behavior: `mobile/lib/features/catalog/catalog_models.dart`, `mobile/lib/features/catalog/catalog_screen.dart`, `mobile/lib/features/catalog/catalog_detail_sheet.dart`, the catalog controller/detail-controller/service/widget tests, and this task document.
- `e8a8a6f` (`test(mobile): cover catalog promotion parity`) — catalog promotion tests/evidence: `mobile/test/catalog_service_test.dart`, `mobile/test/catalog_widget_test.dart`, and this task document.
- `58e8a90` (`feat(mobile): render backend promotions in cart`) — cart promotion parity: `mobile/lib/features/cart/cart_models.dart`, `mobile/lib/features/cart/cart_screen.dart`, the cart model/service/controller/widget tests, and this task document. No cart service/controller source change was necessary: the existing request and state/payment paths already preserve the backend `Cart` object and Phase 8 contract.
- `7687a5a` (`feat(mobile): complete purchase history parity`) — purchase-history parity: `mobile/lib/features/purchase_history/purchase_history_models.dart`, `mobile/lib/features/purchase_history/purchase_history_service.dart`, `mobile/lib/features/purchase_history/purchase_history_controller.dart`, `mobile/lib/features/purchase_history/purchase_history_screen.dart`, the four purchase-history tests, and this task document. `mobile/lib/core/network/api_client.dart` was not changed.
- Commit stats, including task-document evidence in each commit: `4d00d99` 554 additions/62 deletions across 8 files; `e8a8a6f` 84 additions/7 deletions across 3 files; `58e8a90` 379 additions/21 deletions across 7 files; `7687a5a` 769 additions/30 deletions across 9 files. Generated coverage and dependencies are excluded from these implementation boundaries.
- Rollback boundaries: revert the catalog source/tests from `4d00d99` and the catalog test additions from `e8a8a6f` to remove catalog promotion behavior; revert the cart source/tests from `58e8a90` to remove cart promotion parity; or revert the four purchase-history source/tests from `7687a5a` to remove purchase-history parity. Keep the other behavior units and their unrelated stock, branch, confirmation, payment, and authenticated-history behavior intact.
- WU-4 rollback boundary: remove only the verification and receipt entries in this task document; WU-4 adds no runtime behavior or dependency.
- Runtime harness: N/A — no `flutter run`, device/simulator run, or screenshots were authorized or performed; automated widget tests exercised the rendered states.
- Out-of-scope review: the four real commits touched only the existing mobile implementation/tests and this task document. They did not touch backend files, web files, `PLAN_MOBILE_FLUTTER.md`, dependency files, or Phase 12–15 behavior; pre-existing unrelated worktree changes remain outside this task. There is no existing viewer, persistence, or file-opening capability for PDF receipts, so no PDF UI was added or compared and no dependency was added.
```

## Next step

Implementation and automated checks are complete through WU-4: P11-10 and P11-12 are closed, with the four real commits recorded above. Next, complete P11-11 using authorized visual/API/device parity evidence; no screenshots, `flutter run`, live backend payload comparison, or PDF UI verification is claimed here. Keep backend, web, `PLAN_MOBILE_FLUTTER.md`, dependencies, and Phase 12–15 behavior out of scope.

## Advisory changed-line forecast

The measured commit stats above replace this implementation forecast. They exceed the advisory 400-line review budget in aggregate, so the four existing behavior/evidence commits remain the honest review boundaries; no code or test compression was used. Generated coverage and build output are excluded.

## Work-unit commit and rollback boundary

Each work unit must include its behavior and the tests that verify it. Each commit must be independently reviewable, use a Conventional Commit message, and record focused-test results plus the runtime-harness result or an explicit `N/A` reason.

| Work unit | Deliverable and commit boundary | Rollback boundary |
|---|---|---|
| **WU-1 / P11-01–P11-04** | Confirm contracts and implement backend-sourced promotion parsing/rendering in catalog and detail, with the related catalog/detail tests. Commits: `4d00d99` catalog behavior and `e8a8a6f` catalog promotion tests/evidence. | Revert only the catalog/detail source and tests from those two commits; catalog browsing, variant selection, reservation, cart entry, and later cart/history work remain intact. |
| **WU-2 / P11-05–P11-06** | Implement cart promotion and backend-total parity, with cart model/state/widget tests. Commit: `58e8a90` (`feat(mobile): render backend promotions in cart`). | Revert only the cart source and tests from `58e8a90`; catalog and purchase-history work remains untouched. |
| **WU-3 / P11-07–P11-09** | Complete the existing purchase-history delivery/payment/comprobante extension, with history model/service/controller/widget tests. Commit: `7687a5a` (`feat(mobile): complete purchase history parity`). | Revert only the purchase-history source and tests from `7687a5a`; the existing route boundary and unrelated cart/catalog behavior remain available. |
| **WU-4 / P11-10–P11-12** | Close automated tests, scope review, and final receipts for the four preceding commits. P11-11 remains partial/pending because visual/API/device parity evidence was not performed; this closeout adds no runtime behavior. | Revert only this task document's WU-4 verification entries; do not revert the four implementation/evidence commits or introduce a parity adjustment without new authorized evidence. |

If implementation reveals that a single work unit cannot remain independently reviewable, stop at the smallest honest boundary, record the measured count, and split by behavior rather than by file type.
