# Skills and Aliases by Role — Seed Data

`RoleTemplate.ranked_hard_skills`, `RoleTemplate.ranked_soft_skills` and `Role.aliases` for all 75 roles.

**This file is derived, not authored from scratch.** Each role's skills were read off its slot 2 and slot 3 rubric criteria in `rubrics.md` and its artifact in `deliverables.md`. It needs Andrei's review before cohort 1 — it is what judges see in the tagging dropdown.

**Ranking is the point (FR-903b).** The order here is the order the dropdown shows. A judge with ninety seconds between pitches picks from what is in front of them, so the five or six skills a role actually demonstrates go first; typing still searches the whole taxonomy. After cohort 1 this seeded order is refined by what judges have actually tagged in that role.

**The taxonomy is the union of this file.** Every distinct name in the hard column becomes a `Skill` of type `hard`, every name in the soft column a `Skill` of type `soft`. Reuse a name exactly to reuse the skill — "Financial modelling" in four finance roles is one skill with four rankings, not four skills. The soft column deliberately draws on a shared vocabulary of about twenty; fragmenting it into near-duplicates is what makes a dropdown useless.

**Aliases (FR-043)** are what a company might type when searching for this role. They fold into the role rather than creating a near-duplicate.

Separator is `·` throughout, as in `resources.md`.

---

## AI & Data

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| AI / AI Engineering | AI engineer · LLM engineer · GenAI · applied AI · prompt engineer | Prompt engineering · LLM evaluation · RAG architecture · Python · API integration · Cost and latency analysis | Intellectual honesty · Structured thinking · Commercial judgement · Written communication |
| Machine Learning Engineering | ML engineer · MLE · machine learning · deep learning | Model training · Feature engineering · Baseline design · Python · MLOps · Experiment tracking | Intellectual honesty · Attention to detail · Structured thinking · Written communication |
| Data Science | data scientist · applied scientist · statistics · advanced analytics | Statistical inference · Hypothesis testing · Python · Exploratory data analysis · Data visualisation | Scepticism · Structured thinking · Commercial judgement · Written communication |
| Data Analytics | data analyst · BI · business intelligence · analytics · reporting analyst | SQL · Data cleaning · Dashboard design · Data visualisation · KPI definition · Spreadsheet modelling | Executive communication · Attention to detail · Prioritisation · Structured thinking |
| Research and Analysis | research analyst · secondary research · insights analyst · desk research | Desk research · Source evaluation · Citation discipline · Comparative analysis · Report writing | Scepticism · Synthesis · Written communication · Curiosity |
| Healthcare Analytics | health data analyst · clinical analytics · health informatics · healthcare data | Clinical coding literacy · Cohort definition · SQL · Data visualisation · De-identification | Ethical judgement · Attention to detail · Structured thinking · Written communication |

## Engineering & Technical

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| QA / Testing | QA · quality assurance · test engineer · SDET · software testing | Test case design · Exploratory testing · Bug reporting · Severity triage · Test automation · Accessibility testing | Attention to detail · Prioritisation · Written communication · Scepticism |
| Robotics | robotics engineer · ROS · autonomy · mechatronics | ROS · Simulation · Control systems · Python · Sensor data analysis | Intellectual honesty · Structured thinking · Attention to detail · Written communication |
| Mechanical / Civil / Chemical | mechanical engineering · civil engineering · chemical engineering · process engineering · structural | Engineering calculation · CAD modelling · Standards compliance · Simulation (FEA/CFD) · Technical drawing | Attention to detail · Intellectual honesty · Structured thinking · Written communication |
| Blockchain / Web3 | web3 · smart contracts · crypto · solidity · DeFi | Solidity · Smart contract testing · Security review · Gas optimisation · Tokenomics modelling | Scepticism · Attention to detail · Structured thinking · Commercial judgement |

## Product & Design

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| Product Management | PM · product owner · product manager · APM · product | PRD writing · User research synthesis · Roadmap prioritisation · Metric definition · Competitive analysis | Prioritisation · Stakeholder empathy · Executive communication · Structured thinking |
| UX / UI Design | UX · UI · product design · interaction design · visual design | Figma · Interaction design · Heuristic evaluation · Design systems · Accessibility (WCAG) · Prototyping | Stakeholder empathy · Attention to detail · Defending a position · Creative thinking |
| UX Research | user research · design research · usability research · UXR | Usability testing · Interview moderation · Research design · Thematic analysis · Participant recruitment | Stakeholder empathy · Synthesis · Scepticism · Written communication |
| Industrial Design | ID · hardware design · physical product design · product design (physical) | 3D modelling · Concept sketching · Materials selection · Design for manufacture · Rendering | Creative thinking · Stakeholder empathy · Attention to detail · Commercial judgement |
| Architecture | architect · architectural design · building design · built environment | Site analysis · Zoning and code compliance · Space planning · CAD/BIM · Architectural visualisation | Creative thinking · Attention to detail · Defending a position · Structured thinking |
| Technical Writing | documentation · docs · content design · technical author · technical communication | Documentation structure · Information architecture · Style guide application · Editing · API documentation | Written communication · Stakeholder empathy · Attention to detail · Prioritisation |

## Business & Strategy

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| Business Strategy | corporate strategy · strategy · strategic planning · commercial strategy | Market sizing · Scenario analysis · Competitive analysis · Financial modelling · Executive deck writing | Structured thinking · Executive communication · Commercial judgement · Defending a position |
| Consulting | management consulting · strategy consulting · advisory · business consulting | Issue tree structuring · Hypothesis-driven analysis · Executive deck writing · Market sizing · Implementation planning | Structured thinking · Executive communication · Prioritisation · Defending a position |
| Strategy & Corporate Analysis | business analysis · corporate analysis · business unit strategy | Financial statement analysis · Segment analysis · Scenario analysis · Competitive analysis · Executive deck writing | Commercial judgement · Structured thinking · Defending a position · Written communication |
| Innovation Sourcing | scouting · tech scouting · open innovation · startup scouting · innovation | Landscape mapping · Screening criteria design · Company research · Patent search · Scorecard design | Curiosity · Structured thinking · Prioritisation · Written communication |
| Procurement & Sourcing | procurement · sourcing · purchasing · supply management · category management | Spend analysis · Supplier evaluation · Negotiation planning · Category management · Spreadsheet modelling | Commercial judgement · Structured thinking · Persuasion · Attention to detail |
| Entrepreneurship / Founder | founder · startup · entrepreneur · venture building · early-stage | Customer discovery · Unit economics · Market sizing · Landing page build · Prototyping | Self-direction · Resilience under pressure · Persuasion · Intellectual honesty |
| Business Development / Partnerships | BD · partnerships · alliances · business development · channel | Partner mapping · Deal structuring · Value proposition design · Outreach writing · Pipeline management | Persuasion · Stakeholder empathy · Commercial judgement · Written communication |

## Finance

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| Finance (general) | corporate finance · FP&A · financial analysis · finance analyst · treasury | Financial modelling · Sensitivity analysis · Financial statement analysis · Excel · Memo writing | Attention to detail · Commercial judgement · Structured thinking · Executive communication |
| Investment Banking | IB · investment banking analyst · M&A banking · capital markets · sell-side | DCF valuation · Comparable company analysis · Precedent transactions · Financial modelling · Filings analysis | Attention to detail · Resilience under pressure · Executive communication · Defending a position |
| Venture Capital | VC · venture · early-stage investing · startup investing · venture capital analyst | Investment memo writing · Diligence research · Market sizing · Deal sourcing · Cap table literacy | Scepticism · Curiosity · Defending a position · Written communication |
| Private Equity | PE · buyout · growth equity · leveraged buyout | LBO modelling · Debt structuring · Returns analysis · Operational diligence · Financial modelling | Commercial judgement · Attention to detail · Structured thinking · Defending a position |
| Asset & Wealth Management | wealth management · asset management · portfolio management · private banking · buy-side | Portfolio construction · Asset allocation · Performance attribution · Risk analysis · Client reporting | Executive communication · Stakeholder empathy · Attention to detail · Commercial judgement |
| Quantitative Trading | quant · quantitative research · systematic trading · algo trading · quantitative finance | Backtesting · Time series analysis · Python · Statistical modelling · Transaction cost analysis | Intellectual honesty · Scepticism · Attention to detail · Structured thinking |
| Tax | taxation · tax advisory · transfer pricing · tax compliance | Tax legislation research · Position memo writing · Cross-border analysis · Case law analysis · Compliance review | Attention to detail · Written communication · Ethical judgement · Structured thinking |
| Actuarial Science | actuary · actuarial · insurance pricing · reserving | Pricing modelling · Reserving · Mortality table application · Sensitivity testing · Excel | Attention to detail · Intellectual honesty · Structured thinking · Written communication |
| Corporate Development / M&A | corp dev · M&A · mergers and acquisitions · inorganic growth · corporate development | Target screening · Valuation · Synergy analysis · Financial modelling · Integration planning | Commercial judgement · Structured thinking · Executive communication · Defending a position |
| Fintech | financial technology · payments · digital banking · embedded finance · paytech | Product teardown · Regulatory mapping · Feature specification · Competitive analysis · API literacy | Curiosity · Commercial judgement · Structured thinking · Written communication |
| Real Estate | property · REIT · real estate investment · property finance · CRE | Property cash flow modelling · IRR analysis · Comparables analysis · Market research · Excel | Commercial judgement · Attention to detail · Structured thinking · Defending a position |

## Marketing, Sales & Media

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| Marketing (general) | marketing · growth marketing · demand generation · marketing strategy · growth | Positioning · Audience segmentation · Channel planning · Campaign measurement · Copywriting | Commercial judgement · Creative thinking · Executive communication · Prioritisation |
| Brand Management | branding · brand strategy · brand marketing · brand | Brand audit · Positioning · Messaging architecture · Competitive analysis · Brand tracking | Creative thinking · Structured thinking · Executive communication · Stakeholder empathy |
| Advertising & Media Planning | media planning · paid media · advertising · media buying · performance media | Media planning · Reach and frequency modelling · Budget allocation · Audience targeting · Creative briefing | Commercial judgement · Attention to detail · Structured thinking · Creative thinking |
| Creative Strategist | creative strategy · planner · brand planner · account planning | Insight development · Creative platform design · Concept development · Audience research · Creative briefing | Creative thinking · Synthesis · Persuasion · Curiosity |
| Content Creation / Copywriting | copywriting · content marketing · content strategy · writer · content | Copywriting · Tone of voice development · Editing · Content planning · SEO fundamentals | Written communication · Creative thinking · Adaptability · Attention to detail |
| Social Media Management | social media · community management · social marketing · social | Platform-native content · Short-form video editing · Community management · Social analytics · Content batching | Adaptability · Creative thinking · Resilience under pressure · Written communication |
| PR & Communications | PR · public relations · communications · corporate comms · media relations | Story angle development · Press release writing · Media list building · Crisis messaging · Spokesperson briefing | Written communication · Persuasion · Resilience under pressure · Ethical judgement |
| Tech Sales | SDR · BDR · sales development · SaaS sales · inside sales | ICP definition · Prospecting · Outbound sequence writing · Discovery questioning · CRM hygiene | Persuasion · Resilience under pressure · Written communication · Self-direction |
| Sales (Enterprise / B2B) | enterprise sales · B2B sales · account executive · key account management · field sales | Account planning · Stakeholder mapping · Business case building · Proposal writing · Negotiation | Persuasion · Stakeholder empathy · Executive communication · Commercial judgement |
| E-Commerce | ecommerce · online retail · CRO · D2C · digital commerce | Funnel analysis · Conversion rate optimisation · A/B test design · Web analytics · Merchandising | Commercial judgement · Structured thinking · Attention to detail · Prioritisation |
| Journalism | reporting · news · editorial · reporter · investigative | Interviewing · Fact verification · Records research · News writing · Story structuring | Curiosity · Scepticism · Ethical judgement · Written communication |
| Film & Video Production | video production · filmmaking · videography · motion · post-production | Video editing · Videography · Treatment writing · Shot planning · Sound design | Creative thinking · Attention to detail · Time management · Collaboration |
| Music | music production · sound · audio · composition · sync | Music production · Mixing · Arrangement · Sound design · Reference analysis | Creative thinking · Attention to detail · Adaptability · Collaboration |
| Fashion & Luxury | fashion · luxury · retail buying · merchandising · apparel | Trend analysis · Assortment planning · Price architecture · Competitive shopping · Moodboarding | Creative thinking · Commercial judgement · Attention to detail · Curiosity |
| Sports & Entertainment | sports marketing · entertainment · sponsorship · fan engagement · sports business | Audience segmentation · Sponsorship valuation · Activation design · Rights analysis · Measurement planning | Commercial judgement · Creative thinking · Stakeholder empathy · Structured thinking |

## Consumer & Research

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| Consumer Insights | insights · consumer insight · shopper insights · category insights | Survey design · Segmentation analysis · Statistical analysis · Persona development · Data visualisation | Scepticism · Synthesis · Stakeholder empathy · Written communication |
| Consumer Research | qualitative research · consumer studies · ethnography · qual | Research design · Qualitative fieldwork · Interview moderation · Thematic analysis · Findings reporting | Stakeholder empathy · Scepticism · Synthesis · Written communication |
| Market Research | market intelligence · market sizing · industry research · TAM analysis · quant research | Market sizing · Competitive landscaping · Share estimation · Source triangulation · Survey analysis | Structured thinking · Scepticism · Written communication · Attention to detail |
| CPG | consumer packaged goods · FMCG · packaged goods · consumer goods | Category analysis · Pricing architecture · Shelf and planogram reading · Concept development · Trade margin analysis | Commercial judgement · Curiosity · Creative thinking · Structured thinking |
| Travel & Hospitality | hospitality · travel · hotels · tourism · F&B | Guest journey mapping · Service design · Field audit · Review analysis · Revenue analysis | Stakeholder empathy · Attention to detail · Commercial judgement · Written communication |

## People & Organisation

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| HR / People Ops | HR · human resources · people operations · people ops · total rewards | Policy review · Compensation benchmarking · Engagement analysis · Change planning · HR compliance | Stakeholder empathy · Ethical judgement · Executive communication · Structured thinking |
| Learning & Development | L&D · training · instructional design · capability building · talent development | Skills gap analysis · Curriculum design · Instructional design · Assessment design · Competency mapping | Stakeholder empathy · Structured thinking · Written communication · Prioritisation |

## Legal, Policy & Public

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| Compliance & Regulatory | compliance · regulatory affairs · risk and compliance · governance · regtech | Regulatory research · Gap assessment · Risk ranking · Control mapping · Policy drafting | Attention to detail · Ethical judgement · Structured thinking · Written communication |
| Policy Analyst | public policy · policy research · government affairs · policy adviser · policy | Evidence review · Options analysis · Policy brief writing · Stakeholder analysis · Legislative research | Structured thinking · Intellectual honesty · Written communication · Defending a position |
| Government & Public Sector | public sector · govtech · civil service · public administration · public service | Service journey mapping · Process analysis · Implementation planning · Stakeholder analysis · Cost analysis | Stakeholder empathy · Structured thinking · Written communication · Prioritisation |
| International Relations | IR · geopolitics · foreign policy · international affairs · political risk | Geopolitical analysis · Stakeholder mapping · Risk assessment · Trade data analysis · Briefing writing | Structured thinking · Scepticism · Written communication · Curiosity |
| Criminal Justice | criminology · justice policy · law enforcement analysis · corrections | Crime data analysis · Programme evaluation · Statistical analysis · Data visualisation · Policy memo writing | Ethical judgement · Scepticism · Structured thinking · Written communication |
| Social Justice | equity · DEI · human rights · advocacy · social policy | Equity impact assessment · Disaggregated analysis · Stakeholder mapping · Community consultation · Advocacy planning | Ethical judgement · Stakeholder empathy · Persuasion · Written communication |
| Nonprofit & Social Impact | nonprofit · NGO · social impact · philanthropy · charity · third sector | Theory of change · Impact measurement · Grant writing · Funder research · Budget building | Written communication · Persuasion · Stakeholder empathy · Structured thinking |
| Urban Planning | town planning · city planning · urban design · land use planning | Spatial analysis · GIS · Zoning analysis · Site analysis · Development feasibility | Structured thinking · Stakeholder empathy · Defending a position · Written communication |
| Education / EdTech | education · edtech · teaching · learning design · curriculum | Learning design · Assessment design · Curriculum mapping · Pilot design · Learning analytics | Stakeholder empathy · Structured thinking · Written communication · Adaptability |
| Trust & Safety | T&S · content moderation · platform safety · integrity · online safety | Policy drafting · Content adjudication · Harm taxonomy · Escalation design · Enforcement analysis | Ethical judgement · Attention to detail · Resilience under pressure · Structured thinking |

## Health & Life Sciences

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| Pharmaceuticals | pharma · biopharma · drug development · life sciences commercial | Pipeline analysis · Clinical trial literacy · Market access analysis · Competitive landscaping · Literature review | Attention to detail · Commercial judgement · Structured thinking · Written communication |
| Biotech & Life Sciences | biotech · life sciences · bioscience · therapeutics · biotechnology | Literature review · Evidence appraisal · Mechanism analysis · Translational assessment · Patent search | Scepticism · Curiosity · Intellectual honesty · Written communication |
| Medical Devices | medtech · medical technology · device regulatory · IVD · medical device | Regulatory pathway analysis · Predicate device research · Human factors review · Standards compliance · Reimbursement analysis | Attention to detail · Structured thinking · Ethical judgement · Written communication |
| Public Health / Epidemiology | epidemiology · public health · global health · health policy · epi | Epidemiological analysis · Rate and denominator calculation · Confounding adjustment · Evidence review · Data visualisation | Intellectual honesty · Ethical judgement · Structured thinking · Written communication |

## Sustainability & Industrials

| Role | Aliases | Hard skills (ranked) | Soft skills (ranked) |
|---|---|---|---|
| Sustainability / ESG | ESG · sustainability · climate · CSR · corporate sustainability · net zero | Disclosure framework application (GRI/ISSB/TCFD) · Materiality assessment · Peer benchmarking · Gap analysis · GHG accounting | Structured thinking · Prioritisation · Ethical judgement · Executive communication |
| Energy & Renewables | renewables · clean energy · energy transition · solar · power | Techno-economic modelling · LCOE analysis · Policy and incentive analysis · Siting analysis · Sensitivity analysis | Commercial judgement · Attention to detail · Structured thinking · Written communication |
| Environmental Science | environmental · EHS · ecology · environmental consulting · EIA | Monitoring data analysis · Sampling design literacy · Impact assessment · GIS · Mitigation costing | Attention to detail · Intellectual honesty · Structured thinking · Written communication |
| Automotive & Mobility | automotive · mobility · EV · fleet · transport | Duty cycle modelling · Fleet economics · Charging infrastructure analysis · Telematics analysis · GIS | Commercial judgement · Structured thinking · Attention to detail · Scepticism |
| Telecommunications | telco · telecom · connectivity · mobile networks · telecommunications | Network data analysis · Coverage and QoS analysis · Pricing analysis · Churn analysis · Business case modelling | Structured thinking · Commercial judgement · Attention to detail · Written communication |
