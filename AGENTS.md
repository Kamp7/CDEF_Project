# ARM 305 Mini Project - Codex Instructions

## Project goal

Build a locally runnable Python simulator for the ARM 305 Cloud, Dev, Edge and Fog Computing mini project. It must accept or generate computing tasks, place them on simulated Edge, Fog or Cloud nodes, simulate resource use, and report QoS and basic tenant-isolation results.

Treat the assignment PDF supplied by the student as the source of truth. The simulator must run on one computer without real cloud services, real virtual machines, a hypervisor, Docker, paid accounts, or network access.

## Course requirements and rubric

Use this checklist as the definition of done:

| Rubric area | Required evidence |
| --- | --- |
| Problem statement and architecture (10 marks) | A concise objective and one diagram showing users/tasks, placement logic, Edge/Fog/Cloud nodes, and results. |
| Node/resource and workload simulation (20) | At least one Edge, Fog, and Cloud node. Each has CPU and memory capacity, configured latency, and current or peak utilization. Generate or enter at least 10 tasks; every task has CPU, memory, and low/medium/high latency sensitivity. |
| Placement algorithm (20) | A rule-based policy that considers latency and available CPU/RAM. Explain the rules, tie-breakers, rejection/fallback behavior, and any assumptions in the report. |
| VM simulation and basic access control (15) | In-memory VM records include VM ID, host node, allocated CPU/RAM, and status. Support create and stop. Use a simple tenant ID or role check so one tenant cannot view another tenant's protected task records. Never store real passwords or sensitive data. |
| QoS, experiments, and chart (15) | Show placement decisions, simulated latency, resource utilization, successful and failed/rejected tasks, and total task count. Include a results table and at least one clearly labeled chart that communicates placement, utilization, and QoS. |
| Testing, code quality, and README/report (10) | Runnable source, requirements.txt, setup/execution instructions, concise report, and repeatable checks. |
| Demonstration and individual viva (10) | A short demo script that runs the app, submits tasks, shows placements and QoS/security output, and helps each student explain their contribution and the complete simulator. |

The final ZIP must contain runnable source code, requirements.txt, README/setup instructions, the architecture diagram, a 5-8 page report, experiment/test evidence and screenshots, a results table/chart, and a 5-7 slide presentation. Make the ZIP reproducible from the README.

## Keep the implementation small

- Default to a command-line menu. Use Streamlit only if the student explicitly prefers it and it remains easy to run.
- Prefer Python built-in data structures and file handling. Use matplotlib for the required chart. Add pandas only if it materially simplifies the work. Keep requirements.txt limited to packages actually used.
- Do not add Flask, FastAPI, REST/SOAP, SQLite, Docker, databases, cloud SDKs, deployment, authentication services, or real VM tooling; these are outside the assignment.
- Keep the code in a few readable modules with clear names. Avoid frameworks and abstractions that do not improve this small simulator.
- Save results as CSV or JSON using the standard library. Keep generated outputs in a clearly named results or evidence folder.
- Use deterministic sample data or a fixed random seed so policy comparisons and evidence can be repeated.
- Label all latency, resource use, and outcomes as simulated. Do not imply that the measurements came from a real network or hardware benchmark.

## Simulation behavior

- Model one Edge, one Fog, and one Cloud node at minimum. Keep each node's capacity and base latency configurable.
- Validate that task CPU/RAM requirements and VM allocations are positive and do not exceed a node's total capacity.
- A node is eligible for a task only when both remaining CPU and remaining memory can satisfy it.
- Implement two named policies for the required comparison:
  1. **Lowest-latency-first:** choose the eligible node with the lowest configured/projected latency.
  2. **Capacity-aware:** choose an eligible node with the lowest projected resource utilization; use latency as a tie-breaker.
- Use stable tie-breakers so identical inputs produce identical decisions. Explain the policies and assumptions in the README/report.
- Include task latency sensitivity in the QoS reporting. If sensitivity levels use target latencies or weights, make them configurable or clearly documented assumptions; do not present assumed values as course-provided facts.
- Define one simple, consistent resource-use model for a workload run. For example, accepted tasks can reserve CPU/RAM until the run finishes, making overload repeatable. Report the model and reset resources between independent runs.
- Report task placement/rejection separately from whether a placed task meets its simulated QoS target. Include both totals and per-task details.
- VM records must include VM ID, host, allocated CPU/RAM, and running/stopped status. Creating a VM reserves its resources from the host; stopping it releases them. Reject duplicate IDs, unknown hosts, and allocations that do not fit.
- Protect task records by tenant ID. A tenant may view its own records only. A denied request must not reveal the other tenant's task contents.

## Required experiments

Run and document all four experiment types. For each, record setup, expected outcome, actual outcome, and evidence. Use the same seeded workload when comparing policies.

1. **Policy comparison:** Run the same workload with lowest-latency-first and capacity-aware. Compare placement counts, rejections, utilization, and simulated QoS.
2. **Overload:** Submit enough demand to exceed available capacity. Show whether the task is rejected or placed on another eligible node, and explain why.
3. **Tenant isolation:** Attempt to read another tenant's protected task record. Show that access is denied without returning protected contents.
4. **Capacity or latency change:** Change at least one node's capacity or configured latency, rerun the same workload, and compare the results.

Keep experiment evidence in a table or log and save the result files used to produce the report/chart. Do not substitute unit tests for these required experiments.

## Test and quality expectations

- Add focused automated tests using Python's built-in unittest unless the project already has a suitable test setup.
- Cover node eligibility, both placement policies, deterministic tie-breaks, overload/rejection or fallback, VM create/stop resource accounting, tenant isolation, and result export/metrics.
- Keep tests separate from the four experiment write-ups. Tests check behavior; experiments demonstrate the assignment outcomes.
- Before calling the work complete, run the documented setup and execution steps from a clean environment if available, run the automated tests, and confirm the results, chart, report, slides, and ZIP are present and openable.
- Do not fabricate experimental outcomes, screenshots, or completed deliverables. Generate them from the simulator and label any remaining manual presentation work.

## Suggested project phases

Work in small, reviewable phases. At the end of each phase, summarize changed files, decisions/assumptions, and remaining items before moving on.

1. **Rubric and plan:** Inspect the assignment PDF, turn this checklist into an acceptance checklist, choose the simplest architecture, and list the files to create. Do not implement yet.
2. **Core simulator:** Implement node/task/VM models, resource accounting, both placement policies, and tenant checks. Add focused tests and confirm behavior before adding the interface.
3. **CLI and results:** Add the command-line flow, seeded workload, CSV/JSON export, metrics table, and chart. Keep each result reproducible.
4. **Experiments:** Run all four required experiments; save actual outputs and evidence; explain any surprising results.
5. **Submission materials:** Write the README, architecture diagram, 5-8 page report, and 5-7 slide deck from verified implementation and experiment results.
6. **Final package and demo:** Follow the README from a clean start, review the ZIP contents, and rehearse the short demo and viva explanation.

Do not begin by generating a large application in one pass. Implement and review one phase at a time, keeping the rubric visible throughout.

## Final acceptance check

Before delivery, confirm:

- [ ] At least 3 node types and at least 10 valid tasks are demonstrated.
- [ ] Both placement policies work on the same reproducible workload.
- [ ] Overload and capacity/latency-change comparisons are recorded.
- [ ] Unauthorized cross-tenant access is denied without leaking records.
- [ ] VM create/stop and resource accounting are shown.
- [ ] Results include per-task decisions, success/rejection, latency, utilization, totals, a table, and a chart.
- [ ] README setup steps, source, requirements, architecture, report, evidence, and 5-7 slides are included.
- [ ] The 5-8 page report and final ZIP meet the assignment's required contents.
- [ ] A student can explain the algorithm, assumptions, results, security check, and personal contribution.

