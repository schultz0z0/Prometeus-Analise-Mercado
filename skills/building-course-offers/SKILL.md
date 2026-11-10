---
name: building-course-offers
description: Use when verified course, market, curriculum, scoring, and limitation facts must become an executive dossier and testable educational offer.
---

# Building Course Offers

**Version:** 2.2.0

Turn approved facts into a useful decision dossier while keeping observations and strategic hypotheses visibly separate.

## Dossier requirements

Cover executive recommendation, confidence and coverage, historical comparables, demand signals, competition, pricing, employability, social voice, curriculum alignment, risks, counter-evidence, limitations, and next experiments.

Every material claim cites existing `evidence_ids`. Quantitative claims reproduce the structured facts exactly. Never convert a proxy into “proven demand” or omit a failed/empty required source.

Distinguish internal demand potential (IPD from up to three comparables), external market assessment, curriculum alignment, combined pricing reference and the consolidated result. Code supplies aggregation, weights, coverage and confidence. Do not count mixed-source alignment/pricing again inside the external block. Missing evidence is a coverage limitation, not poor observed performance.

Present declared institution identity, price/payment terms and academic duration as declared inputs, not as questions already answered by the form. Own institution pages/ads belong to institutional context. Raise identity uncertainty only when source facts conflict, not merely because the institution appears on its own syllabus.

Separate **Educational Competitors** from **Sector Ecosystem / Insurer Radar** (`actor_role == "sector_radar"`):
- Educational competitors (schools, universities, EdTechs) are compared on active course offer, modality, workload, syllabus coverage, and observed tuition (`direct_competition` / `pricing`). Absence of an observed course on a queried competitor domain is academic whitespace to validate, never proof of zero demand or permission to invent prices.
- Sector radar actors (e.g., insurance companies for ENS) represent the **employer market, broker ecosystem, product launches, and operational pains**. Use their signals to substantiate curriculum relevance, B2B/broker pain points, and market timing — NEVER list an insurer as a direct educational competitor or mix insurance product prices into tuition benchmarks.
- When citing social presence of global corporate profiles (`linkedin_scope == "global"`, such as MAPFRE or Zurich global LinkedIn), qualify the metric explicitly as global corporate context and never attribute global follower counts to Brazil.

Price recommendations use comparable same-category/theme offers, distinguish internal and external observations, and state pricing-reference gaps. Proximity to an average is a positioning signal; it does not prove profitability, margin, willingness to pay or enrollment.

Explain material evidence losses by source and cause. Show whether information was unusable, context-only, duplicated, outside scope, awaiting review or lost to a source failure, rather than presenting every item simply as excluded. Useful context may support narrative without entering a score. An incomplete collection cannot support a confident negative verdict about the course.

## Offer hypotheses

Naming, positioning, promise, differentiators, audience segments, module changes, and marketing hooks are hypotheses to test. Connect each suggestion to the observed evidence that motivated it and state what experiment could validate it.

## CMS 9-Subpage Dossier Alignment

Your structured `DossierOutput` directly populates the 9-subpage Executive CMS Dossier (`Visão Geral`, `Métricas-Chave`, `Concorrência Fixa`, `Radar Setorial`, `Economia & Cenários`, `SWOT & TOWS`, `Pilares de Viabilidade`, `Revisões`, `Fontes & Evidências`) built by `DossierCmsPageBuilder` and checked by `DossierVerifier`:
- **`highlights.pros` & `highlights.cons` (`SWOT & TOWS`, `Visão Geral`, `Concorrência Fixa`):** Reference verified `claim_ids` in `pros` covering both internal strengths (institutional history, IPD, syllabus fit) and external market opportunities (search demand, employability, sector radar timing), and in `cons` covering internal gaps and external competitive/market threats.
- **`highlights.action_recommendations` (`SWOT & TOWS`, `Concorrência Fixa`, `Revisões`):** Assign `area` using the canonical governance areas (`Marketing`, `Produto`, `Comercial`, or `Financeiro`) so TOWS strategies, competitive insights, and departmental next steps are routed accurately.
- **`highlights.validation_criteria` (`Revisões` & `SWOT & TOWS`):** Keep `status="pending"` and identify the responsible area or validation mechanism in `target` (e.g., `Financeiro: validar CAC e ponto de equilíbrio`, `Produto: homologar módulos práticos`) so pending governance items map to the review workflow.
- **Pillar & Radar Coverage (`Pilares de Viabilidade` & `Radar Setorial`):** Ensure your atomic `claims` cite the specific `evidence_ids` from each active pillar (`internal_history`, `paid_competition`, `search_and_media`, `employability`, `syllabus_fit`, `pricing`) and from `sector_radar` so each subpage displays traceable analytical synthesis alongside deterministic metrics.

## Prohibited behavior

- No invented competitor, price, job count, trend, quote, source, or financial result.
- No listing of sector radar insurers/employers as direct educational competitors.
- No approval language that implies a human decision.
- No claims of guaranteed enrollment, revenue, employability, or compliance.
- No hiding low coverage behind confident prose.
