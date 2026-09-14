# Complete Resource Map — All 75 Roles

For each role: what's publicly available, what the company could supply if willing, and what tooling the student needs.

## How to use the company-provided column

Every item is tagged by how hard it is for a company to say yes.

- **[E] Easy** — no legal review. A person's time, something already public or client-facing, a written description. An SME founder or an enterprise function head can approve this in a day.
- **[M] Moderate** — one internal sign-off. Anonymised extracts, internal-but-not-sensitive documents, a tool seat. Realistic for SMEs and startups; possible at enterprises with a sponsor who pushes.
- **[H] Hard** — legal, security review, or an NDA. Customer records, pre-release financials, production access, anything with PII. Assume no at enterprise scale. Don't ask during the sale; it starts a conversation that costs you two months.

**Design rule:** every challenge must be fully completable using only the public column plus [E] items. Anything [M] or [H] is an upgrade that makes the project better, never a dependency. If a student is blocked waiting on a company asset, the programme has failed.

## The baseline every role needs

Don't repeat these per role.

**Always provided by you:** cohort Discord/Slack, Google Meet link, submission folder per student, the validated data pack, rubric, milestone briefs, recorded sessions.

**Always asked of the company [E]:** a recorded brief video (once), a named host with bio and LinkedIn, one live Q&A, async feedback on three curated submissions, attendance at finals.

**Baseline student stack (all free):** Google Workspace · an LLM (Claude, ChatGPT, or Gemini free tier) · Google Colab · GitHub · Loom · Zotero or similar for citations · Canva or Google Slides.

Role-specific additions only are listed below.

---

## AI & Data

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| AI / AI Engineering | Public docs, help centre, published PDFs, public API spec; HuggingFace datasets; RAGAS, promptfoo | [E] API sandbox key with rate limits · [E] list of real user questions they get asked · [M] internal FAQ or knowledge base export · [H] production logs | Python, LangChain or LlamaIndex, a vector DB free tier (Pinecone/Chroma), LLM API credits |
| Machine Learning Engineering | Kaggle, HuggingFace, UCI, data.gov.sg, World Bank | [M] anonymised historical dataset · [E] description of the prediction target and how it's used · [H] labelled production data | Python, scikit-learn, PyTorch, Colab GPU, Docker |
| Data Science | data.gov.sg, SingStat, Our World in Data, FRED, sector datasets | [M] anonymised extract · [E] which decision the output feeds · [E] their current rule-of-thumb as a baseline to beat | Python, pandas, Jupyter, statsmodels |
| Data Analytics | data.gov.sg, SingStat, LTA DataMall, WHO, World Bank, Kaggle | [M] a CSV export with identifiers stripped · [E] their KPI definitions · [E] what the dashboard would replace | Python or SQL, Power BI Desktop, Tableau Public, Looker Studio, DuckDB |
| Data Engineering | data.gov.sg, SingStat, LTA DataMall, public APIs, Kaggle; dbt and Great Expectations docs | [E] which sources they already pull and how often · [E] what the pipeline would feed · [M] their current schema or warehouse structure · [H] production warehouse access | Python, dbt Core, DuckDB, Dagster or Airflow free tier, Docker |
| Research and Analysis | Annual reports, filings, industry association publications, Google Scholar, statistical releases | [E] their framing of the question · [E] internal hypothesis to test · [M] past research they've commissioned | Zotero, Perplexity, Google Scholar |
| Healthcare Analytics | WHO GHO, MOH statistics, HealthHub, CMS public use files, Synthea | [M] aggregated operational metrics (no patient data) · [E] pathway description · [H] any patient-level data — never ask | Python, pandas, Power BI, Synthea generator |

## Engineering & Technical

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Software Engineering | **Requires a public API, SDK or open-source repo to build against.** Their public API docs and SDK, their open-source repos, public changelog and issue tracker; language and framework docs | [E] API sandbox key with rate limits · [E] a feature they cut and why · [E] their code review standards or style guide · [M] staging environment access · [H] their private codebase | GitHub, their SDK or API, Docker, a test framework (pytest/Jest/JUnit), language toolchain |
| QA / Testing | Live public site and app, WCAG 2.2, BrowserStack free tier, Lighthouse, axe DevTools | [E] known issue list · [E] which flows matter most commercially · [M] staging environment access · [H] production credentials | Playwright or Cypress, BrowserStack free, axe, screen reader (NVDA/VoiceOver) |
| Robotics | Gazebo, Isaac Sim, ROS packages, benchmark task definitions, open perception datasets | [E] task specification and success criteria · [M] CAD of the target platform · [M] logged sensor data | ROS2, Gazebo or Isaac, Python/C++, Colab |
| Mechanical / Civil / Chemical | Singapore Standards, BCA codes, URA and OneMap, Eurocodes, manufacturer datasheets, NIST materials | [E] design constraints and requirements · [M] site survey or as-built drawings · [M] existing process flow diagram | Fusion 360 or FreeCAD (edu licences), ANSYS student, OpenFOAM, AutoCAD edu |
| Blockchain / Web3 | Etherscan, Dune Analytics, DefiLlama, public testnets, OpenZeppelin | [E] the mechanism they want modelled · [M] their existing contract addresses · [H] mainnet deploy keys | Hardhat or Foundry, Remix, testnet faucet, MetaMask |

## Product & Design

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Product Management | App/Play Store review APIs, public changelog, competitor products, Reddit API | [E] roadmap themes and current priorities · [E] why a past feature was cut · [M] anonymised usage funnel numbers · [H] analytics access | Figma, Notion, Amplitude free tier, review-scraping scripts |
| UX / UI Design | Live product, public design system or brand page, Figma Community, WCAG | [E] brand assets and fonts · [E] known usability complaints · [M] their Figma library as view-only | Figma, Maze free tier, Stark for contrast |
| UX Research | Public product, student-recruited participants, Maze/UserTesting free tiers, NN/g heuristics | [E] the research question and past assumptions · [M] recruitment help reaching real users · [H] existing customer contact list | Figma, Maze, Otter or Whisper for transcripts, Dovetail free tier |
| Industrial Design | Product photography and teardowns, Google Patents, Espacenet, materials databases, retail observation | [E] use context and target user · [M] physical sample units to handle · [M] manufacturing constraints | Fusion 360, Blender, KeyShot edu, Procreate |
| Architecture | URA Master Plan and zoning, OneMap, BCA Green Mark, site photography, planning guidelines | [E] programme brief and area requirements · [M] site survey · [M] existing drawings | Rhino or SketchUp edu, Revit edu, Enscape, QGIS |
| Technical Writing | Public docs, API reference, help centre, Google and Microsoft style guides, Diátaxis | [E] support ticket themes (the questions users keep asking) · [E] their style preferences · [M] internal docs to rewrite | Markdown, Docusaurus or MkDocs, Vale linter, Hemingway |

## Business & Strategy

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Business Strategy | SGX filings, SEC EDGAR, industry association data, Statista free tier, trade publications | [E] which markets they've already ruled out and why · [M] their own market share estimate · [H] internal strategy documents | Excel/Sheets, Slides, Miro free tier |
| Consulting | Company and competitor filings, sector reports, statistical releases, earnings transcripts | [E] the decision to be made and by when · [E] constraints they can't move · [M] prior analysis already done | Excel, Slides, Miro |
| Strategy & Corporate Analysis | Annual reports, SGX announcements, transcripts, analyst commentary, segment disclosures | [E] which business unit and why now · [M] segment detail beyond public disclosure · [H] board materials | Excel, Slides |
| Innovation Sourcing | Crunchbase free tier, accelerator cohorts, Google Patents, exhibitor lists, EnterpriseSG directory | [E] screening criteria and deal-breakers · [E] companies already evaluated · [M] internal tech roadmap themes | Airtable, Crunchbase free, Google Patents |
| Procurement & Sourcing | GeBIZ tenders and awards, supplier disclosures, commodity indices, UN Comtrade | [M] anonymised spend by category · [E] current pain points with suppliers · [H] contracts and pricing | Excel, Power BI |
| Entrepreneurship / Founder | Student-run interviews, Google Trends, app store data, market sizing sources | [E] mentor time from a founder · [M] intro to 3 potential customers | Figma, Carrd or Framer, Tally, Stripe test mode |
| Business Development / Partnerships | LinkedIn, company sites, press releases, association member lists, partnership announcements | [E] partnership criteria and past failures · [M] target list they've already built · [H] existing partner terms | Airtable, LinkedIn, Lusha or Apollo free tier |

## Finance

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Finance (general) | SGX filings, SEC EDGAR, yfinance, FRED, annual reports | [E] the capital decision framing · [M] anonymised cost structure ratios · [H] actual budget | Excel, Python/pandas |
| Investment Banking | EDGAR and SGX filings, Yahoo Finance, M&A press releases, transcripts | [E] the deal thesis to test · [M] their own comp set · [H] live mandate detail | Excel, CapIQ if the company has a seat [M] |
| Venture Capital | Crunchbase free tier, company sites, Google Patents, accelerator cohorts, founder podcasts | [E] investment thesis and stage focus · [E] why they passed on recent deals · [M] anonymised pipeline | Airtable, Notion, Excel |
| Private Equity | Listed filings, Yahoo Finance, FRED rates, public comps | [E] the target profile they want screened · [M] their return hurdle assumptions | Excel |
| Asset & Wealth Management | yfinance, factsheets and prospectuses, MAS published data, FRED | [E] client archetype to build for · [M] their model portfolio structure · [H] client data | Excel, Python, Portfolio Visualizer |
| Quantitative Trading | yfinance, Alpha Vantage, Stooq, FRED, exchange APIs, Ken French library | [E] the signal family to explore · [M] their backtest framework conventions · [H] proprietary data | Python, pandas, backtrader or vectorbt, Colab |
| Tax | IRAS e-Tax guides, OECD tax database, treaty texts, published rulings | [E] the structure to analyse (generalised) · [M] anonymised entity map · [H] actual filings | Word/Docs, Zotero |
| Actuarial Science | SingStat life tables, SOA public tables, WHO mortality, insurer annual reports | [E] the product to price · [M] anonymised claims frequency ratios · [H] policyholder data | Excel, R or Python |
| Corporate Development / M&A | SGX and SEC filings, deal press releases, landscape sources, Crunchbase | [E] strategic criteria · [E] adjacencies they care about · [H] live target list | Excel, Airtable |
| Fintech | Public product walkthroughs and pricing, MAS notices, app store reviews, competitor teardowns | [E] sandbox account on their own product · [E] regulatory constraints they operate under · [M] product roadmap themes | Figma, Postman, their public sandbox |
| Real Estate | URA transaction data, HDB resale prices, OneMap, REIT reports, rental indices | [E] the asset type and hold period assumptions · [M] their underwriting template · [H] actual deal terms | Excel, QGIS, OneMap API |

## Marketing, Sales & Media

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Marketing (general) | Public channels, competitor sites, Google Trends, industry reports, app store positioning | [E] positioning they've tried · [E] budget order of magnitude · [M] past campaign results at a high level | Sheets, Canva, Google Trends |
| Brand Management | Brand page and press kit, competitor assets, Google Trends, review sentiment, Wayback Machine | [E] brand guidelines · [E] what they think the brand stands for · [M] past brand tracker results | Figma, Canva, Miro |
| Advertising & Media Planning | Meta Ad Library, TikTok Creative Center, rate cards, Statista free tier | [E] target audience definition · [E] budget range · [M] past media mix | Sheets, Meta Ad Library, Google Ads Keyword Planner |
| Creative Strategist | Meta Ad Library, TikTok Creative Center, YouTube Data API, campaign archives, trend sources | [E] brand assets and tone · [E] campaigns that flopped and why · [M] audience research they hold | Figma, CapCut, Canva, Meta Ad Library |
| Content Creation / Copywriting | Existing public content, competitor content, Google Trends, Reddit API | [E] tone of voice guide · [E] topics they can't discuss · [M] content performance data | Google Docs, Grammarly, Canva, Ahrefs free tools |
| Social Media Management | Public profiles, TikTok Creative Center, public engagement metrics, platform trend reports | [E] brand assets · [E] approval constraints · [M] native analytics screenshots · [H] account access | Canva, CapCut, Later or Buffer free tier |
| PR & Communications | Coverage archives, journalist bylines, press releases, Google News, publication mastheads | [E] spokesperson availability for a mock interview · [E] topics that are off-limits · [M] past crisis playbook | Docs, Muck Rack free search, Google Alerts |
| Tech Sales | LinkedIn, company sites, job postings as intent signals, funding announcements, G2 and Capterra | [E] ICP definition and won/lost reasons · [E] a real discovery call recording, redacted · [M] CRM field definitions · [H] CRM access | Lusha or Apollo free tier, LinkedIn, Sheets |
| Sales (Enterprise / B2B) | Target filings and annual reports, LinkedIn org mapping, published priorities, transcripts | [E] the named target account · [E] their qualification framework · [M] a past proposal, redacted | Sheets, Slides, LinkedIn Sales Nav trial |
| E-Commerce | Live storefront, competitor checkouts, Baymard research, app store reviews | [E] which step they believe leaks · [M] anonymised funnel conversion rates · [H] GA4 access | Sheets, Hotjar free tier, Lighthouse |
| Journalism | Student interviews, public records and filings, published data, archives | [E] access to one interviewee · [E] background briefing | Otter or Whisper, Docs |
| Film & Video Production | Brand footage archives, stock libraries, reference reels | [E] brand assets and logo files · [E] usage rights for existing footage · [M] product units to shoot | CapCut or DaVinci Resolve, Canva, stock free tiers |
| Music | Reference catalogues, royalty-free sample libraries, sync brief examples | [E] the brief and reference tracks · [M] stems or brand sonic assets | Reaper or Ableton trial, Splice free, Audacity |
| Fashion & Luxury | Retail observation, public lookbooks, resale pricing data, trend publications | [E] category and price architecture · [M] past season sell-through at a high level | Figma, Canva, Sheets |
| Sports & Entertainment | Attendance and viewership data, sponsorship disclosures, social engagement metrics | [E] rights inventory description · [M] past activation results | Sheets, Canva, Slides |

## Consumer & Research

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Consumer Insights | Student-run surveys, app store reviews, Reddit API, YouTube comments, category data | [E] the segment they care about · [E] their current persona set to challenge · [M] past survey data | Tally or Google Forms, Python/pandas, Miro |
| Consumer Research | Student-recruited participants, published category studies, review corpora | [E] research question · [M] incentive budget for respondents · [M] recruitment access | Forms, Otter, Dovetail free tier |
| Market Research | SingStat, data.gov.sg, association reports, filings, Statista free tier, trade publications | [E] market definition boundaries · [M] their own sizing to compare against | Sheets, Slides |
| CPG | Shelf observation, e-commerce listings and pricing, review data, category reports | [E] product samples · [E] category they want examined · [M] trade margin structure | Sheets, Canva, phone camera |
| Travel & Hospitality | Review platforms, published rate and occupancy data, STB statistics, field visits | [E] one comped stay or visit for the audit · [M] anonymised guest feedback themes | Sheets, Canva |

## People & Organisation

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| HR / People Ops | Competitor policies and benefits pages, MOM labour statistics, employer award criteria, academic instruments | [E] the policy to review · [E] what's driving the review · [M] anonymised aggregate engagement scores · [H] individual responses | Forms, Sheets, Docs |
| Learning & Development | Public job postings, SkillsFuture Skills Frameworks, competency models, open course catalogues | [E] the role family and level · [E] what training exists today · [M] internal competency framework | Articulate trial or Google Slides, Forms |

## Legal, Policy & Public

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Compliance & Regulatory | MAS notices, PDPC guidelines, HSA and IMDA publications, EU texts, enforcement actions | [E] the product and markets in scope · [M] their current control list at a high level · [H] audit findings | Docs, Sheets |
| Policy Analyst | Parliamentary records, consultation papers, data.gov.sg, OECD and World Bank databases, academic literature | [E] their position and what they're lobbying for · [M] past submissions | Docs, Zotero, Sheets |
| Government & Public Sector | Service standards and performance data, citizen-facing services, agency annual reports | [E] the service to review · [E] known complaints themes · [M] internal process map | Miro, Docs |
| International Relations | UN Comtrade, World Bank indicators, GDELT, treaty databases, think tank publications | [E] the market or corridor in question · [M] their own risk register | Docs, Sheets, Flourish |
| Criminal Justice | Court judgments, police and prison statistics, BJS equivalents, academic datasets | [E] the programme to evaluate · [M] anonymised programme outcome data | Python, R, Docs |
| Social Justice | Census and household microdata, equity audits, NGO reports, consultation records | [E] the policy or product in scope · [M] community contacts for consultation | Docs, Miro, Sheets |
| Nonprofit & Social Impact | Charity annual reports and Charity Portal filings, impact frameworks, funder priorities, IRIS+ | [E] their theory of change if one exists · [E] target funder · [M] past grant applications | Docs, Sheets, Miro |
| Urban Planning | URA Master Plan and zoning, OneMap, LTA DataMall, OpenStreetMap, census tracts, site visits | [E] the site and brief · [M] site survey or feasibility study | QGIS, SketchUp, OneMap API, Illustrator edu |
| Education / EdTech | Published curricula, MOE resources, What Works Clearinghouse, course catalogues, app reviews | [E] learner profile and constraints · [M] existing curriculum materials · [M] pilot classroom access | Slides, Forms, Articulate trial |
| Trust & Safety | Platform community guidelines, transparency reports, DSA and Online Safety Act, Oversight Board decisions | [E] the harm category in scope · [E] their current policy text · [M] anonymised sample cases · [H] real reported content | Docs, Sheets, Miro |

## Health & Life Sciences

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Pharmaceuticals | clinicaltrials.gov, openFDA, EMA assessment reports, pipeline disclosures, PubMed | [E] therapeutic area and geography · [M] their published pipeline in more detail · [H] anything pre-disclosure | Zotero, Sheets, Slides |
| Biotech & Life Sciences | PubMed, bioRxiv, Google Patents, clinicaltrials.gov, scientific publications | [E] the target or mechanism · [E] a scientist for one Q&A · [H] unpublished data | Zotero, Benchling free, Slides |
| Medical Devices | FDA 510(k) and PMA databases, HSA device register, EU MDR guidance, reimbursement schedules | [E] device class and intended use · [M] published IFU and labelling · [H] design history file | Docs, Sheets, Figma |
| Public Health / Epidemiology | WHO GHO, MOH statistics, Our World in Data, GBD, Cochrane | [E] the population and outcome of interest · [M] programme delivery data, aggregated | R or Python, QGIS, Docs |

## Sustainability & Industrials

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Sustainability / ESG | SGX sustainability reports, CDP, GRI database, SASB, TCFD and ISSB frameworks, NEA data | [E] their published report and peer set · [E] which framework they're moving to · [M] activity data behind Scope 1/2 · [H] unpublished Scope 3 | Excel, GHG Protocol calculation tools, Power BI |
| Energy & Renewables | EMA statistics, IEA free datasets, IRENA cost databases, NREL ATB, PPA and tariff data | [E] the technology and site type · [M] their capex assumptions · [H] actual PPA terms | Excel, SAM (NREL), PVsyst trial, QGIS |
| Environmental Science | NEA and PUB monitoring data, Copernicus and NASA Earth data, published EIAs, NParks records | [E] the site or discharge in scope · [M] their own monitoring records | QGIS, R, Google Earth Engine |
| Automotive & Mobility | LTA DataMall, vehicle registration data, OpenStreetMap, charging network locations, EV specs | [E] the fleet profile and duty cycle · [M] anonymised telematics sample · [H] live fleet data | Python, QGIS, Sheets |
| Telecommunications | IMDA coverage and QoS data, operator annual reports, public pricing, Ookla open data | [E] the market and segment · [M] anonymised churn rates · [H] subscriber data | Python, Sheets, QGIS |

---

## Three patterns worth pulling out

**The best [E] ask in the whole table is "what did you already try, and why didn't it work?"** It costs the company nothing, it's not confidential, and it saves students from re-running a dead end. It appears in some form for nearly every role and is consistently the highest-value thing a function head can hand over.

**Tool licences are an underused [M] ask.** Extern's financial planning programme gives externs eMoney, Morningstar, Redtail and Asset-Map seats. A company with spare licences can hand over professional tooling without touching a single row of data — no legal review, and the student's CV gains a named industry tool. Ask for this before you ask for data.

**The [H] column is mostly there to tell you what not to ask for.** Run down it before any enterprise call. Every item on it converts a two-week sale into a two-month one, and in almost every case the public column plus [E] items produces work the company will still find useful.
