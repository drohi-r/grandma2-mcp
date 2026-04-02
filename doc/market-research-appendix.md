---
title: Market Research Appendix
description: External market data supporting the monetization strategy audit — all statistics are unverified unless noted
version: 1.1.0
created: 2026-03-12T18:00:00Z
last_updated: 2026-03-25T00:00:00Z
---

# Market Research Appendix

> **Disclaimer:** All statistics in this document are sourced from external market research (March 2026). Unless explicitly marked as "verified," these figures are unverified claims from platform marketing materials, industry reports, or third-party analysis. They should be independently confirmed before use in business decisions or investor materials.

---

## A. SKILL.md Marketplace Landscape

*Source: Platform websites and third-party reporting, March 2026. Unverified.*

| Platform | Catalog Size | Monetization | Notes |
|----------|-------------|-------------|-------|
| **SkillsMP** | 351,000+ skills | Free only (no payment mechanism) | Scrapes GitHub repositories |
| **Skills.sh** | 83,627 skills, 8M installs | Free only | Backed by Vercel, Snyk security scanning |
| **LobeHub** | Curated marketplace | Platform subscriptions ($9.90–$15/mo) | No individual skill sales |
| **ClawHub** | 3,286 verified skills | Free only | Purged after "ClawHavoc" security breach (824 malicious infostealers) |

**Key takeaway:** Catalog-rich, monetization-poor. No SKILL.md directory currently pays skill creators.

---

## B. MCP Server Registry Landscape

*Source: Platform websites and third-party reporting, March 2026. Unverified.*

**Ecosystem-wide:** Over **11,000 MCP servers** exist as of March 2026, but **fewer than 5% generate revenue**. The market resembles early mobile app stores — mostly free, with monetization infrastructure still being built.

| Platform | Catalog Size | Model | Creator Revenue |
|----------|-------------|-------|----------------|
| **Smithery.ai** | 3,305+ servers | $30/mo creator fee | None (creators pay, not earn) |
| **Glama.ai** | Consumer subscription | $9–$80/mo end-user | None for creators |
| **MCP.so** | 18,420+ servers | Pure directory | None |
| **MCPize** | Small, newer | 85/15 revenue share, Stripe Connect | Only functioning paid marketplace |
| **Apify** | Pay-per-event | ~80/20 revenue share | 130,000+ monthly signups; developers reporting $2,000+/month |
| **MCP Hive** | Pre-launch | Per-request, zero platform fees | Launching May 2026 |

**MCPize details (unverified marketing claims):**
- Subscription tiers: $9–$199/month
- One-time purchases: $5–$20
- Usage-based: $0.01–$0.10 per API call
- Claimed top earner range: $3,000–$10,000+/month
- Claimed free-to-paid conversion: 8%
- Payouts in 135+ currencies

**Proven simple models:**
- **21st.dev:** API key gate, 5 free requests, then $20/month (alternate report: 10 free credits, $16/$32/month — pricing may have changed)
- **Ref (ref.tools):** 200 free credits, then $9/month for 1,000 credits

---

## C. Freemium Conversion Case Studies

*Source: Third-party reporting and platform announcements. Unverified unless noted.*

| Product | Model | Reported Results |
|---------|-------|-----------------|
| **Paper.design** | 100 free MCP calls/week → $16–20/mo Pro (1M calls/week) | 40,000+ early access users (unverified) |
| **21st.dev** | API key gate, 5 free requests → $20/mo | £400+/mo MRR (unverified); alternate report: 10 free credits, $16/$32/mo — pricing may have changed |
| **Ref (ref.tools)** | 200 free credits → $9/mo (1,000 credits) | Hundreds of subscribers in 3 months (unverified) |
| **Zapier MCP** | 2 tasks per tool call against 100-task free limit | Drives natural upgrades (no revenue figure) |
| **Jam.dev** | 30 free Jams; MCP burns through quota | Drives natural upgrades (no revenue figure) |

**Key pattern:** Paper.design's approach — usage-gating MCP tool calls between free and paid tiers — is the most elegant model to date. It aligns cost with value: heavy MCP users get more value, so they pay.

**Broader SaaS validation (verified public figures):**

| Company | Model | Reported Scale |
|---------|-------|---------------|
| Vercel | Open-source Next.js → paid hosting | $200M ARR |
| Supabase | Open-core → managed hosting | $5B valuation, $70M ARR |
| Remotion | Source-available, paid for 3+ employee companies | License-based |

**Industry benchmark:** Typical developer tool freemium conversion runs 1–3%; well-executed products reach 6–8%.

---

## D. Lighting Industry Market Sizing

*Source: Industry reports and trade publications. Unverified unless noted.*

### D.1 Global Market

| Metric | Value | Source |
|--------|-------|--------|
| Global stage lighting control console market (2024) | $457 million | Industry report (unverified) |
| Projected market (2032) | $653 million | 5.4% CAGR projection (unverified) |
| grandMA touring/concert segment share | ~35–45% | Industry consensus (unverified) |
| grandMA ecosystem tools | 230 cataloged from 61 publishers | grandma.tools (unverified) |

### D.2 Addressable Market for AI Tooling

| Segment | Estimated Size | Characteristics |
|---------|---------------|----------------|
| Freelance lighting programmers | Largest individual segment | Own command wings ($5K–$13K), use free onPC software |
| Major production companies | 20–50 | PRG (3,000+ employees), Solotech (2,000), Christie Lites (~$137M revenue), 4Wall (12+ locations) |
| Rental houses | Dozens | MA2 consoles in rental inventory |
| Permanent installations | Hundreds | Theaters, theme parks, cruise ships, houses of worship |
| Education/training | Growing | Lighting design programs |
| **Total addressable** | **5,000–15,000 users** | Realistic range for grandMA-specific AI tooling |

### D.3 Price Sensitivity

| Category | Price Point | Observation |
|----------|------------|-------------|
| grandMA2 onPC software | Free | Industry expects free console software |
| AddOnDesk plugins | Free – €19 | Low willingness to pay for plugins |
| Most expensive grandMA tool found | $359 (LPC Full Size) | Ceiling for MA-specific software |
| Capture visualization | €395 – €2,195 | Higher prices for workflow-critical tools |
| Depence visualization | €5,000 – €15,000 | Premium tier for production tools |
| grandMA3 Full-Size console | ~$92,000 | Hardware spending is lavish |

**Paradox:** Free software expectations alongside six-figure hardware spending. Product must frame as "production tool" (Capture tier) not "plugin" (AddOnDesk tier).

### D.4 AI Adoption Status

- Professional lighting AI adoption is in **very early stages** (March 2026)
- Emerging paradigm: AI as "drafting assistant" for base cue stacks, human refinement for key scenes
- **Zero existing AI-to-grandMA automation products** in the market
- Industry quote: "You can program AI to mimic certain colors, but you're still missing the creative spark" — Chester Thompson, WSP

---

## E. Discovery Channels

*Source: Industry knowledge and trade show data. Partially verifiable.*

| Channel | Type | Reach |
|---------|------|-------|
| **MA Lighting Forum** | Online community | Primary MA user community |
| **ControlBooth** | Online community | Broader entertainment tech; strong lighting presence |
| **Facebook groups** | Social | Console-specific groups |
| **LDI** (Las Vegas) | Trade show | 14,000–16,000 attendees (unverified) |
| **Prolight+Sound** (Frankfurt) | Trade show | Major European pro lighting show |
| **PLASA** (London) | Trade show | UK/European entertainment tech |

**Adoption mechanism:** Peer recommendation is dominant. A single respected touring programmer endorsing the tool would likely drive more adoption than digital marketing.

---

## F. Competitive Landscape

*Source: Platform research, March 2026.*

| Category | Competitors | Status |
|----------|------------|--------|
| AI-to-grandMA automation | **None** | First-mover advantage |
| MCP servers for entertainment tech | **None found** | Greenfield vertical |
| grandMA plugins (AddOnDesk) | Dozens, free–€19 | Low-value, no AI component |
| Lighting visualization tools | Capture, Depence, WYSIWYG | Different category (visualization, not AI control) |
| General MCP servers | 18,420+ on MCP.so | None targeting professional lighting |

**Key insight:** Fewer than 5% of 11,000+ registered MCP servers are monetized. The entertainment technology vertical shows essentially zero MCP presence.

---

## G. MCP-Era Design Tool Case Studies

*Source: Third-party reporting on Pencil.dev and Paper.design, March 2026. Unverified unless noted.*

Two VC-backed design-to-code tools launched in 2024–2025 with native MCP servers, representing divergent monetization strategies in the AI agent era.

### G.1 Pencil.dev

- **Product:** AI design canvas embedded in VS Code, Cursor, and Windsurf. Designs save as `.pen` files in Git — version-controlled, branchable, mergeable. Built-in MCP server auto-starts when the app opens. "SWARM mode" (Feb 2026) enables multiple AI agents designing simultaneously.
- **Founder:** Tom Krcha — previously Adobe (XD, Behance), co-founded Alter avatars (acquired by Google), worked on Around (acquired by Miro)
- **Company:** High Agency, Inc., 9 employees, San Francisco
- **Funding:** a16z Speedrun (~$500K for 10% equity + $500K pro-rata rights) + Kaya VC
- **Traction:** 100,000 users by February 24, 2026 (less than a year after launch). Tom Krcha announcement tweet: 337,000 views, 3,200 retweets. Earlier "Design Mode for Cursor" tweet: 856,000 views.
- **Pricing:** Entirely free. Pricing page states: "Pencil is currently free. In the future, we may introduce paid features or plans."
- **Revenue model:** None direct. Piggybacks on paid AI subscriptions — users need Claude Code ($20/mo) or similar. Pencil provides the visual layer; Anthropic's models do the heavy lifting.
- **Distribution:** VS Code Marketplace, Cursor extension, OpenVSX, macOS desktop app, CLI, MCP server. `.claude.json` auto-generated during install. Krcha has 20,200 Twitter/X followers. No Product Hunt launch.

### G.2 Paper.design

- **Product:** Design canvas rendering real HTML/CSS (not Figma's proprietary SVG engine). Right-click any element → "Copy as React" → production-ready code. Paper Shaders — GPU-accelerated real-time effects (liquid metal, halftone CMYK, grain gradients, fluted glass). Paper Snapshot copies sections of live websites as editable layers.
- **Founder:** Stephen Haney — co-founded Modulz (acquired by WorkOS, 2022), created Radix UI (one of the most widely used React component libraries)
- **Funding:** $4.2 million seed from Accel and Basecase Capital. Angels: Guillermo Rauch (Vercel CEO), Des Traynor (Intercom co-founder), Koen Bok (Framer founder), Adrian Mato (GitHub Design Director), Adam Wathan (Tailwind creator)
- **Open source:** Paper Shaders published as npm packages (`@paper-design/shaders-react`, ~1,500 GitHub stars) — serves as marketing channel + developer tool
- **Partnership:** Tailwind CSS team (Adam Wathan) for idiomatic import/export
- **Traction:** 40,000+ early access signups. Stripe used Paper for visuals in their annual letter launch.
- **MCP server:** 24 tools including `get_selection`, `get_jsx`, `write_html`, `update_styles`, `create_artboard`. Runs locally via desktop app at `http://127.0.0.1:29979/mcp`. Works with Claude Code, Cursor, VS Code Copilot, Codex.

### G.3 Side-by-Side Comparison

| Dimension | Pencil.dev | Paper.design |
|-----------|-----------|-------------|
| **Price** | Free (indefinitely, for now) | $0 / $16–20/mo |
| **Monetization** | None yet; VC-funded growth | Freemium subscription |
| **MCP server** | Built-in, auto-starts | Built-in, usage-gated |
| **Revenue model** | Future TBD | MCP calls as metered lever |
| **Funding** | a16z Speedrun (~$1M) + Kaya VC | $4.2M seed (Accel, Basecase + angels) |
| **Users** | 100,000 (Feb 2026) | 40,000+ early access signups |
| **Open source** | Closed source | Shaders library open source |
| **Canvas technology** | Proprietary `.pen` format | HTML/CSS native |
| **AI dependency** | Requires external Claude/GPT sub | Self-contained + external AI |
| **Founder background** | Adobe XD, exits to Google + Miro | Radix UI, exit to WorkOS |

### G.4 Paper.design MCP Pricing (Key Data Point)

**MCP tool calls are the primary monetization lever.** Free users get 100 MCP calls per week — enough to try the workflow but not enough for daily production use. Pro users get a million.

| Plan | Price | MCP calls/week | Image generation | Collaboration |
|------|-------|---------------|-----------------|---------------|
| Free | $0 | 100 | Limited | Limited files |
| Pro | $16/mo (annual) / $20/mo (monthly) | 1,000,000 | 100x more/day | Unlimited files |
| Organizations | Coming soon | Custom | Custom | SSO, admin controls |

---

## H. MCP Payment Infrastructure

*Source: Platform announcements and developer tooling research, March 2026. Unverified.*

Emerging payment rails for MCP server monetization:

| Platform | Model | Status (March 2026) |
|----------|-------|-------------------|
| **Nevermined Pay** | Micropayment protocol for per-call MCP billing | Early; limited adoption |
| **Radius** | HTTP 402-based real-time payment gate | Early; developer-focused |
| **Moesif** | API/MCP usage metering and billing | More mature; metering focus |

**Key finding:** Most monetized MCP servers as of March 2026 use **simple Stripe-based subscription gates** rather than per-call micropayments. The payment infrastructure protocols above are technically interesting but too early and too unfamiliar for non-developer users. For niche professional markets (like lighting design), Stripe subscriptions are the proven path.

---

## I. Lighting Industry Pricing Comparables

*Source: Product websites and industry knowledge. Partially verifiable.*

Three pricing comparables from adjacent niche professional tool markets:

| Product | Market | Pricing | Notes |
|---------|--------|---------|-------|
| **Lightwright** (John McKernon) | Lighting paperwork — 90%+ of Broadway shows | ~$1,000 perpetual license; transitioning to subscription (announced Dec 2025) | Single developer, sustained business for decades in same market size. Proves premium pricing works in tiny professional markets. |
| **Savvy Vectorworks Plugins** (Joshua Benghiat) | Vectorworks add-ons for entertainment design | $14–60 individual tools; $39/year subscription bundle | Proves even micro-niche add-ons can monetize in entertainment tech. |
| **Conveyor** | CLI tool in small, unglamorous niche market | $45/month subscription, bootstrapped | Key insight: niche markets are *better* for bootstrapped products — no VC-funded free competitors, loyal customers, low infrastructure costs. The "Conveyor insight." |

**Value justification framework:** If an AI lighting tool saves a touring LD 30 minutes per show across 200 shows/year at $50+/hour billing rate, that represents **$5,000+ in annual value**. A $300–500/year subscription captures only 6–10% of value created — easily justifiable for working professionals.
