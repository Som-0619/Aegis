# Aegis Project Health Auditor: RAG Scoring Methodology
**Document Control Reference:** PMO-Aegis-Methodology-v1.0  
**Author:** AI Solutions Architecture & PMO Advisory Services  
**Classification:** Confidential - Internal Executive Use Only  

---

## 1. Purpose

The **Aegis Project Health Auditor (RAG) Framework** provides a standardized, repeatable, and auditable methodology to evaluate the execution health of enterprise projects. Project status reporting is traditionally prone to subjective bias, inconsistent grading, and lack of transparency. 

The objective of this framework is to establish a **deterministic, quantitative engine** that computes project health scores based on key operational signals, and then utilizes **Generative AI strictly for reasoning, summary drafting, and action prescribing after the objective score has been locked**.

### Why RAG (Red, Amber, Green) is Used for Project Health
- **RAG Status** acts as a triage indicator for leadership, enabling immediate prioritization of intervention efforts.
  - 🟢 **GREEN (80.0 - 100.0)**: The project is executing within normal boundaries. No PMO intervention is required.
  - 🟡 **YELLOW / AMBER (50.0 - 79.9)**: The project has active slippages or operational blocks that require local mitigation plans to prevent trajectory degradation.
  - 🔴 **RED (0.0 - 49.9)**: The project has breached baseline cost, schedule, or operational bounds. Active recovery governance is required immediately.

---

## 2. Inputs

The framework relies on raw weekly status files (PDF, DOCX, CSV, TXT, MD, XLSX, XLS) loaded through the **Document Reader**. The **Information Extractor** maps these unstructured logs into a structured 13-field Pydantic schema:

1.  `project_name`: Name of the target project.
2.  `planned_start_date`: Scheduled date of project initiation.
3.  `planned_end_date`: Scheduled date of project completion.
4.  `current_progress`: Self-reported progress percentage or status description.
5.  `budget`: Allocated baseline financial budget.
6.  `budget_spent`: Actual cumulative expenditure.
7.  `milestones`: Complete list of scheduled milestones.
8.  `delayed_milestones`: Subset of milestones flagged as late or delayed.
9.  `open_risks`: Identified operational or timeline threats.
10. `blockers`: Active constraints preventing progress on key tasks.
11. `stakeholder_comments`: Descriptive logs of stakeholder sentiment or reviews.
12. `dependencies`: Internal and external integrations/deliverables required.
13. `resource_availability`: Headcount and staffing status.

---

## 3. Evaluation Framework

Aegis evaluates 6 core indicators. Each indicator is calculated on a 0.0 to 100.0 scale:

### I. Schedule (Weight: 30%)
- **How it is evaluated**: Compares the elapsed timeline ratio against actual reported progress. The elapsed ratio is calculated from the start and end dates relative to the current date.
  $$\text{Expected Progress} = \frac{\text{Current Date} - \text{Start Date}}{\text{End Date} - \text{Start Date}} \times 100$$
  If actual progress is less than expected progress, a progress lag is calculated:
  $$\text{Lag} = \text{Expected Progress} - \text{Actual Progress}$$
  $$\text{Schedule Score} = \max(0.0, 100.0 - (\text{Lag} \times 1.5))$$
- **Why it matters**: Monitors if work rate is sufficient to meet deadlines.

### II. Budget (Weight: 20%)
- **How it is evaluated**: Evaluates financial variance. If actual spent exceeds baseline budget, a penalty is applied based on the overrun ratio:
  $$\text{Overrun Ratio} = \frac{\text{Budget Spent} - \text{Budget}}{\text{Budget}}$$
  $$\text{Budget Score} = \max(0.0, 100.0 - (\text{Overrun Ratio} \times 200.0))$$
- **Why it matters**: Controls cost variances and protects profit margins.

### III. Milestones (Weight: 20%)
- **How it is evaluated**: Evaluates milestone achievement rates.
  $$\text{Milestones Score} = \max\left(0.0, 100.0 - \left(\frac{\text{Delayed Milestones Count}}{\text{Total Milestones Count}} \times 100.0\right)\right)$$
- **Why it matters**: Reflects concrete deliverables completed vs. planned.

### IV. Risks (Weight: 15%)
- **How it is evaluated**: Deducts points from a base of 100.0 for active blockers and risks depending on severity:
  - **Blocker**: -25 points
  - **Critical Risk**: -20 points
  - **High Risk**: -15 points
  - **Medium Risk**: -10 points
  - **Low Risk**: -5 points
  $$\text{Risks Score} = \max(0.0, 100.0 - \sum \text{Penalties})$$
- **Why it matters**: Quantifies active roadblocks and mitigates prospective failures.

### V. Stakeholder Sentiment (Weight: 10%)
- **How it is evaluated**: Audits stakeholder comment lists. Scoring starts at a baseline of 80.0. A case-insensitive match on keyword lists boosts or penalizes the score (capped between 0 and 100):
  - **Positive Boost (+10 points)**: *happy, pleased, satisfied, excellent, great, good, successful, on track, confident*
  - **Negative Penalty (-20 points)**: *concerned, worried, unhappy, dissatisfied, poor, issue, delay, risk, block, skeptical*
- **Why it matters**: Measures sponsor confidence and client satisfaction.

### VI. Resources (Weight: 5%)
- **How it is evaluated**: Checks resource availability logs. Starts at 100.0. If deficit keywords are detected (*low, limited, deficit, shortage, missing, tight, constrained, understaffed*), a deficit penalty is applied:
  $$\text{Resources Score} = 100.0 - 50.0 = 50.0$$
- **Why it matters**: Ensures adequate staffing to maintain velocity.

---

## 4. Weight Distribution

The final score is a weighted sum of the 6 sub-scores:

| Indicator Category | Weight | Primary Calculation Driver |
| :--- | :---: | :--- |
| **Schedule** | 30% | Timeline Elapsed Ratio vs. Actual Progress |
| **Budget** | 20% | Cost Overrun Ratio |
| **Milestones** | 20% | Ratio of Delayed Milestones |
| **Risks** | 15% | Count of Blockers and Risk Severities |
| **Sentiment** | 10% | Keyword Scanning of Stakeholder Comments |
| **Resources** | 5% | Keyword Scanning of Resource Availability |

---

## 5. Threshold Table

The final weighted score maps directly to the project's RAG health status:

| Score Range | RAG Status | Definition & Action Level |
| :---: | :---: | :--- |
| **80.0 - 100.0** | 🟢 **GREEN** | Project is healthy. Maintain standard monitoring. |
| **50.0 - 79.9** | 🟡 **YELLOW** | Operational slippage detected. Local PMO action required. |
| **0.0 - 49.9** | 🔴 **RED** | Critical breaches. Escalation and strategic recovery audit. |

---

## 6. Assumptions

When project updates are partial or incomplete, Aegis uses the following default assumptions:
1.  **Start and End Dates**: If not provided, the timeline progress cannot be computed. The Schedule Score defaults to **100.0 (On Track)**.
2.  **Budget & Spent**: If baseline budget orspent is missing, cost tracking is suspended. The Budget Score defaults to **100.0 (On Track)**.
3.  **Milestones**: If no milestone list is provided, the Milestones Score defaults to **100.0 (On Track)**.
4.  **Risks & Blockers**: If no risks or blockers are logged, the Risks Score defaults to **100.0 (Clean)**.
5.  **Sentiment**: If no comments are provided, the Sentiment Score defaults to its neutral baseline of **80.0**.
6.  **Resources**: If resource logs are empty, resource availability is assumed adequate, defaulting to **100.0**.

---

## 7. Handling Missing Data

To maintain audit transparency, **missing data does not prevent project analysis**. Instead, Aegis calculates two key diagnostic parameters:

### AI Confidence Score
Reflects the completeness of the input data based on the 13 required Pydantic fields:
$$\text{Confidence Score} = \left(\frac{\text{Count of non-null extracted fields}}{13}\right) \times 100\%$$
If a project has missing fields, the confidence score drops, but the scoring engine continues calculations.

### Missing Data Log & Warnings
Any field that returns `None` is compiled into a **Missing Data Log** at the top of the report. This flags gaps explicitly to the PMO (e.g. *"Uncertainty: Budget spent is missing from source documents, limiting cost audit"*). This prevents the AI from fabricating (hallucinating) missing parameters.

---

## 8. Decision Flow

The processing sequence is structured as follows:

```
[Raw Weekly Status File]
           │
           ▼
 [Extract 13 Schema Fields]  ──► [Compute Confidence Score & Missing Log]
           │
           ▼
[Run 6 Sub-Score Evaluators] ──► [Fallback to default values if fields missing]
           │
           ▼
[Compute Overall Weighted Score]
           │
           ▼
 [Resolve RAG status (G/Y/R)]
           │
           ▼
[AI Explanation Agent]       ──► [Generates narrative reasoning & recommendations]
           │
           ▼
[RAG Faithfulness QA Audit]  ──► [Verify narrative matches raw input source]
           │
           ▼
[Export Deliverables: JSON, MD, Txt, PPTX]
```

---

## 9. Example Evaluation

### Input Project Data: "Project Alpha"
- **Schedule**: Start Date: `2026-05-01`, End Date: `2026-10-01` (Total Timeline: 153 days). Progress reported: `35%`.
- **Financials**: Budget: `$100,000.00`, Spent: `$110,000.00`.
- **Milestones**: 3 total (2 completed, 1 delayed).
- **Risks**: 1 blocker logged, 1 high-severity risk logged.
- **Sentiment**: Stakeholder comment: *"We are pleased with backend developers, but concerned about the QA delay."*
- **Resources**: Resource log: *"We have limited staffing in the core QA team."*
- **Current Audit Date**: `2026-07-08` (Elapsed: 68 days).

### Step-by-Step Score Calculation

1.  **Schedule Score**:
    - $\text{Expected Progress} = \frac{68}{153} = 44.4\%$
    - $\text{Lag} = 44.4\% - 35.0\% = 9.4\%$
    - $\text{Schedule Score} = 100.0 - (9.4 \times 1.5) = \mathbf{85.9}$
2.  **Budget Score**:
    - $\text{Overrun Ratio} = \frac{110,000 - 100,000}{100,000} = 10.0\%$
    - $\text{Budget Score} = 100.0 - (0.10 \times 200.0) = \mathbf{80.0}$
3.  **Milestones Score**:
    - $\text{Delay Ratio} = \frac{1}{3} = 33.3\%$
    - $\text{Milestones Score} = 100.0 - (0.333 \times 100.0) = \mathbf{66.7}$
4.  **Risks Score**:
    - $\text{Deductions} = \text{Blocker (25)} + \text{High Risk (15)} = 40.0$
    - $\text{Risks Score} = 100.0 - 40.0 = \mathbf{60.0}$
5.  **Sentiment Score**:
    - Base: 80.0. Matches positive *pleased* (+10) and negative *concerned* (-20), *delay* (-20).
    - $\text{Sentiment Score} = 80.0 + 10.0 - 20.0 - 20.0 = \mathbf{50.0}$
6.  **Resources Score**:
    - Base: 100.0. Matches deficit keyword *limited* (-50).
    - $\text{Resources Score} = 100.0 - 50.0 = \mathbf{50.0}$

### Weighted Aggregation
$$\text{Overall Score} = (85.9 \times 0.30) + (80.0 \times 0.20) + (66.7 \times 0.20) + (60.0 \times 0.15) + (50.0 \times 0.10) + (50.0 \times 0.05)$$
$$\text{Overall Score} = 25.77 + 16.00 + 13.34 + 9.00 + 5.00 + 2.50 = \mathbf{71.61}$$

### Result Mapping
- **Weighted Health Score**: **71.6 / 100**
- **RAG Status Resolution**: 🟡 **YELLOW**
- **AI Explanation Agent Output**: Explains the yellow status due to milestones delays (Core Backend/UI lag) and budget overrun, and details recovery action recommendations (e.g. resolve credentials blocker, staffing reallocation).
