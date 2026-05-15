# AShareQuant

AShareQuant is a research and data-analysis project for listed companies in mainland China, Hong Kong, and U.S. equity markets.

The project is intended to support a reproducible equity-research workflow: build an investable universe, identify companies worth following based on durable business quality, collect market and fundamental data, and keep the analysis auditable over time.

## Scope

- Build and maintain universes for A-share, Hong Kong, and U.S. listed securities.
- Distinguish listed companies from their tradable securities, share classes, exchanges, and identifiers.
- Screen listed companies for durable business advantages before any valuation decision.
- Track watchlists as research outputs, not as buy recommendations.
- Collect historical market data including daily open, high, low, close, volume, and related trading fields.
- Track corporate actions such as dividends, splits, bonus shares, rights issues, and other events that affect historical comparability.
- Collect financial report data and disclosure timelines, including forecast, pre-announcement, and official announcement dates where available.

## Principles

- Keep raw source records separate from normalized data and derived signals.
- Preserve data provenance: provider, retrieval time, raw identifier, exchange, currency, reporting period, and adjustment policy.
- Treat trading calendars, suspensions, corporate actions, and identifier mapping as first-class data concerns.
- Keep business-quality screening separate from valuation assessment.
- Avoid committing credentials, paid-data access details, cookies, or private account identifiers.

## Project Docs

- `AGENTS.md` contains repository-specific instructions for coding agents.
- `CONTEXT.md` defines the stable domain language used by the project.
- `.agents/skills/equity-research-workflow/SKILL.md` contains reusable workflow guidance for future agent work in this repository.
- `.agents/` and `.codex/` are local agent workspaces and are intentionally ignored by Git.

## Development Workflow

Read the project docs before making changes. After modifying files, run the most targeted useful local check available and commit the completed change batch. Do not push to a remote unless explicitly requested.

## Scripts

Fetch the current mainland China A-share security universe:

```bash
python3 scripts/fetch_a_share_universe.py --output data/raw/a_share_securities.csv
```

The CSV records security code, exchange, board, listed-company name, security name, listing date, industry, region, source provider, retrieval time, and raw provider identifier useful for later screening.

Fetch the current Hong Kong listed equity security universe:

```bash
python3 scripts/fetch_hong_kong_universe.py --output data/raw/hong_kong_securities.csv
```

The Hong Kong CSV is security-level and keeps separate counters, share classes, and trading currencies as separate **Hong Kong Securities**.

Fetch the current U.S. listed security universe:

```bash
python3 scripts/fetch_us_universe.py --output data/raw/us_securities.csv
```

The U.S. CSV combines Nasdaq Trader `nasdaqlisted.txt` and `otherlisted.txt`, excludes provider test issues by default, and keeps ETF/status/exchange fields for later screening.

Run the legacy first-pass moat screening for A-share and Hong Kong securities:

```bash
python3 scripts/run_moat_screening.py
```

This legacy script reads manually curated evidence from `data/interim/moat_screening_evidence.csv` and writes `data/processed/moat_watchlist_candidates.csv`. That candidate file is kept for audit/history, but it is not the canonical current watchlist. Use the full-coverage market-specific outputs below for current A-share, Hong Kong, and U.S. screening.

The screening workflow keeps `data/raw/` immutable. Source-backed research evidence belongs in `data/interim/`; generated screening outputs belong in `data/processed/`.

For the A-share, Hong Kong, and U.S. universes, the target workflow is now a **Two-Layer Company Review**. The first layer keeps full-universe coverage through baseline triage: every listed security receives an explicit screening status, and every eligible listed-company common-equity security receives a preliminary business-quality review unless it meets the narrow **Insufficient Disclosure** definition. The second layer performs a full **Deep Company Review** for companies with `triage_score >= 65`, companies marked `borderline`, and companies explicitly challenged by a reviewer.

The existing `full_coverage_dimensional_v0.4` scoring model is a baseline triage aid, not the final watchlist decision model. It has seven dimensions: business moat, technology/product/process barrier, market position, business quality, operating quality, industry outlook/cyclicality/compounding profile, and governance risk. Deep reviews must use authoritative research sources such as company periodic reports, exchange announcements, regulator disclosures, official investor-relations materials, reputable institution reports, or professional research reports. Aggregator company introductions are discovery hints only, not scoring evidence. See `docs/moat-scoring-rubric.md`, `docs/adr/0002-use-full-coverage-dimensional-moat-scoring.md`, and `docs/adr/0003-adopt-two-layer-company-review.md`.

Build the current two-layer company triage and second-layer deep-review queue:

```bash
python3 scripts/run_two_layer_company_review.py
```

The script reads the market-specific full-coverage score files and optional reviewer challenges from `data/interim/deep_review_challenges.csv`. It writes `data/processed/company_triage_reviews.csv` as the company-level first-layer triage output and `data/interim/deep_review_queue.csv` as the pending second-layer review queue. The queue is not a final watchlist; it is the auditable worklist for full deep reviews using authoritative sources. Reviewer-challenged companies enter the queue even when the baseline triage score is below the normal threshold.

During calibration, run markets separately. A-share is the first calibration market:

```bash
python3 scripts/run_two_layer_company_review.py --markets A_SHARE --triage-output data/processed/a_share_company_triage_reviews.csv --queue-output data/interim/a_share_deep_review_queue.csv
python3 scripts/audit_a_share_review_standard.py
```

The A-share run writes `data/processed/a_share_company_triage_reviews.csv` and `data/interim/a_share_deep_review_queue.csv`. The audit writes `data/processed/a_share_review_standard_audit.csv`, checking A-share-only scope, universe coverage, queue construction, score-band distribution, and reviewer-challenge routing. Passing this audit only validates the workflow structure. Reviewer-challenged companies are not calibration anchors merely because they were named; reusable rules should come from peer-group calibration, where similar companies in one industry are compared side by side before the reviewer decides which deserve continued attention.

The first A-share peer-group calibration output is baijiu:

- `data/processed/a_share_baijiu_peer_group_calibration.csv`
- `data/processed/a_share_baijiu_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-baijiu.md`

The second A-share peer-group calibration output is EV batteries and new-energy platforms:

- `data/processed/a_share_ev_battery_peer_group_calibration.csv`
- `data/processed/a_share_ev_battery_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-ev-battery.md`

The third A-share peer-group calibration output is high-end medical devices and medical-device platforms:

- `data/processed/a_share_medical_device_peer_group_calibration.csv`
- `data/processed/a_share_medical_device_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-medical-device.md`

The fourth A-share peer-group calibration output is listed banks:

- `data/processed/a_share_bank_peer_group_calibration.csv`
- `data/processed/a_share_bank_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-bank.md`

The fifth A-share peer-group calibration output is semiconductor equipment:

- `data/processed/a_share_semiconductor_equipment_peer_group_calibration.csv`
- `data/processed/a_share_semiconductor_equipment_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-semiconductor-equipment.md`

The sixth A-share peer-group calibration output is strategic resources and mining:

- `data/processed/a_share_strategic_resources_peer_group_calibration.csv`
- `data/processed/a_share_strategic_resources_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-strategic-resources.md`

The seventh A-share peer-group calibration output is lithium resources and lithium salts:

- `data/processed/a_share_lithium_resource_peer_group_calibration.csv`
- `data/processed/a_share_lithium_resource_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-lithium-resource.md`

This group separates lithium resource ownership and lithium-salt capacity from broader EV batteries, cathode materials, battery recycling, and strategic-resource mining rules.

The eighth A-share peer-group calibration output is battery materials and nickel-cobalt integration:

- `data/processed/a_share_battery_materials_peer_group_calibration.csv`
- `data/processed/a_share_battery_materials_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-battery-materials.md`

This group compares precursor, nickel-cobalt resource integration, electrolyte, separator, anode, coating, and cathode companies. Boundary companies are judged by margin quality, product technical content, whether a larger competitor could easily copy the business, and whether the company has a durable local industrial advantage.

The ninth A-share peer-group calibration output is CXO and pharmaceutical R&D outsourcing:

- `data/processed/a_share_cxo_peer_group_calibration.csv`
- `data/processed/a_share_cxo_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-cxo.md`

This group compares CRDMO, CRO, CDMO, clinical CRO, SMO, molecular-building-block, and pharmaceutical R&D service companies. Boundary companies are judged by margin quality, technical or service complexity, customer trust, regulatory/quality-system history, project continuity, and whether a larger retained platform could easily copy the service.

The tenth A-share peer-group calibration output is infrared thermal imaging and special optoelectronic sensing:

- `data/processed/a_share_infrared_sensing_peer_group_calibration.csv`
- `data/processed/a_share_infrared_sensing_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-infrared-sensing.md`

This group is the first carved-out subgroup from the broad residual electronic-equipment queue. It compares infrared detector, thermal imaging, laser/optical, and special optoelectronic sensing companies. High industry barrier does not imply automatic inclusion; weaker companies are rejected when their role is covered by stronger retained leaders.

The eleventh A-share peer-group review output is residual electronic equipment manufacturing:

- `data/processed/a_share_electronic_equipment_manufacturing_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-electronic-equipment-manufacturing.md`

This group applies company-by-company analyst judgment to the broad residual electronic-equipment group. It retains clear hard-technology platforms and distinct boundary niches, rejects replaceable EMS/component/application vendors, and records defense-electronics questions in `docs/peer-group-calibration/a-share-pending-questions.md` for later dedicated handling.

The twelfth A-share peer-group review output is industry application software:

- `data/processed/a_share_industry_application_software_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-industry-application-software.md`

This group separates hard software products and vertical workflow anchors from project-heavy system integrators. It retains EDA, industrial control, energy IT, cybersecurity, AI, financial core systems, construction software, CAD/CAE/PDF, GIS, and selected high-switching-cost vertical software while deferring aerospace and defense-software questions.

The thirteenth A-share peer-group review output is other software services:

- `data/processed/a_share_other_software_services_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-other-software-services.md`

This group keeps only product, infrastructure, workflow, or hard-domain software platforms. It rejects generic IT services, outsourcing, project delivery, and weaker copies, while deferring aviation, traffic-control, and defense-cyber cases.

The fourteenth A-share peer-group review output is biopharma:

- `data/processed/a_share_biopharma_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-biopharma.md`

This group separates global innovative-drug platforms, scarce biological-resource platforms, IVD, companion diagnostics, life-science tools, bioactive materials, vaccines, and weaker early-pipeline companies. Current profit is not the primary screen; clinical/regulatory validation and hard-to-replicate capability are the core tests.

The fifteenth A-share peer-group review output is electronic components:

- `data/processed/a_share_electronic_components_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-electronic-components.md`

This group separates PCB/material leaders, passive and high-reliability components, optical/RF/MEMS/power niches, and weaker duplicate manufacturers. Process know-how, customer qualification, reliability history, and high-end product mix are the core tests.

The sixteenth A-share peer-group review output is the remaining medical-device group:

- `data/processed/a_share_medical_device_remaining_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-medical-device-remaining.md`

This pass applies the earlier medical-device calibration to the rest of the device universe. It keeps selected platform and high-barrier niche companies, while rejecting low-barrier consumables, weaker IVD copies, distribution-led businesses, and capacity-driven manufacturers.

The seventeenth A-share peer-group review output is environmental services:

- `data/processed/a_share_environmental_services_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-environmental-services.md`

This group is treated as utility-like rather than high-growth. It keeps only selected concession/operator platforms and differentiated membrane or hazardous-waste technology cases, while rejecting ordinary engineering, sanitation, restoration, and project-contracting companies.

The eighteenth A-share peer-group review output is integrated circuits:

- `data/processed/a_share_integrated_circuit_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-integrated-circuit.md`

This group separates foundry, OSAT, advanced packaging, analog, RF, image sensors, memory/MCU, SoC, communications chips, GPU, FPGA, semiconductor IP, and weaker fabless copies. Strategic compute and semiconductor-platform capability can qualify even before mature profitability.

The nineteenth A-share peer-group review output is chemical formulations:

- `data/processed/a_share_chemical_formulation_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-chemical-formulation.md`

This group separates innovative-drug platforms, branded OTC and specialty pharma, differentiated niches, generic-drug manufacturers, and weaker formulation companies. Innovation, clinical/channel trust, brand, and integrated capability matter more than current profit alone.

The twentieth A-share peer-group review output is auto parts:

- `data/processed/a_share_auto_parts_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-auto-parts.md`

This group separates intelligent vehicle electronics, safety-critical braking/chassis, drivetrain, powertrain, automotive glass, thermal management, lighting, lightweighting, sensors, and low-barrier component manufacturing. Global OEM validation, safety certification, software/electronics depth, and hard manufacturing process are the core tests.

The twenty-first A-share peer-group review output is traditional Chinese medicine:

- `data/processed/a_share_traditional_chinese_medicine_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-traditional-chinese-medicine.md`

This group separates national/category-defining TCM brands, modern evidence-backed TCM platforms, focused OTC niches, and weaker regional or duplicative companies. Brand, scarce formula, category leadership, pricing power, and channel trust are the core tests.

The twenty-second A-share peer-group review output is API and chemical raw drugs:

- `data/processed/a_share_api_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-api.md`

This group separates API-CDMO platforms, regulated API manufacturers, sterile injectable platforms, radiopharmaceuticals, vitamins, excipients, contrast-agent APIs, and commodity intermediates. Process development, quality systems, regulatory filings, customer validation, cost position, and scarce licenses are the core tests.

The twenty-third A-share peer-group review output is consumer electronics:

- `data/processed/a_share_consumer_electronics_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-consumer-electronics.md`

This group separates global EMS/ODM platforms, terminal brands, cross-border brands, optical-display leaders, AI/5G modules, high-end audio niches, legacy consumer-electronics groups, distributors, accessories, and structural-part suppliers. Global platform scale, leading-customer qualification, semiconductor/system capability, differentiated terminal ecosystems, and distinct niche brands or modules are the core tests.

The twenty-fourth A-share peer-group review output is solar:

- `data/processed/a_share_solar_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-solar.md`

This group separates photovoltaic power electronics, equipment, glass, encapsulation materials, wafers, polysilicon, integrated modules, power-station operators, EPC/system integration, late pivots, and low-barrier component suppliers. Global leadership, cost curve, hard process know-how, bankability, and specialty material or equipment barriers are the core tests; cycle-trough profitability is not the primary screen.

The twenty-fifth A-share peer-group review output is other electronic devices:

- `data/processed/a_share_other_electronic_devices_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-other-electronic-devices.md`

This mixed group separates distributors, polymer and EMI/thermal materials, PCB/interconnect platforms, PMIC and MEMS chips, RF connectors, acoustic components, vacuum electronics, microwave devices, display technologies, portable energy-storage brands, fuses, and ordinary consumer-electronics components. Proprietary materials, hard-technology niches, customer certification, cross-industry capability, and whether stronger retained peers already cover the thesis are the core tests.

The twenty-sixth A-share peer-group review output is communication transmission equipment:

- `data/processed/a_share_communication_transmission_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-communication-transmission.md`

This group separates telecom equipment, optical modules, optical chips/devices, optical fiber/preform/cable, submarine cable, industrial IoT gateways, cellular modules, RF filters, integrated photonics, special communication, industrial networking, high-reliability connectors, test instruments, ceramic filters, and legacy communication-equipment vendors. Network-infrastructure leadership, AI/data-center optical interconnects, deep-sea optical networks, special communication, and high-speed interconnect barriers are the core tests.

The twenty-seventh A-share peer-group review output is pharmaceutical commerce:

- `data/processed/a_share_pharma_commerce_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-pharma-commerce.md`

This group separates integrated pharmaceutical industrial platforms, ordinary regional distribution, national regulated distribution platforms, leading pharmacy chains, medical-brand commercialization platforms, diagnostics leaders, and companies misclassified into commerce despite stronger drug-discovery or branded-drug capabilities. Distribution scale alone is not enough; regulated qualification, industrial capability, chain consolidation, differentiated commercialization, and real technology platforms are the core tests.

The twenty-eighth A-share peer-group review output is the remaining storage-equipment group:

- `data/processed/a_share_storage_equipment_remaining_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-storage-equipment-remaining.md`

This pass completes the companies in `电气设备-电源设备-储能设备` that were not already decided in the EV-battery calibration pass. It separates digital-energy and UPS/data-center power platforms, storage-system and power-electronics platforms, special/aerospace power, BMS/PACK, inverter/storage niches, lithium-equipment niches, consumer-battery brands, ordinary battery manufacturing, lead-acid replacement markets, weak storage integrators, and late pivots.

The twenty-ninth A-share peer-group review output is other special machinery:

- `data/processed/a_share_other_special_machinery_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-other-special-machinery.md`

This pass reviews all companies in `机械设备-专用设备-其他专用机械`. It separates hard-to-replicate process equipment, semiconductor and advanced-manufacturing tools, photovoltaic/lithium process equipment, precision thermal-control and testing platforms, qualification-heavy safety/nuclear equipment, cross-industry capability stacks, ordinary project-based special machines, lower-barrier traditional equipment, and weaker followers already covered by stronger retained peers.

The thirtieth A-share peer-group review output is communication terminal equipment:

- `data/processed/a_share_communication_terminal_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-communication-terminal.md`

This pass reviews all companies in `信息技术-通信设备-通信终端设备`. It separates global enterprise communication endpoint brands, professional/dedicated-network communications, enterprise networking, Beidou/GNSS and defense communications, grid communication niches, secure-card/eSIM, RF/antenna/materials, optical-module boundary cases, ordinary ODM/JDM terminal manufacturing, CPE/STB vendors, mature smart-card followers, and project-based communication system integrators.

The thirty-first A-share peer-group review output is optical components:

- `data/processed/a_share_optical_components_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-optical-components.md`

This pass reviews all companies in `电子设备-光电子器件-光学元件`. It separates AI optical-communication components, photomasks, OLED materials and evaporation-source equipment, precision optics, optical instruments, optical films and functional materials, infrared/sensor niches, laser and military optics, non-leading display panels, camera-module assemblers, low-barrier display/backlight/touch components, and recent optical pivots without proven capability.

The thirty-second A-share peer-group review output is specialized computer equipment:

- `data/processed/a_share_specialized_computer_equipment_peer_group_decisions.csv`
- `docs/peer-group-calibration/a-share-specialized-computer-equipment.md`

This pass reviews all companies in `信息技术-计算机硬件-专用计算机设备`. It separates compute-infrastructure platforms, global automotive diagnostic terminals, LED display-control systems, payment and barcode-recognition platforms, commercial-cryptography hardware, defense embedded-computing equipment, financial self-service machines, data-storage niches, rail and transport terminals, ordinary peripherals, mature financial equipment, video-surveillance followers, and project-based system integrators.

Fetch A-share screening evidence into resumable interim CSV files:

```bash
python3 scripts/fetch_a_share_research_evidence.py
```

The fetcher writes `data/interim/a_share_research_queue.csv`, `data/interim/a_share_company_profiles.csv`, and `data/interim/a_share_financial_indicators.csv`.

Generate dimensional A-share scores from fetched evidence:

```bash
python3 scripts/run_a_share_full_coverage_scoring.py
```

The scorer writes `data/processed/a_share_full_coverage_scores.csv` and `data/processed/a_share_full_coverage_watchlist.csv`. The full scores file keeps the complete audit fields, including `cyclicality_profile`, `compounding_profile`, `industry_outlook_*`, reasons, sources, and timestamps. The generated watchlist is a compact algorithmic reading view with security code, security name, labeled score fields, peer group, peer-relative position, and scoring model version. It is not the peer-group-calibrated final watchlist. Use `--require-complete` when the fetch queue is complete and the run should fail if any eligible A-share company remains unscored.

Build the current A-share peer-group-calibrated watchlist from accepted reviewer decisions:

```bash
python3 scripts/build_a_share_peer_group_calibrated_watchlist.py
```

The script reads `data/processed/a_share_*_peer_group_decisions.csv` and writes `data/processed/a_share_peer_group_calibrated_watchlist.csv`. Decision files and the watchlist preserve `watch_selection_route`, distinguishing direct reviewer-accepted watch companies from boundary companies retained after analyst judgment under calibrated rules. Cross-industry rejection checks are tracked in `data/processed/a_share_cross_industry_review_audit.csv`; `藏格矿业` is the first corrected false-negative case, because its company-level resource thesis includes potash, lithium, Julong Copper equity economics, and Zijin control rather than only a weaker salt-lake lithium comparison.

Build the A-share remaining peer-group screening queue:

```bash
python3 scripts/build_a_share_peer_group_screening_queue.py
```

The queue reads `data/processed/a_share_company_triage_reviews.csv` and existing peer-group decision tables, then writes `data/interim/a_share_peer_group_screening_queue.csv`. It marks peer groups as not started, partially screened, or complete, proposes review modes, and explicitly allows low-barrier whole-group rejection when an industry lacks durable barriers. Unclear or mixed peer groups can be routed back to reviewer discussion before decisions are finalized.

Peer-group completion must not be done by a threshold-only automated screening script. A final `*_peer_group_decisions.csv` file should represent analyst judgment applied company by company within a comparable peer group, using source-backed evidence and the calibrated rules from prior groups. Scripts may build queues, merge accepted decisions into the watchlist, or validate coverage, but they should not create final watch/reject decisions from numeric thresholds alone. See `docs/adr/0004-require-analyst-peer-group-decisions.md`.

Fetch Hong Kong screening evidence into resumable interim CSV files:

```bash
python3 scripts/fetch_hong_kong_research_evidence.py
```

The fetcher writes `data/interim/hong_kong_research_queue.csv`, `data/interim/hong_kong_company_profiles.csv`, and `data/interim/hong_kong_financial_indicators.csv`. It uses Eastmoney HKF10 first and falls back to ETNet company information for newly listed securities that are not yet covered by Eastmoney.

Generate dimensional Hong Kong scores from fetched evidence:

```bash
python3 scripts/run_hong_kong_full_coverage_scoring.py
```

The scorer writes `data/processed/hong_kong_full_coverage_scores.csv` and `data/processed/hong_kong_full_coverage_watchlist.csv`. The full scores file keeps market identity and complete audit fields. The watchlist is a compact reading view with security code, security name, labeled score fields, peer group, peer-relative position, and scoring model version. When Hong Kong has duplicate currency counters for the same listed company, the full scores keep each security but the watchlist keeps one representative row.

Fetch U.S. screening evidence into resumable interim CSV files:

```bash
python3 scripts/fetch_us_research_evidence.py
```

The fetcher writes `data/interim/us_research_queue.csv`, `data/interim/us_company_profiles.csv`, and `data/interim/us_financial_indicators.csv`. It uses Nasdaq Trader for the raw security universe and SEC EDGAR `company_tickers`, `submissions`, and `companyfacts` for company profile and financial evidence. ETF, ETN, unit, warrant, right, preferred, closed-end fund, and other non-common-equity instruments are kept in the output with an explicit not-applicable status rather than being scored as listed companies. Use `--symbols UNH,MSFT` to refresh a targeted subset without rewriting unrelated evidence rows.

Generate dimensional U.S. scores from fetched evidence:

```bash
python3 scripts/run_us_full_coverage_scoring.py
```

The scorer writes `data/processed/us_full_coverage_scores.csv` and `data/processed/us_full_coverage_watchlist.csv`. The full scores file keeps market identity and complete audit fields. The watchlist is a compact reading view with security code, security name, labeled score fields, peer group, peer-relative position, and scoring model version. When the U.S. universe has multiple common-share classes for the same SEC CIK, the full scores keep each security but the watchlist keeps one representative row.
