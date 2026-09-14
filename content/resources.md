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
| AI / AI Engineering | Public docs, help centre, published PDFs, public API spec, [HuggingFace datasets](https://huggingface.co/datasets), [RAGAS](https://docs.ragas.io), [promptfoo](https://www.promptfoo.dev) | [E] API sandbox key with rate limits · [E] list of real user questions they get asked · [M] internal FAQ or knowledge base export · [H] production logs | Python, LangChain or LlamaIndex, a vector DB free tier (Pinecone/Chroma), LLM API credits |
| Machine Learning Engineering | [Kaggle](https://www.kaggle.com), [HuggingFace](https://huggingface.co), [UCI](https://archive.ics.uci.edu), [data.gov.sg](https://data.gov.sg), [World Bank](https://data.worldbank.org) | [M] anonymised historical dataset · [E] description of the prediction target and how it's used · [H] labelled production data | Python, scikit-learn, PyTorch, Colab GPU, Docker |
| Data Science | [data.gov.sg](https://data.gov.sg), [SingStat](https://www.singstat.gov.sg), [Our World in Data](https://ourworldindata.org), [FRED](https://fred.stlouisfed.org), sector datasets | [M] anonymised extract · [E] which decision the output feeds · [E] their current rule-of-thumb as a baseline to beat | Python, pandas, Jupyter, statsmodels |
| Data Analytics | [data.gov.sg](https://data.gov.sg), [SingStat](https://www.singstat.gov.sg), [LTA DataMall](https://datamall.lta.gov.sg), [WHO](https://www.who.int), [World Bank](https://data.worldbank.org), [Kaggle](https://www.kaggle.com) | [M] a CSV export with identifiers stripped · [E] their KPI definitions · [E] what the dashboard would replace | Python or SQL, Power BI Desktop, Tableau Public, Looker Studio, DuckDB |
| Data Engineering | [data.gov.sg](https://data.gov.sg), [SingStat](https://www.singstat.gov.sg), [LTA DataMall](https://datamall.lta.gov.sg), public APIs, [Kaggle](https://www.kaggle.com) | [E] which sources they already pull and how often · [E] what the pipeline would feed · [M] their current schema or warehouse structure · [H] production warehouse access | Python, dbt Core, DuckDB, Dagster or Airflow free tier, Docker |
| Research and Analysis | Annual reports, filings, industry association publications, [Google Scholar](https://scholar.google.com), statistical releases | [E] their framing of the question · [E] internal hypothesis to test · [M] past research they've commissioned | Zotero, Perplexity, Google Scholar |
| Healthcare Analytics | [WHO GHO](https://www.who.int/data/gho), [MOH statistics](https://www.moh.gov.sg/resources-statistics), [HealthHub](https://www.healthhub.sg), [CMS public use files](https://www.cms.gov/data-research), [Synthea](https://synthea.org) | [M] aggregated operational metrics (no patient data) · [E] pathway description · [H] any patient-level data — never ask | Python, pandas, Power BI, Synthea generator |

## Engineering & Technical

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Software Engineering | Their public API docs and SDK, their open-source repos, public changelog and issue tracker, language and framework docs | [E] confirmation they have a public API, SDK or open-source repo to build against — required, this role cannot run without one · [E] API sandbox key with rate limits · [E] a feature they cut and why · [E] their code review standards or style guide · [M] staging environment access · [H] their private codebase | GitHub, their SDK or API, Docker, a test framework (pytest/Jest/JUnit), language toolchain |
| QA / Testing | Live public site and app, [WCAG 2.2](https://www.w3.org/TR/WCAG22), [BrowserStack free tier](https://www.browserstack.com), [Lighthouse](https://developer.chrome.com/docs/lighthouse), [axe DevTools](https://www.deque.com/axe) | [E] known issue list · [E] which flows matter most commercially · [M] staging environment access · [H] production credentials | Playwright or Cypress, BrowserStack free, axe, screen reader (NVDA/VoiceOver) |
| Robotics | [Gazebo](https://gazebosim.org), [Isaac Sim](https://developer.nvidia.com/isaac/sim), [ROS packages](https://www.ros.org), benchmark task definitions, open perception datasets | [E] task specification and success criteria · [M] CAD of the target platform · [M] logged sensor data | ROS2, Gazebo or Isaac, Python/C++, Colab |
| Mechanical / Civil / Chemical | [Singapore Standards](https://www.singaporestandardseshop.sg), [BCA codes](https://www1.bca.gov.sg/regulatory-info/building-control), [URA and OneMap](https://www.onemap.gov.sg), [Eurocodes](https://eurocodes.jrc.ec.europa.eu), manufacturer datasheets, [NIST materials](https://webbook.nist.gov/chemistry) | [E] design constraints and requirements · [M] site survey or as-built drawings · [M] existing process flow diagram | Fusion 360 or FreeCAD (edu licences), ANSYS student, OpenFOAM, AutoCAD edu |
| Blockchain / Web3 | [Etherscan](https://etherscan.io), [Dune Analytics](https://dune.com), [DefiLlama](https://defillama.com), public testnets, [OpenZeppelin](https://www.openzeppelin.com/contracts) | [E] the mechanism they want modelled · [M] their existing contract addresses · [H] mainnet deploy keys | Hardhat or Foundry, Remix, testnet faucet, MetaMask |

## Product & Design

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Product Management | App/Play Store review APIs, public changelog, competitor products, [Reddit API](https://www.reddit.com/dev/api) | [E] roadmap themes and current priorities · [E] why a past feature was cut · [M] anonymised usage funnel numbers · [H] analytics access | Figma, Notion, Amplitude free tier, review-scraping scripts |
| UX / UI Design | Live product, public design system or brand page, [Figma Community](https://www.figma.com/community), [WCAG](https://www.w3.org/WAI/standards-guidelines/wcag) | [E] brand assets and fonts · [E] known usability complaints · [M] their Figma library as view-only | Figma, Maze free tier, Stark for contrast |
| UX Research | Public product, student-recruited participants, [Maze/UserTesting free tiers](https://maze.co), [NN/g heuristics](https://www.nngroup.com/articles/ten-usability-heuristics) | [E] the research question and past assumptions · [M] recruitment help reaching real users · [H] existing customer contact list | Figma, Maze, Otter or Whisper for transcripts, Dovetail free tier |
| Industrial Design | Product photography and teardowns, [Google Patents](https://patents.google.com), [Espacenet](https://worldwide.espacenet.com), materials databases, retail observation | [E] use context and target user · [M] physical sample units to handle · [M] manufacturing constraints | Fusion 360, Blender, KeyShot edu, Procreate |
| Architecture | [URA Master Plan and zoning](https://www.ura.gov.sg/Corporate/Guidelines/Development-Control/Master-Plan), [OneMap](https://www.onemap.gov.sg), [BCA Green Mark](https://www1.bca.gov.sg/buildsg/sustainability/green-mark-certification-scheme), site photography, planning guidelines | [E] programme brief and area requirements · [M] site survey · [M] existing drawings | Rhino or SketchUp edu, Revit edu, Enscape, QGIS |
| Technical Writing | Public docs, API reference, help centre, [Google and Microsoft style guides](https://developers.google.com/style), [Diátaxis](https://diataxis.fr) | [E] support ticket themes (the questions users keep asking) · [E] their style preferences · [M] internal docs to rewrite | Markdown, Docusaurus or MkDocs, Vale linter, Hemingway |

## Business & Strategy

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Business Strategy | [SGX filings](https://www.sgx.com/securities/company-announcements), [SEC EDGAR](https://www.sec.gov/edgar), industry association data, [Statista free tier](https://www.statista.com), trade publications | [E] which markets they've already ruled out and why · [M] their own market share estimate · [H] internal strategy documents | Excel/Sheets, Slides, Miro free tier |
| Consulting | Company and competitor filings, sector reports, statistical releases, earnings transcripts | [E] the decision to be made and by when · [E] constraints they can't move · [M] prior analysis already done | Excel, Slides, Miro |
| Strategy & Corporate Analysis | Annual reports, [SGX announcements](https://www.sgx.com/securities/company-announcements), transcripts, analyst commentary, segment disclosures | [E] which business unit and why now · [M] segment detail beyond public disclosure · [H] board materials | Excel, Slides |
| Innovation Sourcing | [Crunchbase free tier](https://www.crunchbase.com), accelerator cohorts, [Google Patents](https://patents.google.com), exhibitor lists, [EnterpriseSG directory](https://www.enterprisesg.gov.sg) | [E] screening criteria and deal-breakers · [E] companies already evaluated · [M] internal tech roadmap themes | Airtable, Crunchbase free, Google Patents |
| Procurement & Sourcing | [GeBIZ tenders and awards](https://www.gebiz.gov.sg), supplier disclosures, commodity indices, [UN Comtrade](https://comtrade.un.org) | [M] anonymised spend by category · [E] current pain points with suppliers · [H] contracts and pricing | Excel, Power BI |
| Entrepreneurship / Founder | Student-run interviews, [Google Trends](https://trends.google.com), app store data, market sizing sources | [E] mentor time from a founder · [M] intro to 3 potential customers | Figma, Carrd or Framer, Tally, Stripe test mode |
| Business Development / Partnerships | LinkedIn, company sites, press releases, association member lists, partnership announcements | [E] partnership criteria and past failures · [M] target list they've already built · [H] existing partner terms | Airtable, LinkedIn, Lusha or Apollo free tier |

## Finance

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Finance (general) | [SGX filings](https://www.sgx.com/securities/company-announcements), [SEC EDGAR](https://www.sec.gov/edgar), [yfinance](https://pypi.org/project/yfinance), [FRED](https://fred.stlouisfed.org), annual reports | [E] the capital decision framing · [M] anonymised cost structure ratios · [H] actual budget | Excel, Python/pandas |
| Investment Banking | [EDGAR and SGX filings](https://www.sec.gov/edgar), [Yahoo Finance](https://finance.yahoo.com), M&A press releases, transcripts | [E] the deal thesis to test · [M] their own comp set · [H] live mandate detail | Excel, CapIQ if the company has a seat [M] |
| Venture Capital | [Crunchbase free tier](https://www.crunchbase.com), company sites, [Google Patents](https://patents.google.com), accelerator cohorts, founder podcasts | [E] investment thesis and stage focus · [E] why they passed on recent deals · [M] anonymised pipeline | Airtable, Notion, Excel |
| Private Equity | Listed filings, [Yahoo Finance](https://finance.yahoo.com), [FRED rates](https://fred.stlouisfed.org/categories/22), public comps | [E] the target profile they want screened · [M] their return hurdle assumptions | Excel |
| Asset & Wealth Management | [yfinance](https://pypi.org/project/yfinance), factsheets and prospectuses, [MAS published data](https://eservices.mas.gov.sg/statistics), [FRED](https://fred.stlouisfed.org) | [E] client archetype to build for · [M] their model portfolio structure · [H] client data | Excel, Python, Portfolio Visualizer |
| Quantitative Trading | [yfinance](https://pypi.org/project/yfinance), [Alpha Vantage](https://www.alphavantage.co), [Stooq](https://stooq.com), [FRED](https://fred.stlouisfed.org), exchange APIs, [Ken French library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) | [E] the signal family to explore · [M] their backtest framework conventions · [H] proprietary data | Python, pandas, backtrader or vectorbt, Colab |
| Tax | [IRAS e-Tax guides](https://www.iras.gov.sg/taxes/e-tax-guides), [OECD tax database](https://www.oecd.org/tax/tax-policy/tax-database), treaty texts, published rulings | [E] the structure to analyse (generalised) · [M] anonymised entity map · [H] actual filings | Word/Docs, Zotero |
| Actuarial Science | SingStat life tables, [SOA public tables](https://www.soa.org/resources/experience-studies), [WHO mortality](https://www.who.int/data/data-collection-tools/who-mortality-database), insurer annual reports | [E] the product to price · [M] anonymised claims frequency ratios · [H] policyholder data | Excel, R or Python |
| Corporate Development / M&A | [SGX and SEC filings](https://www.sgx.com/securities/company-announcements), deal press releases, landscape sources, [Crunchbase](https://www.crunchbase.com) | [E] strategic criteria · [E] adjacencies they care about · [H] live target list | Excel, Airtable |
| Fintech | Public product walkthroughs and pricing, [MAS notices](https://www.mas.gov.sg/regulation/notices), app store reviews, competitor teardowns | [E] sandbox account on their own product · [E] regulatory constraints they operate under · [M] product roadmap themes | Figma, Postman, their public sandbox |
| Real Estate | [URA transaction data](https://www.ura.gov.sg/Corporate/Property/Property-Data), [HDB resale prices](https://data.gov.sg/collections/189/view), [OneMap](https://www.onemap.gov.sg), REIT reports, rental indices | [E] the asset type and hold period assumptions · [M] their underwriting template · [H] actual deal terms | Excel, QGIS, OneMap API |

## Marketing, Sales & Media

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Marketing (general) | Public channels, competitor sites, [Google Trends](https://trends.google.com), industry reports, app store positioning | [E] positioning they've tried · [E] budget order of magnitude · [M] past campaign results at a high level | Sheets, Canva, Google Trends |
| Brand Management | Brand page and press kit, competitor assets, [Google Trends](https://trends.google.com), review sentiment, [Wayback Machine](https://web.archive.org) | [E] brand guidelines · [E] what they think the brand stands for · [M] past brand tracker results | Figma, Canva, Miro |
| Advertising & Media Planning | [Meta Ad Library](https://www.facebook.com/ads/library), [TikTok Creative Center](https://ads.tiktok.com/business/creativecenter), rate cards, [Statista free tier](https://www.statista.com) | [E] target audience definition · [E] budget range · [M] past media mix | Sheets, Meta Ad Library, Google Ads Keyword Planner |
| Creative Strategist | [Meta Ad Library](https://www.facebook.com/ads/library), [TikTok Creative Center](https://ads.tiktok.com/business/creativecenter), [YouTube Data API](https://developers.google.com/youtube/v3), campaign archives, trend sources | [E] brand assets and tone · [E] campaigns that flopped and why · [M] audience research they hold | Figma, CapCut, Canva, Meta Ad Library |
| Content Creation / Copywriting | Existing public content, competitor content, [Google Trends](https://trends.google.com), [Reddit API](https://www.reddit.com/dev/api) | [E] tone of voice guide · [E] topics they can't discuss · [M] content performance data | Google Docs, Grammarly, Canva, Ahrefs free tools |
| Social Media Management | Public profiles, [TikTok Creative Center](https://ads.tiktok.com/business/creativecenter), public engagement metrics, platform trend reports | [E] brand assets · [E] approval constraints · [M] native analytics screenshots · [H] account access | Canva, CapCut, Later or Buffer free tier |
| PR & Communications | Coverage archives, journalist bylines, press releases, Google News, publication mastheads | [E] spokesperson availability for a mock interview · [E] topics that are off-limits · [M] past crisis playbook | Docs, Muck Rack free search, Google Alerts |
| Tech Sales | LinkedIn, company sites, job postings as intent signals, funding announcements, [G2 and Capterra](https://www.g2.com) | [E] ICP definition and won/lost reasons · [E] a real discovery call recording, redacted · [M] CRM field definitions · [H] CRM access | Lusha or Apollo free tier, LinkedIn, Sheets |
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
| Consumer Insights | Student-run surveys, app store reviews, [Reddit API](https://www.reddit.com/dev/api), YouTube comments, category data | [E] the segment they care about · [E] their current persona set to challenge · [M] past survey data | Tally or Google Forms, Python/pandas, Miro |
| Consumer Research | Student-recruited participants, published category studies, review corpora | [E] research question · [M] incentive budget for respondents · [M] recruitment access | Forms, Otter, Dovetail free tier |
| Market Research | [SingStat](https://www.singstat.gov.sg), [data.gov.sg](https://data.gov.sg), association reports, filings, [Statista free tier](https://www.statista.com), trade publications | [E] market definition boundaries · [M] their own sizing to compare against | Sheets, Slides |
| CPG | Shelf observation, e-commerce listings and pricing, review data, category reports | [E] product samples · [E] category they want examined · [M] trade margin structure | Sheets, Canva, phone camera |
| Travel & Hospitality | Review platforms, published rate and occupancy data, STB statistics, field visits | [E] one comped stay or visit for the audit · [M] anonymised guest feedback themes | Sheets, Canva |

## People & Organisation

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| HR / People Ops | Competitor policies and benefits pages, [MOM labour statistics](https://stats.mom.gov.sg), employer award criteria, academic instruments | [E] the policy to review · [E] what's driving the review · [M] anonymised aggregate engagement scores · [H] individual responses | Forms, Sheets, Docs |
| Learning & Development | Public job postings, [SkillsFuture Skills Frameworks](https://www.skillsfuture.gov.sg/skills-framework), competency models, open course catalogues | [E] the role family and level · [E] what training exists today · [M] internal competency framework | Articulate trial or Google Slides, Forms |

## Legal, Policy & Public

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Compliance & Regulatory | [MAS notices](https://www.mas.gov.sg/regulation/notices), [PDPC guidelines](https://www.pdpc.gov.sg/guidelines-and-consultation), [HSA and IMDA publications](https://www.hsa.gov.sg/announcements), EU texts, enforcement actions | [E] the product and markets in scope · [M] their current control list at a high level · [H] audit findings | Docs, Sheets |
| Policy Analyst | [Parliamentary records](https://sprs.parl.gov.sg), consultation papers, [data.gov.sg](https://data.gov.sg), [OECD and World Bank databases](https://data.oecd.org), academic literature | [E] their position and what they're lobbying for · [M] past submissions | Docs, Zotero, Sheets |
| Government & Public Sector | [Service standards and performance data](https://www.gov.sg/data), citizen-facing services, agency annual reports | [E] the service to review · [E] known complaints themes · [M] internal process map | Miro, Docs |
| International Relations | [UN Comtrade](https://comtrade.un.org), [World Bank indicators](https://data.worldbank.org/indicator), [GDELT](https://www.gdeltproject.org), treaty databases, think tank publications | [E] the market or corridor in question · [M] their own risk register | Docs, Sheets, Flourish |
| Criminal Justice | [Court judgments](https://www.judiciary.gov.sg/judgments), [police and prison statistics](https://www.police.gov.sg/media-room/statistics), [BJS equivalents](https://bjs.ojp.gov), academic datasets | [E] the programme to evaluate · [M] anonymised programme outcome data | Python, R, Docs |
| Social Justice | Census and household microdata, equity audits, NGO reports, consultation records | [E] the policy or product in scope · [M] community contacts for consultation | Docs, Miro, Sheets |
| Nonprofit & Social Impact | [Charity annual reports and Charity Portal filings](https://www.charities.gov.sg), impact frameworks, funder priorities, [IRIS+](https://iris.thegiin.org) | [E] their theory of change if one exists · [E] target funder · [M] past grant applications | Docs, Sheets, Miro |
| Urban Planning | [URA Master Plan and zoning](https://www.ura.gov.sg/Corporate/Guidelines/Development-Control/Master-Plan), [OneMap](https://www.onemap.gov.sg), [LTA DataMall](https://datamall.lta.gov.sg), OpenStreetMap, census tracts, site visits | [E] the site and brief · [M] site survey or feasibility study | QGIS, SketchUp, OneMap API, Illustrator edu |
| Education / EdTech | Published curricula, [MOE resources](https://www.moe.gov.sg/microsites), [What Works Clearinghouse](https://ies.ed.gov/ncee/wwc), course catalogues, app reviews | [E] learner profile and constraints · [M] existing curriculum materials · [M] pilot classroom access | Slides, Forms, Articulate trial |
| Trust & Safety | Platform community guidelines, transparency reports, [DSA and Online Safety Act](https://digital-strategy.ec.europa.eu/en/policies/dsa-enforcement), [Oversight Board decisions](https://www.oversightboard.com/decision) | [E] the harm category in scope · [E] their current policy text · [M] anonymised sample cases · [H] real reported content | Docs, Sheets, Miro |

## Health & Life Sciences

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Pharmaceuticals | [clinicaltrials.gov](https://clinicaltrials.gov), [openFDA](https://open.fda.gov), [EMA assessment reports](https://www.ema.europa.eu/en/medicines), pipeline disclosures, [PubMed](https://pubmed.ncbi.nlm.nih.gov) | [E] therapeutic area and geography · [M] their published pipeline in more detail · [H] anything pre-disclosure | Zotero, Sheets, Slides |
| Biotech & Life Sciences | [PubMed](https://pubmed.ncbi.nlm.nih.gov), [bioRxiv](https://www.biorxiv.org), [Google Patents](https://patents.google.com), [clinicaltrials.gov](https://clinicaltrials.gov), scientific publications | [E] the target or mechanism · [E] a scientist for one Q&A · [H] unpublished data | Zotero, Benchling free, Slides |
| Medical Devices | [FDA 510(k) and PMA databases](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPMN/pmn.cfm), [HSA device register](https://eservice.hsa.gov.sg/prism/common/enquirepublic/SearchRegisteredMD.do), [EU MDR guidance](https://health.ec.europa.eu/medical-devices-sector/new-regulations_en), reimbursement schedules | [E] device class and intended use · [M] published IFU and labelling · [H] design history file | Docs, Sheets, Figma |
| Public Health / Epidemiology | [WHO GHO](https://www.who.int/data/gho), [MOH statistics](https://www.moh.gov.sg/resources-statistics), [Our World in Data](https://ourworldindata.org), [GBD](https://www.healthdata.org/research-analysis/gbd), [Cochrane](https://www.cochranelibrary.com) | [E] the population and outcome of interest · [M] programme delivery data, aggregated | R or Python, QGIS, Docs |

## Sustainability & Industrials

| Role | Public resources | Company could provide | Tools |
|---|---|---|---|
| Sustainability / ESG | [SGX sustainability reports](https://www.sgx.com/sustainability), [CDP](https://www.cdp.net), [GRI database](https://database.globalreporting.org), [SASB](https://sasb.ifrs.org), [TCFD and ISSB frameworks](https://www.ifrs.org/sustainability), [NEA data](https://www.nea.gov.sg/our-services/resources-tools) | [E] their published report and peer set · [E] which framework they're moving to · [M] activity data behind Scope 1/2 · [H] unpublished Scope 3 | Excel, GHG Protocol calculation tools, Power BI |
| Energy & Renewables | [EMA statistics](https://www.ema.europa.eu/en/about-us/what-we-do/facts-figures), [IEA free datasets](https://www.iea.org/data-and-statistics), [IRENA cost databases](https://www.irena.org/Data), [NREL ATB](https://atb.nrel.gov), PPA and tariff data | [E] the technology and site type · [M] their capex assumptions · [H] actual PPA terms | Excel, SAM (NREL), PVsyst trial, QGIS |
| Environmental Science | [NEA and PUB monitoring data](https://www.nea.gov.sg/our-services/resources-tools), [Copernicus and NASA Earth data](https://www.earthdata.nasa.gov), published EIAs, [NParks records](https://www.nparks.gov.sg/biodiversity/wildlife-in-singapore/wildlife-datasets) | [E] the site or discharge in scope · [M] their own monitoring records | QGIS, R, Google Earth Engine |
| Automotive & Mobility | [LTA DataMall](https://datamall.lta.gov.sg), vehicle registration data, OpenStreetMap, charging network locations, EV specs | [E] the fleet profile and duty cycle · [M] anonymised telematics sample · [H] live fleet data | Python, QGIS, Sheets |
| Telecommunications | [IMDA coverage and QoS data](https://www.imda.gov.sg/how-we-can-help/consumer-information/mobile-and-fixed-broadband-networks-quality-of-service), operator annual reports, public pricing, [Ookla open data](https://www.ookla.com/ookla-for-good/open-data) | [E] the market and segment · [M] anonymised churn rates · [H] subscriber data | Python, Sheets, QGIS |

---

## Three patterns worth pulling out

**The best [E] ask in the whole table is "what did you already try, and why didn't it work?"** It costs the company nothing, it's not confidential, and it saves students from re-running a dead end. It appears in some form for nearly every role and is consistently the highest-value thing a function head can hand over.

**Tool licences are an underused [M] ask.** Extern's financial planning programme gives externs eMoney, Morningstar, Redtail and Asset-Map seats. A company with spare licences can hand over professional tooling without touching a single row of data — no legal review, and the student's CV gains a named industry tool. Ask for this before you ask for data.

**The [H] column is mostly there to tell you what not to ask for.** Run down it before any enterprise call. Every item on it converts a two-week sale into a two-month one, and in almost every case the public column plus [E] items produces work the company will still find useful.
