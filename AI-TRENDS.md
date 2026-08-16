# 🤖 AI Trends Digest — YouTube Transcript Synthesis

**Window covered:** 2026-06-08 → 2026-07-22
**Compiled:** 2026-08-16
**Source corpus:** [`gbhambha1/ytstock`](https://github.com/gbhambha1/ytstock) `transcripts/` — 43 transcripts across 3 tracked channels
**AI-relevant transcripts used:** 11 of 43

> ⚠️ **What this is.** A synthesis of *what people said on YouTube*, not verified fact. Every number
> below is a speaker's estimate or claim unless marked otherwise. ARK Invest is an asset manager
> discussing positions it holds; LuxAlgo is selling the product it demos. Treat both as informed but
> interested parties. Not financial advice.

---

## 📡 Source coverage — read this first

The AI signal in this corpus is **heavily concentrated in one channel**. Stated plainly so the
"multiple channels" framing isn't oversold:

| Channel | Transcripts | AI-relevant | What it contributes |
|---|---|---|---|
| **ARK Invest** (@ARKInvest2015) | 18 | **10** | Essentially all of the substance — model economics, compute, labor, capital markets |
| **LuxAlgo** (@LuxAlgo) | 15 | **1** | One data point: AI as a code-generation tool for retail trading strategies |
| **Trading Notes** (@TradingNotes1) | 10 | **0** | Pure price-action / technical education. No AI content at all. |

Within ARK, three long-form *Brainstorm* episodes (135, 140, 141) carry ~85% of the argument; the
other seven are 1–3 minute clips, several of which are excerpts cut from those same episodes.

**Practical consequence:** this document is best read as *ARK Invest's evolving AI thesis over six
weeks*, cross-checked against one outside data point — not as a consensus view across independent
sources. Where the panel disagrees with itself, that's noted, because the internal disagreement is
the most useful thing in the corpus.

---

## 🎯 Executive summary — the six shifts

1. **The frontier redefined itself, again.** It went from *smartest model* → *smartest model per
   training dollar* → **smartest model per inference dollar**. Open-weight models are competing hard
   on the frontier that mattered 18 months ago, not the one that matters now.
2. **Tokens and dollars have decoupled.** On OpenRouter, ~**75% of token volume** runs on open
   models while ~**80% of spend** goes to closed ones. Any argument that cites token share is
   measuring a different thing than any argument that cites revenue.
3. **Kimi K3 is not a DeepSeek moment** — and the market's non-reaction is itself the story. Bigger
   open models mean *more* compute demand, not less. Infrastructure names didn't break.
4. **Cheap open weights ≠ cheap deployment.** Free weights still need infrastructure, an agent
   harness, a product, and a team. The margin just moves to whoever supplies those.
5. **The pressure point has moved from capability to ROI.** "Token-maxing" is over; the question in
   front of every buyer is now whether measurable productivity turns into measurable business
   results. It largely hasn't yet.
6. **Compute demand still exceeds supply, and that's the durable constraint.** Every hyperscaler is
   guiding capex up; power and data centers are the bottleneck, and the political friction against
   them is starting (New York's one-year moratorium).

---

## 1. 🏁 The frontier keeps moving — and it's now priced in dollars

The clearest through-line across Brainstorm 140 and 141.

**The stated progression of what "frontier" means:**

| Era | Frontier definition | Who wins |
|---|---|---|
| Early | Who has the smartest model | Whoever trains biggest |
| Middle | Smartest model at lowest *training* cost | Efficiency + distillation |
| **Now** | **Smartest model at lowest *inference* cost** | Whoever owns intelligence-per-dollar |

Open-weight labs are optimising for the *previous* frontier — strong benchmarks from cheap,
distilled training — which is why they look impressive on leaderboards and less impressive on cost
per completed task.

**Model landscape as described (2026-07-15):**

| Model | Claim made on the show |
|---|---|
| **GPT 5.6** | ~half the cost of GPT 5.5 for the same performance; ~half the cost of Fable with higher benchmark scores |
| **Fable** (Anthropic) | Reputed best-in-class; unclear how much of its price premium is margin vs. genuine inefficiency |
| **Gemini 3.5 Flash** | Shipped; **3.5 Pro delayed ~2 months** — read as Google re-tuning against competitor launches |
| **Meta's latest** | Better than Gemini 3.5 Flash at lower cost; "back on the leaderboard," ahead of Google on benchmarks |
| **Grok 4.5** | Behind the frontier but not far, at much lower cost; trained on xAI infra with the Cursor team and dataset |

A five-lab release cluster inside about six weeks, all emphasising efficiency. The panel's caveat on
its own chart: benchmarks are "relatively one-dimensional," but are "the best basis of comparison we
have outside of vibes." A secondary argument worth keeping: **coding benchmarks are a decent proxy
for general agentic capability**, because agent behaviour depends on coding capability.

**Products shipped alongside the models:** Anthropic's **Claude Cowork** (web + mobile enterprise
surface, so you're not tethered to an open laptop), OpenAI's **ChatGPT Work** (Codex-powered agent
across ChatGPT services), and xAI's Grok build app. Also flagged as underrated: the **new ChatGPT
voice model** — full duplex (listens and talks simultaneously) and able to delegate reasoning and
tool use to a frontier model behind the scenes, so responses stop being shallow.

**Grok predictions on the record (18-month horizon):**

| Question | Frank | Nick |
|---|---|---|
| Will Grok hold the #1 model spot? | No — but likely reaches the Pareto frontier on intelligence-vs-cost | No |
| Will it gain significant users? | Yes — better model, smaller base | Token growth > user growth; "strategically impaired" |

---

## 2. ⚖️ Open vs. closed — the metric you pick decides the answer

The single most portable insight in the corpus.

> **OpenRouter, trailing 30 days, top 20 models:** ~**75% of tokens consumed** on open models,
> ~**80% of dollars spent** on closed models.

Two opposite conclusions, both true, from the same platform. Caveats the panel itself raised: some
OpenRouter models are temporarily free; open models are cheaper on average; and **OpenRouter users
are a self-selected population** who set themselves up to switch models, so they over-represent
aggressive switchers relative to the market.

**Weekly usage leaderboard (2026-07-15) was dominated by Chinese open-weight models:**

| # | Model / lab |
|---|---|
| 1 | Tencent |
| 2 | Xiaomi |
| 3 | DeepSeek |
| 4 | MiniMax |
| 5 | Z-ai |
| 7 | **Anthropic** — first Western lab on the list |
| 8 | Nemotron 3 |

**Why dollars still favour closed** — the "weights are free, everything else isn't" argument:

- You either run your own infrastructure (only the most technically advanced companies will) or you
  pay a cloud provider's margin — ballpark **50% gross margin** on general cloud pricing.
- The agent harness to run it isn't free. The product around it isn't free. The team maintaining it
  isn't free.
- Revenue as evidence of revealed preference *(all speaker estimates)*: **Anthropic ~$60–70B run
  rate, projected ~$100B by year end**; **OpenAI "mid tens of billions"**; **open-source AI companies
  in the hundreds of millions to low billions**.

**The falsifier the panel offered on itself** — and the best thing to track from this whole
document: *if the clouds start growing faster than the frontier labs, open source is winning.*
Right now they say it isn't — **Google Cloud is the fastest-growing cloud at 63% YoY on an ~$80B run
rate**, but on the stated trajectory *Anthropic could exceed all of Google Cloud by year end*.

**Counter-pressure, from the same panel:** open weights hand enterprises a **negotiating position**
they didn't have at the last contract renewal. Expected consequence is pricing pressure on the
frontier and eventual margin compression — timing unknown, and possibly never, if inference profit
holds.

**Perception distortion worth internalising:** all-you-can-eat Pro plans mean many loud voices
*never face the marginal cost of a token* and therefore rate the most expensive model best. Above
~150 seats, or in regulated industries, you pay per token — and that's where the "why is our spend
so high" conversation lives. Same technology, two incompatible information spheres.

---

## 3. 🇨🇳 Kimi K3 — big, good, and not the disruption it was reported as

**What shipped (2026-07-22):** Moonshot's **Kimi K3**, **2.8 trillion parameters — the largest
open-source model ever released**. On benchmarks it was described as sitting "in between Opus and
Fable and GPT 5.6" — i.e. between the last generation and the current one. Chinese
competitors to Moonshot sold off **28%** on the news, and coverage framed it as a second DeepSeek
moment.

**Why the panel says it isn't:**

| Claim | The counter |
|---|---|
| "Half the price" — $15/M output tokens vs $30/M for GPT 5.6 Soul | It's **less token-efficient — ~2× the tokens to answer** — so *average cost per task lands the same*. Competitive, **not cheaper**. |
| "Open weights, so anyone can run it" | Weights weren't on US clouds until the following week; the site and API buckled and **new signups had to be turned off** |
| "Bad for compute demand" | The demand spike *proved the opposite* — that much interest needs far more compute |
| "Another DeepSeek shock" | Semis didn't break. The market already learned in January 2025 that a strong open model is a **positive** for infrastructure |

**A structural unknown, stated as unknown:** nobody outside these labs knows the real cost base — how
much is distillation of US labs' R&D, how much is state subsidy, what margin is being taken.
Evidence it's opaque: **DeepSeek V4 lists up to 10× cheaper on DeepSeek's own service than the same
model on Azure**. That gap is a business-model choice, not a technology fact.

---

## 4. 🧠 "Good enough" — the corpus's central unresolved argument

This is where the panel openly disagrees, and the disagreement is more useful than either position.

**The case for good-enough (Nick):** the frontier has gotten crowded. For a large share of knowledge
work, models are already "good enough, if not way too good." The median knowledge worker hasn't felt
a material bump in the last few releases because they'd already figured out how to do most of their
day with existing models. Recurring anxiety: the Brian Armstrong chart — **token usage inflecting up
while cost per token comes down**. That shape is the threat to model companies, not Kimi K3.

**The case for frontier (Brett):** we haven't had the agentic iPhone moment yet. Pressed on how many
tasks you can hand an agent with "do this in half an hour" and get back what you'd have produced
yourself — **"basically zero."** Sharp skepticism of the "12 hours of human work at 70% success"
framing: **if you can't tell which 30% is wrong, the 30% kills you.** Corollary: work an average
model can do is instantly commoditised in a competitive market; the edge goes to whoever augments
with the *best* model.

**The reconciliation that actually predicts behaviour** — route by task ambiguity, not by prestige:

> **Well-specified task → cheapest model that clears the bar.** Using a frontier model is overkill.
> **Ambiguous task → frontier model.** You need intelligence to fill gaps and route around
> ambiguity. A weaker model will flail, burn tokens failing, and **end up more expensive anyway.**

The empirical hook: if most tasks were cleanly definable, **RPA would be far bigger than a
couple-of-billion-dollar market** — UiPath's size is evidence that most real work is ambiguous. The
panel split on whether this generalises past software; the tentative answer was that *some* software
processes (CRM pipeline stages) are more well-defined than nominally rule-bound professional work.

**Where this lands strategically:** the more open models close the gap, the more the **orchestration
/ harness layer** matters — the thing that routes each task to the cheapest model that can do it.
OpenAI is described as holding the raw material for this: a full continuum of models across price
points, currently "packaged in a really kind of chaotic way," with intelligent routing as the
obvious next step.

**An explicit open gap — treat it as a build opportunity:** the most-used agent apps are OpenAI's and
Anthropic's own. Frank's standing call-out is that **no independent, enterprise-ready agent harness
really exists yet** — the thing you'd install or visit that isn't ChatGPT or Claude.

---

## 5. 📊 ROI — the question that replaced capability

The framing shift, in the panel's own words: *"We're not in the token-maxing Q1 2026 era anymore."*

The uncomfortable version of the question: **should models be evaluated on productivity lift to the
firm rather than on benchmarks?** It's easy to say "I'm more productive with AI." It does not follow
that sales went up. The predicted wave is companies discovering *"everyone is more productive and
our revenue is flat"* — which is a statement about the work being assigned, not about the models.

Two calibrating analogies used:

- **Electricity.** Right now people are "playing with raw electricity." Everyone touched it, everyone
  got burned, and the industry that turns it into useful output hasn't been built yet.
- **Lawyers.** Anyone who passes the bar is a lawyer; firms still pay a lot for the best one. A
  benchmark score is a credential, not a story.

**The optimistic reading of cost declines** (Frank): optimisation raises ROI, which raises willingness
to spend, which grows total spend. Prediction offered: *Coinbase spends more on AI a year from now
than today*, even with per-token cost down.

**The pessimistic reading** (Nick): cost declines are how technology evolves — and they still burn
companies caught on the wrong side. Being the supplier of the cheaper tokens is fine; being priced
against them is not.

---

## 6. ⚡ Compute, power, and the SpaceX data-center economics

**Demand still exceeds supply**, and the panel expected every major cloud to say exactly that on the
following week's earnings calls: more demand than supply, building as fast as possible, raising capex
guidance, still short. "I don't see us consuming fewer tokens in our future" — nowhere near saturated
on demand for AI intelligence.

Friction is arriving on the physical side: **data-center pushback, including New York's one-year
moratorium**. Energy infrastructure is expected to return as a constraint *harder* than in the
previous cycle.

**SpaceX's terrestrial data-center business (2026-06-10), as modelled on the show:**

| Item | Figure |
|---|---|
| SpaceX build cost | **< $30B per gigawatt** |
| Market build cost | **$45–55B per gigawatt** |
| Anthropic rental rate | **> $30B per GW** — roughly a **one-year payback** |
| Google GPU rental rate | **> $50B per GW** — implied **high-80s% gross margin** |
| Capacity rented | ~**0.8 GW of the 1 GW built** as of end Q1 2026 (~80%) |

Four buckets any gigawatt falls into — **infrastructure-as-a-service** (contracted, cash-generating),
**monetised inference** (~$30B/GW), **unmonetised inference** (free Grok queries, image gen — a bet on
later conversion), and **training** (a bet on future capability).

**The tension:** those rental contracts are cancellable and read as short-term — Anthropic wants
maximum revenue growth into an IPO and is paying premium rates. The bear case is that Elon redirects
revenue-generating capacity into training Grok, killing near-term cash flow. The charitable read is
that renting capacity **self-funds the capex** — rent out the long tail to pay for frontier training,
roughly cash-neutral, while space-based compute scales into the mid-2030s.

**Context on scale:** X was taken private 1,320 days ago at **$44B**; the re-IPO was expected at
**~$1.75T**. The underlying power-law argument: value is concentrating so steeply that the top three
or four positions run away, and the dangerous place is the middle. Enterprise AI sized at a
**~$15–20T enterprise-value opportunity**; consumer at **~$900B of revenue**, maybe **~$9T** of value.

---

## 7. 🍎 Apple — the "last 15%" problem, on schedule

From WWDC coverage (2026-06-10). Useful less as an Apple take than as the corpus's clearest statement
of *why AI products slip*.

**What was announced:** Siri renamed **"Siri AI"** with a new backend; **Apple foundation models
distilled with Google Gemini models**, split across on-device compute, Apple's private servers, and
Google Cloud; deep personal-context access (messages, photos, images, calendar); **Siri gets its own
app** so conversations are referenceable; and a **re-architected system-wide search** that Apple
Intelligence will call as a tool.

**The skepticism:** shipping is deferred to the fall, with language limits — an echo of the Apple
Intelligence announcement two years earlier that moved the stock and then largely didn't ship.

**The generalisable principle, and the best paragraph in the corpus:**

> Getting an AI prototype to **80%** is easy. Cleaning up the next **15%** (leaving 5% error) is
> roughly **300% more work than everything done so far**. This is a property of how AI systems work,
> and it leads management teams astray — the demo *almost* works, so it gets promised. Apple is
> *especially* exposed because it won't ship visible imperfection, which makes operating at the
> frontier structurally hard for them. Same dynamic as "robotaxis are almost there."

**The capability gap, in one demo:** asked about tickets not yet on sale, Siri offered to *set a
reminder*. What users now expect is **"when they drop, buy them."** The distance between those two
sentences is the distance between assistant and agent.

**The underrated asset:** Mac Mini and Mac Studio as the substrate for personally-run agents — custom
silicon, a privacy story, and sold out. Speculative strategy floated: let the phone securely command
agents running on a machine at home, effectively making the OS an orchestration layer over your own
agents. Evidence the form factor needs to change: people are buying **3D-printed doodads to hold
laptops open** so Codex or Claude Code keeps running while they carry it around.

---

## 8. 👥 Labor and macro — the counterintuitive one

**AI adopters are hiring *more*, not less.** A Ramp study cited (2026-07-14): over the two years
following ChatGPT's launch, aggressive AI adopters hired **~10% more people** than non-adopters. ARK
reports the same on itself — three engineers hired in a year, which a firm its size normally couldn't
justify, plus associate-level hiring specifically for people who are **natively AI**. Stated
expectation: *labor shortages* become the topic, not job losses.

**Unit labor costs ~0.5%** (2026-06-11) — productivity offsetting nearly all compensation increases,
the structural opposite of the cost-push inflation of the 1970s–80s. One driver named is
uncomfortable: fear of AI and robotics is making workers **less aggressive in wage demands**.

**Capex has broken a 40-year ceiling.** Cathie Wood's framing: this measure of capital spending
peaked at roughly the same level for four decades and has now broken out — the boom is *just
beginning*, and it converges with every other technology.

**Private markets:** **>$5T of private company valuation created from ~nothing in five years**, with
AI as the biggest catalyst — spinning up a company is easier than ever, and **US new company
formations are up 10–20%** since the ChatGPT moment. The defence of pre-IPO valuations against the
"money-losing at sky-high multiples" critique is time horizon plus moat: SpaceX, OpenAI and Anthropic
are described as investing aggressively now toward software-like operating margins later.

**One adopter's view from outside the labs** (Lucra, 2026-07-16) — a healthy counterweight to the
frontier discourse: *"we identified early on we are not an AI-native company… let's not try to be
one."* Partner, hire selectively, run enterprise Claude internally. Most companies are buyers of this
technology, not builders of it.

---

## 9. 📉 AI in retail trading tools — the one non-ARK data point

**LuxAlgo, 2026-06-11.** The only AI content outside ARK in the corpus, and it's a vendor demo — the
video exists to sell **LuxAlgo Quant**. Worth including because it shows what AI actually looks like
at the retail end, well below the frontier discourse.

**The workflow:** describe an indicator in natural language (or paste existing code) → Quant generates
**Pine Script** → paste into TradingView. The demo generates a **3D parameter-optimization surface**
plus a performance table for a SuperTrend across length and multiplier values, optimizable for win
rate, net profit, profit factor, average trade, or risk-reward.

**The genuinely good idea buried in the ad — stability over peak performance:**

> Yellow marks the *most profitable* parameter values. Blue marks the *most stable* ones — values
> surrounded by other profitable values, so performance doesn't lurch when a parameter moves from 4
> to 5. A robust system shouldn't change dramatically on small input changes.

That's a real defence against curve-fitting, and it's the transferable lesson: **prefer plateaus to
peaks.** Note the framing pressure — "in the next 6 months everyone will be building strategies like
this, and you need to understand or you'll be left behind" is marketing, and there is **no
out-of-sample performance evidence anywhere in the video.**

---

## 📌 Numbers index

Every figure is as stated by a speaker. None is independently verified here.

| Figure | Claim | Source |
|---|---|---|
| **2.8T params** | Kimi K3 — largest open-source model ever released | BS 141 · 07-22 |
| **$15 vs $30 /M** | Kimi K3 vs GPT 5.6 Soul output tokens — but ~2× tokens used, so parity per task | BS 141 · 07-22 |
| **28%** | Selloff in Moonshot's Chinese competitors on the K3 release | BS 141 · 07-22 |
| **75% / 80%** | OpenRouter 30-day: open models' share of *tokens* / closed models' share of *dollars* | BS 141 · 07-22 |
| **10×** | DeepSeek V4 list price gap — DeepSeek's own service vs Azure | BS 141 · 07-22 |
| **~50%** | Typical cloud gross margin you pay when running "free" open weights | BS 140 · 07-15 |
| **$60–70B → $100B** | Anthropic run-rate revenue, current → year-end estimate | BS 140 · 07-15 |
| **mid tens of $B** | OpenAI run-rate revenue estimate | BS 140 · 07-15 |
| **$100Ms – low $B** | Total revenue of open-source AI companies | BS 140 · 07-15 |
| **63% / $80B** | Google Cloud YoY growth / run rate — fastest-growing cloud | BS 140 · 07-15 |
| **< $30B/GW** | SpaceX data-center build cost vs **$45–55B/GW** market | BS 135 · 06-10 |
| **> $30B/GW** | Anthropic's rental rate — ~1-year payback for SpaceX | BS 135 · 06-10 |
| **> $50B/GW** | Google's GPU rental rate — implied high-80s% gross margin | BS 135 · 06-10 |
| **~0.8 of 1 GW** | SpaceX capacity rented as infrastructure-as-a-service, end Q1 2026 | BS 135 · 06-10 |
| **$44B → $1.75T** | X taken private 1,320 days ago → expected re-IPO valuation | BS 135 · 06-10 |
| **$15–20T / ~$900B** | Enterprise AI enterprise-value opportunity / consumer AI revenue opportunity | BS 135 · 06-10 |
| **80% → 300%** | AI prototypes reach 80% easily; the next 15% costs 3× all prior work | BS 135 · 06-10 |
| **+10%** | Extra hiring by aggressive AI adopters over 2 years (Ramp study) | 07-14 |
| **~0.5%** | Unit labor costs — productivity offsetting compensation growth | 06-11 |
| **>$5T / +10–20%** | Private value created in 5 years / rise in US new company formations | 06-11 |

---

## 🔭 What to watch next

Ordered by how much they'd change the picture, with the specific tell to look for.

1. **Cloud growth vs. frontier-lab growth.** The panel's own falsifier. If the clouds out-grow
   OpenAI and Anthropic, spend is moving to self-hosted open models and the thesis flips.
2. **Whether open-model *dollar* share rises.** Token share is noise. The 20% closed-dollar figure
   trending is the signal. It has already moved up year-over-year.
3. **Gemini 3.5 Pro.** Two months late and counting. Whether it lands at the intelligence-per-dollar
   frontier tells you if Google is competitive or re-tuning under pressure.
4. **An independent enterprise agent harness.** Named as a gap by the panel. First credible non-lab
   answer captures the orchestration layer.
5. **Hyperscaler capex guidance and power constraints.** Expected up. The New York moratorium is the
   template for the political friction to track.
6. **Any firm publishing a real productivity-to-P&L link.** Everyone claims productivity; nobody has
   shown revenue. First credible study reframes the whole ROI debate.
7. **Whether Apple ships what it demoed, in the fall, unchanged.** A clean read on the last-15%
   problem, with a two-year prior of not shipping.
8. **H100 spot pricing** — now tradeable on Kalshi compute prediction markets. Frank's call was
   **lower**, on Blackwell and Vera Rubin ramping.

---

## 🗂️ Source index

Transcripts live in [`gbhambha1/ytstock`](https://github.com/gbhambha1/ytstock) under
`transcripts/<channel-handle>/`.

### ARK Invest — @ARKInvest2015

| Date | Video | Weight |
|---|---|---|
| 2026-07-22 | [Will China's Kimi K3 Win The AI Model Race? — Brainstorm 141](https://www.youtube.com/watch?v=aQ-BxFtxVWE) | ★★★ Primary |
| 2026-07-20 | [AI Got More Expensive. Does It Even Matter?](https://www.youtube.com/watch?v=0g_fY_w_AC0) | Clip from BS 140 |
| 2026-07-17 | [Cathie Wood: The AI Boom Is Just Beginning](https://www.youtube.com/watch?v=8vnYOm5lUwc) | Short |
| 2026-07-16 | [Gamifying Loyalty — Lucra, Dylan Robbins](https://www.youtube.com/watch?v=Lw5WDTdjblA) | Adopter view |
| 2026-07-15 | [What Is The Best AI Model In 2026? — Brainstorm 140](https://www.youtube.com/watch?v=FUdfXNEFmNA) | ★★★ Primary |
| 2026-07-14 | [Why AI Adopters Are Hiring More, Not Less](https://www.youtube.com/watch?v=0LF6iWX7sVo) | Short |
| 2026-06-11 | [$5T In Private Value, Created From Nothing](https://www.youtube.com/watch?v=rPFLop94H3A) | Short |
| 2026-06-11 | [The Number That Kills The Inflation Narrative](https://www.youtube.com/watch?v=vmLy-tIbZFc) | Short |
| 2026-06-10 | [Apple WWDC, Siri AI, And SpaceX Data Centers — Brainstorm 135](https://www.youtube.com/watch?v=hc6JGYC5Zcg) | ★★★ Primary |
| 2026-06-08 | [Are The Pre-IPO Valuations Too High?](https://www.youtube.com/watch?v=yWcyBe6wmOc) | Short |

### LuxAlgo — @LuxAlgo

| Date | Video | Weight |
|---|---|---|
| 2026-06-11 | [The Greatest AI Strategy Builder On TradingView](https://www.youtube.com/watch?v=w4_i_27Ottw) | Vendor demo |

### Trading Notes — @TradingNotes1

No AI-relevant content in the 10 transcripts covering 2026-05-09 → 2026-07-02.

---

*Compiled from transcripts in `gbhambha1/ytstock`. Claims are the speakers', not the compiler's.
Not financial advice.*
