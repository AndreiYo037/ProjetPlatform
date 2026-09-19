# Role-Specific Rubrics — All 75 Roles

Four criteria, 1–5 each, 20 total. Slots 1 and 4 are fixed. Slots 2 and 3 are written per role below.

---

# The fixed criteria

## Slot 1 — Problem understanding

| | |
|---|---|
| **5** | Reframed the problem more sharply than we stated it. Named a constraint or assumption we hadn't. |
| **3** | Answered the question we asked, correctly, within the frame we gave. |
| **1** | Answered a different question, or restated the brief without engaging with it. |

## Slot 4 — Defence under questioning

| | |
|---|---|
| **5** | Answered directly. Conceded where we were right, held ground with reasoning where we weren't. Knew the limits of their own work. |
| **3** | Answered reasonably. Some hedging or retreat under pressure. |
| **1** | Couldn't explain their own analysis, or defended a position just shown to be wrong. |

**Why these don't vary.** They measure the person, not the craft — identical whether someone built a DCF or a campaign platform, and the two that predict hiring outcomes best. Holding them steady is what lets you compare a Finance cohort to an ESG cohort and tell a weak brief from a weak cohort.

---

# AI & Data

### AI / AI Engineering
| Slot 2 — *What worked and what didn't* | Slot 3 — *Production judgement* |
|---|---|
| **5** Eval set includes cases designed to break it, and they report the failures plainly | **5** Named the cost, latency and failure mode at our real volume, and what they'd cut to fix it |
| **3** Working prototype with a real eval set and honest pass rates | **3** Sensible architecture with stated trade-offs |
| **1** Demo that works on the happy path only, no evals, or cherry-picked examples | **1** No consideration of cost, latency, or what happens when the model is wrong |

### Machine Learning Engineering
| Slot 2 — *Modelling discipline* | Slot 3 — *Deployability* |
|---|---|
| **5** Baseline established first and beaten honestly. Leakage checked and stated. | **5** Model card names failure modes, drift triggers, and when to retrain. Runs from a clean clone. |
| **3** Correct pipeline, sensible metrics, reproducible | **3** Containerised, documented, metrics reported |
| **1** Metric reported with no baseline, or a result that leakage explains | **1** Notebook only, no path to anything running |

### Data Science
| Slot 2 — *Statistical care* | Slot 3 — *Decision relevance* |
|---|---|
| **5** Stated what the sample can't support and tested the assumption that mattered most | **5** Output maps to one decision we'd make differently tomorrow |
| **3** Appropriate method, conclusions supported, caveats mentioned | **3** Findings are relevant and clearly tied to the business |
| **1** Method chosen for familiarity, or significance claimed where none exists | **1** Interesting statistics with no decision attached |

### Data Analytics
| Slot 2 — *Data handling* | Slot 3 — *Insight to decision* |
|---|---|
| **5** Cleaning decisions documented. Caught a quality problem the brief didn't mention. | **5** Three findings, each tied to something we'd do differently. Visuals carry the argument unnarrated. |
| **3** Data prepared correctly, transformations traceable | **3** Real findings, clearly presented, relevance stated |
| **1** Silent row loss, unexplained transformations | **1** Descriptive statistics presented as insight |

### Data Engineering
| Slot 2 — *Data quality discipline* | Slot 3 — *Schema and cost judgement* |
|---|---|
| **5** Checks written for the failures these sources actually have, and states what happens when one fires | **5** Schema justified against how it would be queried, with cost at our volume and what they'd change at 10x |
| **3** Quality checks present and sensible, errors handled rather than swallowed | **3** Clean schema, sensible architecture, cost noted |
| **1** Happy path only. Breaks on the first malformed row and says nothing about it. | **1** No schema rationale, or cost never considered |

### Research and Analysis
| Slot 2 — *Source quality* | Slot 3 — *Calibrated conclusions* |
|---|---|
| **5** Primary sources over aggregators. Noticed where two sources disagree and said which to trust. | **5** Confidence levels stated and justified. Distinguished what's known from what's inferred. |
| **3** Credible sources, correctly cited, reasonably comprehensive | **3** Clear recommendation with supporting evidence |
| **1** Secondary sources uncritically repeated, or claims without attribution | **1** Equal confidence in everything, or hedging on everything |

### Healthcare Analytics
| Slot 2 — *Clinical data literacy* | Slot 3 — *Governance awareness* |
|---|---|
| **5** Understood what the coding and collection method does to the numbers before analysing them | **5** De-identification and governance handled correctly without being asked, and explained why |
| **3** Correct cohort definition, appropriate analysis, sensible visuals | **3** Governance considerations noted |
| **1** Treated clinical data as generic numbers | **1** No awareness that health data carries obligations |

---

# Engineering & Technical

### Software Engineering
| Slot 2 — *Code someone else can own* | Slot 3 — *Trade-offs under time pressure* |
|---|---|
| **5** Reads like the codebase it joins. Tests cover what would actually break it, and a stranger gets it running from the README first try. | **5** Named what they cut and why, and what they'd do first with another week. The cuts were the right ones. |
| **3** Works, tested, documented well enough to follow | **3** Some trade-offs stated, scope choices reasonable |
| **1** Works on their machine. No tests, or tests that assert nothing. | **1** Over-built one corner and left the feature unfinished, or claims no trade-offs were made |

### QA / Testing
| Slot 2 — *Coverage and prioritisation* | Slot 3 — *Reproducibility* |
|---|---|
| **5** Went where bugs live — edge cases, error states, accessibility. Severity ratings I'd agree with. | **5** Every issue reproducible from their notes first try, with environment and expected-vs-actual |
| **3** Systematic coverage of main flows, sensible severity | **3** Clear steps, reproducible with minor guesswork |
| **1** Happy paths only, severity unjustified | **1** "Page looks broken." Unreproducible. |

### Robotics
| Slot 2 — *Simulation fidelity* | Slot 3 — *Failure analysis* |
|---|---|
| **5** Sim conditions chosen to stress the controller, not flatter it. Named the sim-to-real gap. | **5** Characterised where and why it fails, not just that it succeeded |
| **3** Task runs, metrics reported, conditions stated | **3** Some failure conditions tested |
| **1** One successful run under ideal conditions | **1** No failure testing at all |

### Mechanical / Civil / Chemical
| Slot 2 — *Calculation rigour* | Slot 3 — *Standards and constraints* |
|---|---|
| **5** Assumptions explicit, factors of safety justified, hand-check against the simulation | **5** Cited the correct code sections and designed against real constraints, not idealised ones |
| **3** Correct calculations, appropriate method | **3** Relevant standards identified and applied |
| **1** Simulation output accepted without a sanity check | **1** Standards ignored, or the wrong jurisdiction's code |

### Blockchain / Web3
| Slot 2 — *Contract safety* | Slot 3 — *Economic and UX reasoning* |
|---|---|
| **5** Tested against real vulnerability classes, not just happy path. Explained what they deliberately didn't handle. | **5** Gas costs modelled at realistic usage and the end-user flow actually makes sense |
| **3** Deployed, tested, common vulnerabilities considered | **3** Cost analysis present, flow described |
| **1** Untested contract, or copy-paste with no security review | **1** No cost or usability consideration |

---

# Product & Design

### Product Management
| Slot 2 — *User evidence* | Slot 3 — *Scoping and trade-offs* |
|---|---|
| **5** Grounded in real signal. Distinguished what users said from what they meant. | **5** Cut scope deliberately and said what and why. Success metric that could actually fail. |
| **3** Real evidence cited, problem accurately characterised | **3** Well-scoped, clear requirements, metrics defined |
| **1** Assumed user needs | **1** Everything in scope, or metrics that can't be missed |

### UX / UI Design
| Slot 2 — *Diagnosis* | Slot 3 — *Craft of the solution* |
|---|---|
| **5** Found the real friction, not the ugly part. Tied each problem to a principle or evidence. | **5** Solves the diagnosed problem without creating new ones. Consistent with our system. Accessible by construction. |
| **3** Genuine usability problems correctly identified | **3** Clear improvement, internally consistent |
| **1** Aesthetic preference presented as usability finding | **1** Restyling that ignores the diagnosis |

### UX Research
| Slot 2 — *Method fit* | Slot 3 — *Synthesis* |
|---|---|
| **5** Method matched the question. Recruitment criteria defensible. Avoided leading the participant. | **5** Themes earned from the data, severity ranked, with a clear "so what" per finding |
| **3** Sound method, adequate sample, findings documented | **3** Findings organised and prioritised sensibly |
| **1** Leading questions, or a method that can't answer the question asked | **1** Quote dump with no synthesis |

### Industrial Design
| Slot 2 — *Form and use* | Slot 3 — *Manufacturability* |
|---|---|
| **5** Design decisions traceable to how the thing is actually held and used | **5** Materials and process chosen with real cost and tooling implications stated |
| **3** Coherent concept, ergonomics considered | **3** Sensible material choices, process named |
| **1** Styling with no use-context reasoning | **1** Unmakeable, or no manufacturing thought |

### Architecture
| Slot 2 — *Site and regulatory response* | Slot 3 — *Spatial resolution* |
|---|---|
| **5** Scheme is shaped by the real constraints — plot ratio, setbacks, orientation — not despite them | **5** Plan works at every scale. Circulation, daylight and programme all resolve. |
| **3** Constraints identified and respected | **3** Coherent plan meeting the brief |
| **1** Ignored zoning or site reality | **1** Renders without a resolvable plan behind them |

### Technical Writing
| Slot 2 — *Clarity of instruction* | Slot 3 — *Information architecture* |
|---|---|
| **5** A reader could complete the task on first read without guessing. Removed more than they added. | **5** Structure matches how people actually arrive at the docs, not how the product is built |
| **3** Accurate, clear, correctly structured | **3** Sensible organisation, findable content |
| **1** Reworded the original without improving comprehension | **1** Reorganised by internal logic, not user need |

---

# Business & Strategy

### Business Strategy
| Slot 2 — *Sizing discipline* | Slot 3 — *Strategic choice* |
|---|---|
| **5** Every assumption sourced and sensitised. Said which assumption the answer hinges on. | **5** Picked a play and named what we'd give up. Stated the condition that would change their mind. |
| **3** Defensible sizing, assumptions stated | **3** Clear recommendation with reasoning |
| **1** Top-down number with no build-up, or assumptions pulled from air | **1** Options with no choice made |

### Consulting
| Slot 2 — *Structure of reasoning* | Slot 3 — *Implementability* |
|---|---|
| **5** Issue tree that genuinely decomposes the problem. Every branch earns its place. | **5** Roadmap with owners, sequencing and the first thing to do Monday |
| **3** Logical structure, framework sensibly applied | **3** Recommendations are actionable in principle |
| **1** Framework applied decoratively | **1** Analysis with no path to action |

### Strategy & Corporate Analysis
| Slot 2 — *Financial literacy* | Slot 3 — *Strategic judgement* |
|---|---|
| **5** Read the segment disclosures properly and spotted what the headline numbers hide | **5** Took a position and named the trade-off. Scenarios genuinely differ, not optimistic/pessimistic. |
| **3** Financials correctly interpreted and contextualised | **3** Clear recommendation with reasoning |
| **1** Quoted revenue and margin with no interpretation | **1** No position taken |

### Innovation Sourcing
| Slot 2 — *Coverage and screening* | Slot 3 — *Partnership reasoning* |
|---|---|
| **5** Found companies we hadn't heard of. Criteria weighted and justified. | **5** Explained why each target would want to work with *us*, not just why we'd want them |
| **3** Solid landscape, sensible criteria | **3** Clear rationale per shortlist entry |
| **1** Obvious names from one search | **1** Shortlist with no reasoning |

### Procurement & Sourcing
| Slot 2 — *Spend analysis* | Slot 3 — *Negotiation strategy* |
|---|---|
| **5** Found the concentration or leakage in the category that we hadn't seen | **5** Named our actual leverage and where we have none. Target terms are achievable. |
| **3** Category correctly analysed, suppliers scored sensibly | **3** Sensible negotiation approach |
| **1** Spend listed with no structure | **1** Aggressive targets with no leverage behind them |

### Entrepreneurship / Founder
| Slot 2 — *Validation quality* | Slot 3 — *Unit economics* |
|---|---|
| **5** Collected real signal from strangers, including disconfirming evidence they reported anyway | **5** Economics built bottom-up with the assumption that kills it identified |
| **3** Talked to real potential customers, some signal collected | **3** Coherent model with stated assumptions |
| **1** Friends and family, or a landing page with no traffic | **1** Hockey stick with no cost side |

### Business Development / Partnerships
| Slot 2 — *Partner landscape* | Slot 3 — *Deal logic* |
|---|---|
| **5** Tiered by strategic fit, not size. Named who we should *not* partner with and why. | **5** Structure gives both sides a reason to sign and says what each gives up |
| **3** Sensible map with clear tiering | **3** Clear mutual value case |
| **1** A list of big logos | **1** One-sided ask |

---

# Finance

### Finance (general)
| Slot 2 — *Model integrity* | Slot 3 — *Decision framing* |
|---|---|
| **5** Clean build, assumptions traceable, sensitivities isolate the real driver | **5** Recommendation names the threshold at which the answer flips |
| **3** Correct mechanics, assumptions stated | **3** Clear recommendation with reasoning |
| **1** Broken links, circularity, or unsourced inputs | **1** Numbers presented with no decision attached |

### Investment Banking
| Slot 2 — *Model integrity* | Slot 3 — *Valuation judgement* |
|---|---|
| **5** Clean build, assumptions traceable to filings, sensitivities isolate the value drivers | **5** Explained why methods disagree and which to trust here. Comp set defended on operating similarity. |
| **3** Correct mechanics, plausible output | **3** Sensible range, methods appropriately applied |
| **1** Broken model or unsourced assumptions | **1** Point estimate as truth, comps by sector tag |

### Venture Capital
| Slot 2 — *Diligence depth* | Slot 3 — *Investment judgement* |
|---|---|
| **5** Found something about the company or market that isn't in the pitch deck | **5** Named the one thing that has to be true, and what would make them pass |
| **3** Thorough memo covering market, team, traction, risk | **3** Clear recommendation with risks acknowledged |
| **1** Restated the company's own marketing | **1** Enthusiasm with no risk analysis |

### Private Equity
| Slot 2 — *LBO mechanics* | Slot 3 — *Value creation logic* |
|---|---|
| **5** Debt structure realistic, covenants considered, returns decomposed into their sources | **5** Named operational levers with evidence they're available, not generic cost-cutting |
| **3** Model builds correctly, returns sensitised | **3** Credible value creation plan |
| **1** Leverage assumed with no capacity check | **1** "Improve margins" with no mechanism |

### Asset & Wealth Management
| Slot 2 — *Portfolio construction* | Slot 3 — *Client translation* |
|---|---|
| **5** Allocation justified against a stated objective and risk tolerance, correlations considered | **5** A non-expert could read the summary and know what they own and why |
| **3** Sensible allocation, attribution correctly done | **3** Clear client-facing explanation |
| **1** Allocation with no objective behind it | **1** Jargon that assumes finance literacy |

### Quantitative Trading
| Slot 2 — *Backtest hygiene* | Slot 3 — *Intellectual honesty* |
|---|---|
| **5** Out-of-sample tested, transaction costs included, survivorship and look-ahead addressed | **5** Said plainly why the result may not survive live, and what they'd test next |
| **3** Clean backtest with performance and drawdown stats | **3** Overfitting risk acknowledged |
| **1** In-sample results, no costs, no lookahead check | **1** Sharpe ratio presented as fact |

### Tax
| Slot 2 — *Technical accuracy* | Slot 3 — *Practical judgement* |
|---|---|
| **5** Cited the right provisions and distinguished settled treatment from grey area | **5** Flagged where the planning is aggressive and what the exposure would be |
| **3** Correct rules identified and applied | **3** Compliance considerations noted |
| **1** Wrong jurisdiction, or guidance treated as binding | **1** Planning proposed with no risk discussion |

### Actuarial Science
| Slot 2 — *Assumption discipline* | Slot 3 — *Sensitivity insight* |
|---|---|
| **5** Every assumption sourced and justified, with the basis for deviation from the table stated | **5** Identified which assumption the answer is most exposed to and by how much |
| **3** Model correct, assumptions documented | **3** Sensitivities run across key drivers |
| **1** Table applied without adjustment or comment | **1** Single-point result with no sensitivity |

### Corporate Development / M&A
| Slot 2 — *Screening rigour* | Slot 3 — *Synergy realism* |
|---|---|
| **5** Criteria weighted to our actual strategy. Named strong companies they excluded and why. | **5** Synergies quantified with a mechanism, integration risk named honestly |
| **3** Sensible matrix, defensible shortlist | **3** Valuation range with stated synergy assumptions |
| **1** Screened on size and sector alone | **1** Synergy number with no source |

### Fintech
| Slot 2 — *Product teardown* | Slot 3 — *Regulatory awareness* |
|---|---|
| **5** Walked the actual flows and found the friction a user would hit but never report | **5** Mapped where each feature touches licensing or compliance, correctly |
| **3** Thorough comparison, real differences identified | **3** Relevant regulatory touchpoints named |
| **1** Compared feature lists from marketing pages | **1** Feature proposed with no regulatory thought |

### Real Estate
| Slot 2 — *Model integrity* | Slot 3 — *Market judgement* |
|---|---|
| **5** Assumptions sourced from real transaction data, sensitivity shows the true driver | **5** Comps genuinely comparable with adjustments justified. Named the risk that breaks the deal. |
| **3** Model builds correctly, assumptions stated | **3** Reasonable comps, market view supported |
| **1** Hardcoded assumptions or circular references | **1** Comps chosen for convenience, no downside |

---

# Marketing, Sales & Media

### Marketing (general)
| Slot 2 — *Positioning clarity* | Slot 3 — *Measurement thinking* |
|---|---|
| **5** Positioning that excludes someone. Named who this is not for. | **5** KPIs that could show failure, with a baseline and a time frame |
| **3** Clear positioning and messaging by segment | **3** Sensible metrics defined |
| **1** Positioning that would fit any competitor | **1** Vanity metrics, or "increase awareness" |

### Brand Management
| Slot 2 — *Audit honesty* | Slot 3 — *Architecture* |
|---|---|
| **5** Named the gap between what we say we are and how we're actually perceived, with evidence | **5** Messaging architecture that holds across audiences without becoming vague |
| **3** Competent audit against competitors | **3** Clear positioning statement and hierarchy |
| **1** Described our brand back to us | **1** A word cloud of adjectives |

### Advertising & Media Planning
| Slot 2 — *Channel logic* | Slot 3 — *Budget realism* |
|---|---|
| **5** Mix justified by where the audience actually is and what each channel does in the funnel | **5** Flighting and reach/frequency stand up to arithmetic at the stated budget |
| **3** Sensible mix with audience rationale | **3** Plan is internally consistent |
| **1** Every channel included, no rationale | **1** Budget can't buy the reach claimed |

### Creative Strategist
| Slot 2 — *Strength of insight* | Slot 3 — *Creative leap* |
|---|---|
| **5** A true and uncomfortable observation about the audience, evidenced. Something we hadn't said out loud. | **5** Executions that could only come from that insight. Flexes across formats without breaking. |
| **3** Real insight, supported, relevant | **3** Ideas connect to the insight and fit the brand |
| **1** A demographic fact presented as insight | **1** Executions that would fit any insight |

### Content Creation / Copywriting
| Slot 2 — *Craft of the writing* | Slot 3 — *Strategic coherence* |
|---|---|
| **5** I'd publish this as-is. Voice consistent, every line earns its place. | **5** Pillars map to real audience questions, and the calendar has a reason for its sequence |
| **3** Clean, on-brand, publishable with light editing | **3** Coherent calendar with clear pillars |
| **1** Generic content that could be about anything | **1** A posting schedule with no strategy |

### Social Media Management
| Slot 2 — *Platform fluency* | Slot 3 — *Community thinking* |
|---|---|
| **5** Content built for how each platform actually behaves, not cross-posted | **5** Playbook covers the awkward cases — complaints, silence, a post that lands badly |
| **3** Format-appropriate content, sensible cadence | **3** Sensible engagement guidelines |
| **1** One asset resized for every platform | **1** "Respond promptly and positively" |

### PR & Communications
| Slot 2 — *Newsworthiness* | Slot 3 — *Crisis judgement* |
|---|---|
| **5** Found an angle a journalist would actually run, and matched it to the right named reporter | **5** Holding statement that says something without conceding what shouldn't be conceded |
| **3** Competent release, relevant media list | **3** Sensible crisis plan with clear escalation |
| **1** Press release about a non-event, generic media list | **1** A statement that would inflame the situation |

### Tech Sales
| Slot 2 — *ICP definition* | Slot 3 — *Outreach craft* |
|---|---|
| **5** Defined from evidence, including who to disqualify. Named the trigger making an account worth calling now. | **5** Copy I'd actually send. Specific, short, with a reason to reply that isn't about us. |
| **3** Coherent ICP with sensible criteria | **3** Competent personalised sequence |
| **1** "Companies that need our product" | **1** Template spam about our features |

### Sales (Enterprise / B2B)
| Slot 2 — *Account intelligence* | Slot 3 — *Value case* |
|---|---|
| **5** Mapped the buying committee including the likely blocker, and found their stated priority in a filing | **5** Business case in the buyer's own metrics, with a number they'd recognise |
| **3** Solid account plan with stakeholder map | **3** Clear value proposition |
| **1** Org chart from LinkedIn with no insight | **1** Our features restated as benefits |

### E-Commerce
| Slot 2 — *Funnel diagnosis* | Slot 3 — *Test design* |
|---|---|
| **5** Walked the real flow and found the specific step that leaks, with evidence for why | **5** Tests are prioritised by expected impact and are actually runnable at our traffic |
| **3** Sensible friction points identified | **3** Reasonable test plan with success criteria |
| **1** Generic CRO checklist | **1** Tests we could never power |

### Journalism
| Slot 2 — *Sourcing* | Slot 3 — *Narrative discipline* |
|---|---|
| **5** Primary sources, including one who didn't want to talk. Verified the central claim independently. | **5** Structure serves the story. Nothing overstated beyond what the reporting supports. |
| **3** Real sources, accurate, adequately verified | **3** Clear, well-structured piece |
| **1** Rewrote existing coverage | **1** Conclusions the reporting doesn't carry |

### Film & Video Production
| Slot 2 — *Craft* | Slot 3 — *Brief translation* |
|---|---|
| **5** Shot choices, pacing and sound all serve the idea. Watchable twice. | **5** The cut delivers the brief's message in the first three seconds and holds it |
| **3** Competently shot and edited, on-brief | **3** Clear treatment executed faithfully |
| **1** Technically rough in ways that distract | **1** Attractive footage that doesn't say anything |

### Music
| Slot 2 — *Production quality* | Slot 3 — *Brief fit* |
|---|---|
| **5** Mix translates across headphones and phone speaker. Arrangement has intent. | **5** Serves the brand and the placement, not just the artist's taste |
| **3** Clean production, coherent arrangement | **3** Matches the reference and the brief |
| **1** Muddy, unbalanced, or unfinished | **1** Good track, wrong brief |

### Fashion & Luxury
| Slot 2 — *Trend reading* | Slot 3 — *Commercial judgement* |
|---|---|
| **5** Distinguished a durable shift from a passing moment, with evidence | **5** Assortment reflects real price architecture and who actually buys at each tier |
| **3** Accurate trend analysis, relevant to the category | **3** Coherent direction with sensible range logic |
| **1** Repeated trend-report headlines | **1** Aesthetically strong, commercially unviable |

### Sports & Entertainment
| Slot 2 — *Audience analysis* | Slot 3 — *Activation and valuation* |
|---|---|
| **5** Segmented the fanbase by behaviour, not demographics, and found the underserved group | **5** Sponsorship valued against comparable deals with a measurement plan that could show failure |
| **3** Sound audience analysis with real data | **3** Credible concept with stated metrics |
| **1** "Young people like short video" | **1** Valuation with no comparables |

---

# Consumer & Research

### Consumer Insights
| Slot 2 — *Instrument quality* | Slot 3 — *Segmentation usefulness* |
|---|---|
| **5** Questions avoid leading and bias. Sample limitations stated before conclusions drawn. | **5** Segments differ in ways we could actually act on — different products, messages or channels |
| **3** Sound survey design, adequate responses | **3** Defensible segments grounded in data |
| **1** Leading questions or a sample that can't support the claim | **1** Demographic buckets relabelled as personas |

### Consumer Research
| Slot 2 — *Method justification* | Slot 3 — *Confidence calibration* |
|---|---|
| **5** Chose the method because of what the question needs, and said what it can't reveal | **5** Findings ranked by how much the evidence actually supports them |
| **3** Appropriate method, clean fieldwork | **3** Findings clearly presented with implications |
| **1** Method chosen by convenience | **1** Every finding asserted with equal confidence |

### Market Research
| Slot 2 — *Sizing build* | Slot 3 — *Competitive read* |
|---|---|
| **5** Bottom-up and top-down cross-checked. Named which assumption moves the answer most. | **5** Shares estimated with a stated method, and the structural trend that changes them |
| **3** Defensible sizing, sources cited | **3** Accurate landscape and share picture |
| **1** A number from a report, uncited | **1** Logo slide with no analysis |

### CPG
| Slot 2 — *Category and shelf read* | Slot 3 — *Concept commerciality* |
|---|---|
| **5** Walked the shelf and found the price or space gap nobody is occupying | **5** Concept has a buyer, a price point and a reason a retailer would list it |
| **3** Accurate category analysis with pricing ladder | **3** Coherent concept with clear positioning |
| **1** Desk research with no shelf reality | **1** Product idea with no route to market |

### Travel & Hospitality
| Slot 2 — *Experience audit* | Slot 3 — *Commercial redesign* |
|---|---|
| **5** Actually went, and found the friction guests feel but never write a review about | **5** Fix is costed against the revenue or rating it would move |
| **3** Thorough journey map with real pain points | **3** Sensible service improvement proposed |
| **1** Summarised existing reviews | **1** Improvements with no cost or impact estimate |

---

# People & Organisation

### HR / People Ops
| Slot 2 — *Benchmarking quality* | Slot 3 — *Change realism* |
|---|---|
| **5** Compared against companies we actually compete with for talent, not household names | **5** Named what will resist the change and how to sequence around it |
| **3** Relevant benchmarks, sound policy review | **3** Sensible recommendations with implementation noted |
| **1** Compared us to Google | **1** Policy recommendation with no change plan |

### Learning & Development
| Slot 2 — *Gap analysis rigour* | Slot 3 — *Instructional design* |
|---|---|
| **5** Gap derived from our own job postings against a real framework, not assumed | **5** Module has objectives, practice and an assessment that could fail someone |
| **3** Credible gap analysis, sensible curriculum | **3** Coherent module with clear objectives |
| **1** Generic skills list | **1** Slides with no practice or assessment |

---

# Legal, Policy & Public

### Compliance & Regulatory
| Slot 2 — *Regulatory accuracy* | Slot 3 — *Gap prioritisation* |
|---|---|
| **5** Correct instruments and sections. Distinguished binding requirement from guidance. | **5** Ranked by actual exposure. Said which to fix first and why. |
| **3** Correct regulations identified and summarised | **3** Gaps identified with a risk view |
| **1** Wrong jurisdiction, or guidance presented as law | **1** Undifferentiated checklist |

### Policy Analyst
| Slot 2 — *Evidence review* | Slot 3 — *Options realism* |
|---|---|
| **5** Engaged with the strongest opposing evidence rather than the weakest | **5** Options differ in ways a decision-maker could act on, with political feasibility named |
| **3** Sound evidence base, fairly represented | **3** Clear options with a recommendation |
| **1** Cherry-picked support for a predetermined position | **1** Options that are obviously one real choice and two straw men |

### Government & Public Sector
| Slot 2 — *Service diagnosis* | Slot 3 — *Implementation realism* |
|---|---|
| **5** Mapped the journey as citizens experience it, including the steps that happen offline | **5** Proposal accounts for budget cycles, staffing and the agency that has to deliver it |
| **3** Accurate journey map with real friction points | **3** Sensible proposal with cost considered |
| **1** Reviewed the website only | **1** Recommendation ignoring how government actually works |

### International Relations
| Slot 2 — *Analytical framing* | Slot 3 — *Risk calibration* |
|---|---|
| **5** Interests mapped to what actors actually do, not what they say | **5** Risks ranked by likelihood and impact, with the indicator to watch for each |
| **3** Sound stakeholder analysis with evidence | **3** Credible risk assessment |
| **1** Restated news coverage | **1** Everything flagged as high risk |

### Criminal Justice
| Slot 2 — *Data handling* | Slot 3 — *Causal caution* |
|---|---|
| **5** Understood what the recording practice does to the numbers before analysing | **5** Distinguished correlation from effect, and named the confounder that matters |
| **3** Correct analysis, appropriate visuals | **3** Findings presented with caveats |
| **1** Treated reported crime as incidence | **1** Causal claims from cross-sectional data |

### Social Justice
| Slot 2 — *Impact analysis* | Slot 3 — *Stakeholder realism* |
|---|---|
| **5** Disaggregated the impact and found who bears the cost that the headline hides | **5** Strategy accounts for who has power here and what would actually move them |
| **3** Sound equity assessment with evidence | **3** Credible stakeholder map and plan |
| **1** Asserted disparate impact without data | **1** Advocacy plan with no theory of influence |

### Nonprofit & Social Impact
| Slot 2 — *Theory of change* | Slot 3 — *Funder fit* |
|---|---|
| **5** Causal chain is testable, with an indicator that could show the programme isn't working | **5** Proposal written in the funder's stated priorities, with a budget that adds up |
| **3** Coherent theory of change with outcome indicators | **3** Credible case for support |
| **1** Activities listed as outcomes | **1** Generic appeal sent to a specific funder |

### Urban Planning
| Slot 2 — *Spatial analysis* | Slot 3 — *Community and feasibility* |
|---|---|
| **5** Used the spatial data to find something site visits alone wouldn't show | **5** Proposal names who loses from it and how that's addressed |
| **3** Competent site and zoning analysis | **3** Feasible proposal with community impact noted |
| **1** Mapped without analysing | **1** Proposal that ignores existing residents |

### Education / EdTech
| Slot 2 — *Learning design* | Slot 3 — *Evaluation thinking* |
|---|---|
| **5** Objectives, activities and assessment genuinely aligned. Anticipated where learners get stuck. | **5** Pilot could actually show the thing doesn't work, with a realistic comparison |
| **3** Coherent unit with clear objectives and assessment | **3** Sensible pilot with defined metrics |
| **1** Content delivery with assessment bolted on | **1** Evaluation that can only confirm success |

### Trust & Safety
| Slot 2 — *Policy construction* | Slot 3 — *Adjudication consistency* |
|---|---|
| **5** Policy is enforceable at scale by a reviewer with 30 seconds. Edge cases named in advance. | **5** Cases decided consistently, with reasoning that would survive an appeal |
| **3** Clear policy with sensible escalation | **3** Sound adjudications with stated reasoning |
| **1** Principles that can't be operationalised | **1** Inconsistent calls, or reasoning that contradicts the policy |

---

# Health & Life Sciences

### Pharmaceuticals
| Slot 2 — *Pipeline literacy* | Slot 3 — *Access judgement* |
|---|---|
| **5** Read trial design and endpoints properly, not just phase and indication | **5** Named the payer or pricing constraint that decides whether this matters commercially |
| **3** Accurate landscape and pipeline map | **3** Sensible market access considerations |
| **1** Listed assets by phase with no read | **1** Clinical analysis with no commercial lens |

### Biotech & Life Sciences
| Slot 2 — *Scientific rigour* | Slot 3 — *Translational judgement* |
|---|---|
| **5** Weighed evidence quality, not just abundance. Noted where the field disagrees. | **5** Named the specific technical risk between here and a product |
| **3** Thorough, accurate review of the literature | **3** Credible feasibility assessment |
| **1** Abstracts summarised uncritically | **1** Treated preclinical promise as translatable |

### Medical Devices
| Slot 2 — *Regulatory pathway* | Slot 3 — *Human factors and reimbursement* |
|---|---|
| **5** Correct classification with a named predicate, and the evidence that pathway demands | **5** Usability risks tied to actual use environment, and a reimbursement route identified |
| **3** Correct pathway identified and described | **3** Sound usability review, landscape mapped |
| **1** Wrong class or wrong jurisdiction | **1** Design review with no clinical context |

### Public Health / Epidemiology
| Slot 2 — *Epidemiological method* | Slot 3 — *Intervention judgement* |
|---|---|
| **5** Denominators right, confounders addressed, limitations stated before conclusions | **5** Weighed the evidence base against what's deliverable in this setting |
| **3** Sound analysis with appropriate visuals | **3** Evidence-based intervention proposed |
| **1** Raw counts presented as rates | **1** Recommended what works elsewhere with no context fit |

---

# Sustainability & Industrials

### Sustainability / ESG
| Slot 2 — *Framework command* | Slot 3 — *Materiality judgement* |
|---|---|
| **5** Right framework, correctly applied, and knew why that one. Separated mandatory from voluntary here. | **5** Told us which two or three disclosures matter to our stakeholders and why the rest can wait |
| **3** Recognised framework used accurately | **3** Real gaps identified and sensibly ranked |
| **1** Framework named but misapplied | **1** Every gap listed with no prioritisation |

### Energy & Renewables
| Slot 2 — *Techno-economic modelling* | Slot 3 — *Policy and siting realism* |
|---|---|
| **5** LCOE built from real cost data with the input that drives it isolated | **5** Accounted for the actual grid, tariff and permitting conditions at that site |
| **3** Correct model, assumptions stated | **3** Relevant incentives and constraints identified |
| **1** Generic cost assumptions from a headline figure | **1** Model with no policy or siting context |

### Environmental Science
| Slot 2 — *Monitoring analysis* | Slot 3 — *Mitigation practicality* |
|---|---|
| **5** Understood detection limits and sampling design before interpreting the data | **5** Mitigation is proportionate, costed and actually implementable at this site |
| **3** Correct analysis with clear visualisation | **3** Sensible mitigation proposed |
| **1** Interpreted noise as signal | **1** Recommendations with no feasibility |

### Automotive & Mobility
| Slot 2 — *Operational analysis* | Slot 3 — *Service viability* |
|---|---|
| **5** Modelled the real duty cycle, including dwell, charging and utilisation troughs | **5** Unit economics hold at realistic utilisation, not best case |
| **3** Sound analysis with sensible assumptions | **3** Coherent concept with stated economics |
| **1** Range and cost figures from spec sheets | **1** Economics that only work at 90% utilisation |

### Telecommunications
| Slot 2 — *Network and data analysis* | Slot 3 — *Commercial reasoning* |
|---|---|
| **5** Distinguished coverage from experienced quality, and found where they diverge | **5** Investment case weighs churn, ARPU and capex against a real competitive response |
| **3** Accurate analysis of coverage or pricing | **3** Credible business case |
| **1** Restated published coverage claims | **1** Capex proposal with no return case |

---

# Authoring one for a new role

Four steps, about twenty minutes at programme setup.

1. **Name the two craft criteria.** Ask what the two ways of doing this job badly are. Usually one is *technical execution*, one is *judgement applied to the output*.
2. **Write the 1 anchor first.** The failure mode is easier to name than excellence and it calibrates everything else. Describe something you've actually seen a junior person do.
3. **Write the 5 anchor from intake question 5** — the host's answer to *"what would make you say that's better than I expected"*, in their words.
4. **Write 3 as competent-but-unremarkable.** Not "good" — what a capable person produces on a normal day.

**Test before publishing:** could two reps read this and score the same submission three points apart? If yes, the anchors are too vague.

---

# Note

Your list drops **Talent Acquisition**, which was in the earlier resource map and is a strong fit — the candidate-experience audit of a company's own public application process is cheap for them to verify and immediately useful. Add it back if that was a trim rather than a decision. Its criteria would be *Funnel diagnosis* and *Assessment design*.
