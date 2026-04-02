---
title: Monetization Strategy Audit
description: Comprehensive audit of IP valuation, licensing posture, and monetization pathways for the GMA2 MCP project
version: 2.1.0
created: 2026-03-12T02:10:00Z
last_updated: 2026-03-25T00:00:00Z
---

# Monetization Strategy Audit

## Executive Summary

The **GMA2 MCP** project is an MCP server exposing 90 tools that allow AI assistants to control grandMA2 lighting consoles via Telnet. It represents **8–12 weeks of specialized engineering** and encodes reverse-engineered protocol knowledge that is not publicly documented.

**Current posture:** The repository is licensed under **Apache 2.0** with no monetization infrastructure — no paywall, no license keys, no usage tracking. Anyone can legally fork, modify, and commercialize the code today.

**Key finding:** The project's primary value lies in its **domain expertise** (reverse-engineered MA2 telnet protocol, live-verified specifications, 152-keyword vocabulary) rather than raw code volume. This expertise is the defensible moat, but the permissive license currently gives it away for free.

**Recommendation:** Make the repository private immediately. Pursue a **hybrid model** — maintain a limited public version for discovery and community goodwill while developing premium features behind a paywall. If acquisition is the goal, establish paying customers first to prove market demand and increase valuation.

**Strategic framing (March 2026):** The emerging MCP monetization landscape confirms tool-call metering as an accepted payment primitive — Paper.design gates free users at 100 MCP calls/week, charging $16–20/month for Pro access. The niche market position is a structural advantage: unlike broad developer tools where VC-subsidized free products eliminate pricing power, the 5,000–15,000 user MA2 market is too small to attract funded competitors. This echoes the "reverse MA Lighting philosophy" — MA gives away software and sells hardware; GMA2 MCP should give away basic knowledge (SKILL.md skills) and sell the AI automation layer. See Section 3.5 for detailed case study analysis and Section 4.6 for strategic positioning.

---

## 1. IP Valuation Assessment

### 1.1 Codebase Metrics

| Metric | Value |
|--------|-------|
| MCP tools | 90 |
| Command builder functions | 150 |
| Keyword vocabulary entries | 152 |
| Unit tests | 1,498 |
| Live integration tests | 132 |
| Python source lines | ~40,000 |
| Source files | 42 |
| Test files | 46 |
| Repository size | 63 MB |

### 1.2 Domain Expertise Value

The codebase encodes knowledge that is **not available in MA Lighting's public documentation** and was obtained through systematic reverse-engineering and live console verification:

- **Telnet protocol behavior** — Login handshake, response parsing, ANSI escape handling, multi-chunk buffering with timeout falloff
- **26 system variables** — Wire formats, update triggers, and edge cases (e.g., `$SELECTEDFIXTURESCOUNT` only updates via `SelFix`, not `Select`; `Echo $VAR` fails because MA2 expands before executing)
- **MAtricks subsystem** — 13+ keywords with dimensional notation, Y-axis asymmetry (`NextRow` exists but `PreviousRow` does not), state is GUI-only with no telnet read command
- **PresetType / Feature / CD-Tree correlation** — Calling `Feature [name]` or `PresetType [id]` updates three system variables simultaneously; fixture-dependent naming
- **New Show connectivity hazard** — Creating a new show without `/globalsettings` resets Telnet to "Login Disabled," severing the MCP connection
- **CD tree navigation** — Show-dependent root prompt names, 4+ level depth navigation, index-based child addressing

All specifications are **live-verified on MA2 v3.9.60.65** with exact dates (2026-03-10/11).

### 1.3 Replication Difficulty

| Component | Lines | Estimated Replication Time | Difficulty |
|-----------|-------|---------------------------|------------|
| Telnet protocol knowledge | 1,000+ | 3–4 weeks | Very High |
| 152-keyword vocabulary | 520 | 2–3 weeks | Very High |
| Command builder library | 7,225 | 1–2 weeks | High |
| Navigation + state tracking | 300+ | 3–4 days | Medium |
| RAG semantic search pipeline | 2,000+ | 1–2 weeks | High |
| Test suite (1,498+ tests) | — | 2–3 weeks | High |
| ML tool categorization | 500+ | 3–4 days | Medium |
| **Total** | **~40,000** | **8–12 weeks** | **High** |

### 1.4 Unique Differentiators

1. **Three-tier safety system** — All commands pass through `SAFE_READ → SAFE_WRITE → DESTRUCTIVE` classification before reaching telnet, preventing accidental console corruption
2. **Pure command builders** — 150 stateless functions with zero I/O, fully testable in isolation
3. **RAG pipeline** — AST-aware Python chunking, heading-based markdown chunking, web crawler for ~1,043 MA2 help pages, SQLite vector store with hash-based deduplication
4. **Custom K-Means clustering** — Pure numpy implementation (no scikit-learn dependency) for automatic tool categorization
5. **Command injection prevention** — Line break stripping (`\r`, `\n`) in all telnet commands

---

## 2. Current Licensing Gap Analysis

### 2.1 Apache 2.0 Implications

The current license (`LICENSE` file, copyright 2025 thisis-romar) is **fully permissive**:

- Anyone can use, modify, and distribute the code
- Anyone can create and sell commercial derivatives
- Only requirement: attribution and license notice preservation
- **No copyleft** — derivative works need not be open-source
- **No patent retaliation** (unlike some licenses)

**Impact:** A competitor could legally fork the repository today, rebrand it, and sell it. The existing public version cannot be retroactively relicensed or recalled.

### 2.2 VS Code Extension License Gap

The VS Code extension in `vscode-mcp-provider/` has **no explicit LICENSE file**. It inherits the root Apache 2.0 license by default, but the absence of an explicit license creates ambiguity. An explicit license file should be added to align with the core project before any commercial licensing strategy.

### 2.3 AI-Generated Contribution Risk

The git history shows **5 commits attributed to "Claude"** (AI assistant). This raises questions:

- **Copyright ownership** — AI-generated code may not be copyrightable under current US law (Thaler v. Perlmutter, 2023)
- **Work-for-hire doctrine** — If the AI was used as a tool by the author, the human author likely retains copyright, but this has not been tested for code contributions
- **Due diligence flag** — Any acquirer's legal team will scrutinize AI-authored portions

**Recommendation:** Document which commits are AI-assisted and ensure the primary author asserts ownership over all contributions in a written declaration.

### 2.4 Missing Legal Documents

| Document | Status | Required For |
|----------|--------|-------------|
| Terms of Service | Missing | Subscription/SaaS model |
| Privacy Policy | Missing | Any user data collection |
| EULA | Missing | Software licensing |
| Contributor License Agreement | Missing | Accepting external contributions |
| CONTRIBUTING.md | Missing | Community contribution guidelines |
| SECURITY.md | Missing | Vulnerability disclosure process |

### 2.5 Version Inconsistency

- `pyproject.toml` declares version **0.1.0** with "Development Status :: 3 - Alpha"
- `README.md` front matter declares version **3.1.0**
- This inconsistency undermines professional credibility during due diligence

---

## 3. Monetization Path Analysis

### Path A: Micro-Monetization (Sell Access)

**Model:** Charge individual users or teams for repository access via subscription or one-time purchase.

**Platforms:**

| Platform | Model | How It Works |
|----------|-------|-------------|
| Basetools | Pay-per-repo | Set a price; buyers get auto-invited as collaborators to private repo |
| GitPaid | Subscription | Monthly/annual access with seat management |
| SugarKubes | Marketplace | List alongside other developer tools |
| Lemon Squeezy | License keys | API-based license validation with seat limits |

**Requirements to implement:**

1. **Make repository private** — Otherwise there is no technical barrier to free access
2. **Add license key validation** — Integrate with Lemon Squeezy or similar API to validate keys at MCP server startup
3. **Implement feature gating** — Separate free tier from paid tier functionality
4. **Create billing infrastructure** — Payment processing, customer management, support channel

**Candidate features for premium tier:**

| Feature | Current Location | Rationale |
|---------|-----------------|-----------|
| RAG semantic search | `rag/` | High-value; requires embedding API |
| Web doc ingestion | `scripts/rag_ingest_web.py` | Domain-specific; crawls 1,043 pages |
| ML tool categorization | `src/categorization/` | Unique; custom K-Means implementation |
| Full fixture library support | `src/commands/constants.py` | `FILTER_ATTRIBUTES` is fixture-dependent |
| Advanced MAtricks (store presets) | `src/commands/functions/matricks.py` | DESTRUCTIVE tier; power-user feature |
| Strategic scan | `scripts/strategic_scan.py` | Console discovery; 4-phase scan |

**Pricing benchmarks from comparable niches:**

| Comparable | Price | Market |
|-----------|-------|--------|
| Lightwright (John McKernon) | ~$1,000 perpetual; transitioning to subscription (Dec 2025) | 90%+ of Broadway shows |
| Savvy Vectorworks Plugins (Joshua Benghiat) | $14–60/tool, $39/year bundle | Entertainment design add-ons |
| Paper.design MCP Pro | $16–20/month for 1M MCP calls/week | Design-to-code tools |
| 21st.dev MCP | $20/month after 5 free requests | Developer MCP tools |
| Conveyor (bootstrapped CLI) | $45/month | Niche professional market |

**Recommended range:** $29–79/month or $200–500/year (annual discount). Usage-based per-call pricing adds unnecessary complexity for a market of 500–2,000 paying users. Simple Stripe subscription billing is sufficient; do not invest in MCP-native payment infrastructure (Nevermined, Radius) — too immature as of March 2026.

**Value justification:** 30 minutes saved per show x 200 shows/year x $50+/hour billing rate = $5,000+ annual value. A $500/year subscription captures 10% of value created.

**Estimated revenue potential:** With 100–500 early adopters at $29–79/month, realistic annual revenue is $35K–475K.

**Pros:**
- Recurring revenue stream
- Proves market demand (valuable for acquisition)
- Retains IP control

**Cons:**
- Small addressable market
- Support burden on single author
- Requires building billing/auth infrastructure

### Path B: Full Acquisition (Exit)

**Model:** Sell the entire intellectual property to a strategic buyer.

**Potential buyer profiles:**

| Buyer Type | Interest | Likely Valuation |
|-----------|----------|-----------------|
| Lighting software companies | Integrate AI control into their platforms | $25,000–$100,000 |
| MCP/AI agent platforms | Add lighting vertical to their ecosystem | $50,000–$200,000 |
| MA Lighting (vendor) | Official AI integration for grandMA3 | Potentially higher but risk of rejection |
| Entertainment tech acquirers | Portfolio play in live event automation | $25,000–$75,000 |

**Requirements to maximize valuation:**

1. **Make repository private** — Preserve "proprietary" status of new features
2. **Establish revenue** — Even $500/month proves the tool generates income; Acquire.com listings with revenue command significantly higher multiples
3. **Clean IP chain** — Document AI contributions, resolve license mismatch, add CLA
4. **Asset Purchase Agreement** — Transfer "all substantial rights" including code, documentation, domain knowledge, customer list, and trademarks
5. **Due diligence package** — Prepared documentation showing code quality, test coverage, architecture, and deployment procedures

**Valuation factors:**

| Factor | Status | Impact on Value |
|--------|--------|----------------|
| Active paying customers | None | Significantly reduces valuation |
| Proprietary license | No (Apache 2.0) | Reduces valuation — public forks exist |
| Domain expertise | Very high | Primary value driver |
| Test coverage | 1,498 tests | Increases buyer confidence |
| Documentation | Comprehensive | Positive signal |
| Bus factor | 1 (single author) | Risk factor for buyers |
| Market traction | Unknown (stars/forks) | Need to quantify |

**Listing platforms:**

- **Acquire.com** — More likely to accept with active customers; targets $25K+ listings
- **MicroAcquire** — Developer tool acquisitions
- **Direct outreach** — Contact lighting software companies, MCP platform builders

### Path C: Hybrid (Public Lite + Private Pro)

**Model:** Maintain a free, limited-feature public repository for discovery and community engagement, while keeping the full-featured version private for paying customers.

**Public tier (open-source, marketing function):**

- Core telnet connectivity
- Basic command builders (10–15 essential tools)
- Safety tier system
- README with full feature list (showcasing premium capabilities)
- Community contributions welcome (with CLA)

**Private tier (paid access):**

- All 90 MCP tools
- RAG semantic search pipeline
- Web doc ingestion (1,043 MA2 help pages)
- ML tool categorization
- Advanced MAtricks control
- Filter library generation (168 filters with VTE variants)
- Strategic scan utility
- Priority support

**Implementation approach:**

1. Fork current repo → Private (becomes the "Pro" version)
2. Strip private repo to essentials → New public repo (becomes the "Lite" version)
3. Public repo README links to paid tier with feature comparison table
4. Use Lemon Squeezy / Basetools for access management

**Pros:**
- Public version drives discovery via search engines and GitHub stars
- Stars/forks serve as "social proof" for acquisition negotiations
- Free users become potential paid customers
- Maintains open-source community goodwill

**Cons:**
- Maintaining two codebases (or branching strategy)
- Risk of community building a feature-complete fork of the lite version
- More operational overhead than single-repo approach

### Path D: SKILL.md Marketplace Funnel → Freemium MCP Server

**Model:** Use free SKILL.md agent skills as distribution channels that funnel lighting professionals toward a paid hosted MCP server. This inverts the traditional "make repo private" approach — instead, free knowledge skills maximize reach while execution is gated behind a subscription.

**Three-layer architecture:**

| Layer | What | Revenue | Purpose |
|-------|------|---------|---------|
| 1. Knowledge skills | 6 free SKILL.md files on marketplaces | $0 | Distribution, SEO, funnel entry |
| 2. Freemium MCP server | Credit-gated Telnet bridge | $29–79/mo or $200–500/yr | Core revenue |
| 3. Hosted SaaS assistant | Web-based AI lighting programmer | Per-show/project pricing (future) | Enterprise capture |

**Knowledge-execution split:**

The six proposed agent skills (scaffolded in `skills/`) are classified into two tiers:

*Instruction-only skills (standalone value, full free distribution):*
- **Command Reference** — MA2 syntax, keyword vocabulary, command patterns
- **Show Architecture** — Show file structure, CD tree navigation, pool organization
- **Networking** — Art-Net, sACN, MA-Net2 configuration

These function as "smart reference manuals" — a lighting programmer can use them with any AI agent to generate correct grandMA2 syntax without the MCP bridge.

*Hybrid skills with execution gates (generate commands, gate execution):*
- **Macros** — Macro creation, timing, conditional logic → generates command sequences
- **Programming** — Cue/sequence programming, effects, MAtricks → generates full cue stacks
- **Lua Scripting** — Lua plugin development, API calls → generates runnable scripts

Hybrid skills generate complete command sequences but instruct the agent: *"These commands are ready for execution. Connect the grandMA2 MCP bridge to send them to your console. First 20 executions are free."*

**Freemium conversion model:**

Following proven MCP monetization patterns (Paper.design validates MCP call gating; 21st.dev validates API key + subscription):
- N free command executions to prove the bridge works
- Pro tier: $29–79/month or $200–500/year for freelance programmers (200–400 users → $58K–380K ARR)
- Enterprise tier: $99–199/month for production companies (20–50 accounts → $24K–120K ARR)
- Typical developer tool freemium conversion: 1–3%, well-executed products: 6–8%

Flat subscription with generous call limits is preferred over per-call metering. Paper.design's per-call model works for millions of users; flat pricing is right for thousands. Simple Stripe subscription billing — do not invest in MCP-native payment infrastructure (Nevermined, Radius) at this stage.

**Distribution (community-first, not marketplace-first):**

Primary channels — peer recommendation drives adoption in this market more than marketplace listing:
- **ControlBooth forums**, **MA Lighting Forum**, **r/lightingdesign**, lighting Facebook groups
- **LDI** (Las Vegas), **Prolight+Sound** (Frankfurt), **PLASA** (London) — trade show demos
- A single endorsement from a well-known touring LD is worth more than 10,000 MCP directory listings

Secondary channels — marketplace presence for AI-curious developers:
- SkillsMP, Skills.sh, LobeHub, GitHub, dedicated product website
- MCPize for paid MCP server listing (only functional paid marketplace as of March 2026)
- npm and Docker for self-serve MCP server installation

**Competitive moat:**

The SKILL.md files document grandMA2 command patterns using publicly available syntax — this is not the moat. The moat is the **reliable, queue-managed, error-handled Telnet bridge** that makes AI-to-console communication production-safe. Publishing tool schemas (parameters, return types) is safe; the Telnet communication logic, error handling, reconnection strategies, and command sequencing are the defensible IP.

**Pros:**
- Maximizes distribution (free skills reach every AI agent user)
- Natural conversion path (skill generates commands → user needs bridge to execute)
- No "make repo private" needed for skills — only MCP server implementation is proprietary
- Aligns with industry culture (free console software, pay for production tools)
- First-mover advantage in a zero-competition vertical

**Cons:**
- Requires building hosted MCP server infrastructure (OAuth, credit tracking, billing)
- Small TAM limits revenue ceiling (5,000–15,000 addressable users)
- Marketplace policies on promotional content within skills are uncharted
- Conversion rates in niche professional tools are unproven

> **Note:** Market research supporting this path (marketplace statistics, industry sizing, case studies) is documented separately in `doc/market-research-appendix.md`. All external statistics are labeled as unverified.

### 3.5 MCP-Era Monetization Models: Pencil.dev vs. Paper.design

Two VC-backed design-to-code tools launched in 2024–2025 with native MCP servers offer contrasting monetization strategies that bracket the range of options for MCP-native products. Both sit at the intersection of design and code, both ship MCP servers as core features, and both ride the "vibe coding" wave — but their business models diverge sharply.

**Side-by-side comparison:**

| Dimension | Pencil.dev | Paper.design | GMA2 MCP (this project) |
|-----------|-----------|-------------|------------------------|
| **MCP tools** | Built-in, auto-starts | 24 tools, local desktop app | 90 tools, Telnet bridge |
| **Pricing** | Free (VC-subsidized) | Free 100 calls/wk → $16–20/mo Pro | None (currently) |
| **Revenue model** | Parasitic (piggybacks on AI subs) | MCP call metering | N/A |
| **Users** | 100,000 (Feb 2026) | 40,000+ early access | Unknown |
| **Funding** | ~$1M (a16z Speedrun) | $4.2M (Accel, Basecase) | Bootstrapped |
| **TAM** | Millions (all designers) | Millions (all designers) | 5,000–15,000 (MA2 users) |
| **Distribution** | VS Code Marketplace, Cursor | Desktop app, word of mouth | GitHub, community forums |

**Three strategic takeaways for this project:**

**1. Pencil's free model is wrong for this market.** Pencil gives away everything because (a) it has VC runway to burn, (b) its TAM is millions of designers, and (c) it monetizes indirectly through AI subscription volume. GMA2 MCP has none of these conditions — no VC capital, a TAM of 5,000–15,000, and no indirect monetization channel. Copying Pencil's approach means perpetual $0 revenue.

**2. Paper's MCP call metering is the right template, adapted for scale.** Paper.design proves that gating MCP tool calls is a viable, accepted monetization mechanism as of early 2026. However, Paper's 100-free-calls/week threshold works because their users make hundreds of calls per design session. For GMA2 MCP, where a single show programming session might involve 50–200 commands, the free tier threshold and pricing must be calibrated to lighting workflow cadence rather than design workflow cadence. A flat subscription with generous call limits is preferable to per-call metering at this market size.

**3. The "Conveyor insight" — niche markets structurally favor bootstrapped products.** Conveyor, a CLI tool charging $45/month in a small market, found that niche markets are actually *better* for bootstrapped products: no VC-funded free competitors, loyal customers, low infrastructure costs. Unlike broad developer tools where VC-subsidized free products (Pencil) kill monetization, the 5,000–15,000 user MA2 market is too small to attract funded competitors. No one will raise $4 million to build a competing MA2 MCP server. **That's the moat.**

> **Supporting data:** Company profiles and raw metrics for Pencil.dev and Paper.design are in `doc/market-research-appendix.md`, Sections G–I. Lighting industry pricing comparables (Lightwright, Savvy Vectorworks Plugins, Conveyor) are in Section I.

---

## 4. Risk Analysis

### 4.1 Existing Public Exposure

The code has been public under Apache 2.0. **Any version already distributed cannot be recalled.** Existing forks (if any) retain their license rights indefinitely. This means:

- New features developed after going private are protectable
- Existing code in the public version is permanently available
- A competitor could build on the current public version legally

**Mitigation:** Go private now to limit further exposure. Focus IP protection efforts on new features and improvements.

### 4.2 Competitor Replication

While the code is replicable in 8–12 weeks, the **domain expertise** is the true moat:

- The MA2 telnet protocol is undocumented at this level of detail
- Live-verified specifications require access to a real console
- The 152-keyword vocabulary with risk classification took significant effort
- Edge cases (New Show connectivity, `SelFix` vs `Select`, `Echo` variable expansion failure) are only discoverable through extensive testing

**Risk level:** Medium. A motivated competitor with MA2 access could replicate this, but the head start is significant.

### 4.3 MA Lighting Vendor Relationship

- MA Lighting may view third-party control tools favorably (extends platform value) or unfavorably (bypasses official tooling)
- grandMA2 is a legacy platform; **grandMA3** is the current product line — MA Lighting's strategic focus is likely on MA3
- A cease-and-desist or API lockdown is low-probability but possible
- The tool depends on the telnet interface remaining available in MA2 firmware

### 4.4 Niche Market Size

The addressable market is the intersection of:

- grandMA2 console users (thousands worldwide, but declining as MA3 adoption grows)
- Users interested in AI/MCP-based control (early adopter segment)
- Users willing to pay for tooling (subset of above)

**Realistic early market:** 50–500 potential paying users. This limits subscription revenue but is sufficient to prove demand for an acquisition.

### 4.5 Single-Author Bus Factor

The project has one primary contributor. For an acquirer, this means:

- Knowledge transfer is critical and concentrated
- Ongoing maintenance depends on retaining or replacing one person
- Typically results in an earn-out clause or consulting agreement post-acquisition

### 4.6 Strategic Positioning: "Reverse MA Lighting Philosophy"

MA Lighting gives away software (onPC, MA3D) and sells hardware ($5,000–$92,000 consoles). The GMA2 MCP project should invert this: **give away basic functionality** (knowledge skills, reference documentation, perhaps basic MCP connectivity) and **charge for the AI automation layer** (full 90-tool suite, RAG pipeline, advanced features).

This framing solves three positioning problems:

1. **Avoids "why pay for a plugin?" resistance** — AddOnDesk plugins are free-to-€19. Positioning as a plugin invites comparison to that price tier. Positioning as a "production tool" (Capture/Depence tier at €395–€15,000) reframes the value conversation entirely.
2. **Aligns with industry expectations** — The lighting community expects free console software. Giving away the knowledge layer (SKILL.md skills, reference docs) satisfies this expectation while reserving execution for the paid tier.
3. **Mirrors the proven Pencil/Paper split** — Pencil gives away everything and depends on external AI subscriptions. Paper gives away a taste and charges for production usage. The GMA2 approach gives away knowledge and charges for AI-powered execution — the best of both models.

See appendix Section D.3 for price sensitivity data supporting this positioning.

---

## 5. Recommended Action Items

### Immediate (This Week)

| # | Action | Rationale |
|---|--------|-----------|
| 1 | **Make repository private** | Stop free distribution of new features; preserve IP for negotiation |
| 2 | **Resolve version inconsistency** | Align `pyproject.toml` and `README.md` versions |
| 3 | **Document AI contributions** | Written declaration that all AI-assisted code is owned by the primary author |
| 4 | **Audit existing forks** | Check GitHub for existing forks/clones to understand exposure |
| 5 | **Select billing infrastructure** | Stripe subscription — do not invest in MCP-native payment infra (Nevermined, Radius) as it is too immature |

### Short-Term (1–4 Weeks)

| # | Action | Rationale |
|---|--------|-----------|
| 6 | **Add CLA** | Protect IP when accepting external contributions |
| 7 | **Add explicit VS Code extension license** | Add LICENSE file to vscode-mcp-provider/ to eliminate ambiguity |
| 8 | **Relicense new code** | Consider BSL (Business Source License) or dual-license (AGPL + commercial) for new features |
| 9 | **Create TOS, Privacy Policy, EULA** | Legal foundation for commercial operation |
| 10 | **Implement license key validation** | Gate MCP server startup on a valid license key |
| 11 | **Set up Stripe subscription billing** | Paper.design and most monetized MCP servers use Stripe; MCP-native payment rails are immature |
| 12 | **Set pricing at $29–79/month or $200–500/year** | Anchored to Lightwright, Savvy, Paper.design, Conveyor comparables; value justified at 10% of $5K+ annual time savings |

### Medium-Term (1–3 Months) — IP Protection Path (Paths A/B/C)

| # | Action | Rationale |
|---|--------|-----------|
| 13 | **Launch paid tier** | Even a handful of paying users dramatically increases valuation |
| 14 | **Create public lite version** | Discovery channel and social proof (stars, forks) |
| 15 | **Build acquisition package** | Architecture docs, demo videos, financial summary, customer testimonials |
| 16 | **List on Acquire.com** | Requires revenue and active customers for best listing placement |
| 17 | **Direct outreach** | Contact lighting software companies and MCP platform builders |

### Medium-Term (1–3 Months) — Marketplace Funnel Path (Path D)

| # | Action | Rationale |
|---|--------|-----------|
| 18 | **Community-first distribution** | Post on ControlBooth, MA Lighting Forum, r/lightingdesign, Facebook groups. Peer recommendation drives adoption in this market more than marketplace listing. A single respected touring programmer endorsement outweighs 10,000 MCP directory listings. |
| 19 | **Flesh out SKILL.md content** | Complete the 6 scaffolded skills in `skills/` with full domain knowledge |
| 20 | **Publish skills to marketplaces** | Submit to SkillsMP, Skills.sh, LobeHub, and GitHub simultaneously |
| 21 | **Implement credit-gating in MCP server** | Add free execution quota (15–25 commands) before requiring subscription |
| 22 | **Set up MCPize paid listing** | List MCP server with tiered pricing ($29–79/mo or $200–500/year). Secondary to community channels. |
| 23 | **Build OAuth + remote MCP server** | Enable hosted access without local installation; required for SaaS layer |
| 24 | **LDI / trade show demo** | Prepare demo for LDI 2026 (Las Vegas) or Prolight+Sound |

---

## 6. Due Diligence Checklist

What a buyer or investor will examine:

- [ ] **Code ownership** — Single author with clear copyright chain
- [ ] **License cleanliness** — No GPL dependencies that could force copyleft
- [ ] **AI contribution disclosure** — Documented and ownership asserted
- [ ] **Test coverage** — 1,498 unit tests passing in CI
- [ ] **Security posture** — No hardcoded secrets, injection prevention, safety tiers
- [ ] **Dependencies** — Review `pyproject.toml` for supply chain risk
- [ ] **Revenue data** — MRR, customer count, churn rate
- [ ] **Market validation** — GitHub stars, community engagement, user testimonials
- [ ] **Technical debt** — Version inconsistency, alpha status, missing legal docs
- [ ] **Competitive landscape** — Other MA2 control tools, MCP ecosystem maturity
- [ ] **Vendor risk** — MA Lighting's stance on third-party control tools
- [ ] **Scalability** — Path to grandMA3 support (future market)
- [ ] **Bus factor** — Knowledge transfer plan for single-author project

---

## 7. Conclusion

The GMA2 MCP project has genuine IP value rooted in specialized domain expertise that would take 8–12 weeks to replicate. However, the current Apache 2.0 license and lack of monetization infrastructure leave this value unprotected and uncaptured.

Two strategic directions are available, and the recommended path depends on the author's goals:

**IP Protection Path (Paths A/B/C):**
- **If seeking recurring revenue:** Make repo private, implement license key validation, launch with Stripe subscription billing at $29–79/month, and build a customer base
- **If seeking acquisition:** Establish even minimal revenue ($500+/month), prepare a due diligence package, and list on Acquire.com or conduct direct outreach to lighting software companies
- **If uncertain:** Start with the hybrid model — a public lite version for discovery and a private pro version for revenue — which preserves optionality for both paths

**Marketplace Funnel Path (Path D):**
- Distribute free SKILL.md knowledge skills across agent skill marketplaces for maximum reach
- Gate command execution behind a freemium MCP server subscription ($29–79/month or $200–500/year)
- Let free skills serve as the distribution channel — no need to make the repo private for skills, only for the MCP server implementation
- Leverage first-mover advantage in a vertical with zero AI competition

**Emerging MCP monetization data** (March 2026) strengthens the hybrid approach. Paper.design's MCP call metering validates tool-call gating as an accepted payment mechanism. The "Conveyor insight" — that niche markets structurally favor bootstrapped products over VC-subsidized free competitors — directly applies to this 5,000–15,000 user market. Pricing should be anchored at $29–79/month (or $200–500/year), justified by the $5,000+ annual value created through time savings. Distribution should be community-first (ControlBooth, MA forums, r/lightingdesign, LDI) rather than marketplace-first.

**The paths are not mutually exclusive.** The strongest position may be combining IP protection for the MCP server implementation (Paths A/C) with marketplace distribution for knowledge skills (Path D). This preserves the competitive moat while maximizing awareness in a small, peer-driven market.

> **Supporting materials:**
> - Market research: `doc/market-research-appendix.md`
> - Scaffolded agent skills: `skills/grandma2-*/SKILL.md` (6 files)
