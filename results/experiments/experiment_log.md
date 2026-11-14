# ARM 305 Required Experiment Evidence

All measurements below are simulated. Accepted tasks reserve CPU and RAM until each run ends. Independent policy runs start with fresh nodes.

## 1. Policy comparison

**Setup:** Generate 20 tasks with seed 305 and run lowest-latency-first and capacity-aware on the same task objects, using fresh default Edge/Fog/Cloud nodes for each policy.

**Expected:** Both policies process the same 20 tasks. Their placements may differ; each reports rejection, final/peak utilization, simulated latency, and QoS separately.

**Actual:**
| Policy | Total | Placed | Rejected | QoS met | QoS missed | Mean simulated latency | Placements by node | Node CPU/RAM utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| lowest-latency-first | 20 | 12 | 8 | 7 | 5 | 46.58 ms | edge-1: 3, fog-1: 2, cloud-1: 7 | edge-1: 87.5%/87.5%, fog-1: 62.5%/87.5%, cloud-1: 57.8%/100.0% |
| capacity-aware | 20 | 12 | 8 | 8 | 4 | 46.59 ms | edge-1: 3, fog-1: 2, cloud-1: 7 | edge-1: 87.5%/87.5%, fog-1: 56.2%/87.5%, cloud-1: 59.4%/100.0% |

**Evidence:** `policy_comparison.csv`, `policy_comparison.json`, and `policy_comparison_chart.png`.

## 2. Overload and fallback

**Setup:** Submit 12 tasks, each requiring 8 CPU units and 8 GB RAM. Every task fits an empty node, while total requested CPU is 96 units against 88 units across the three default nodes. Run both policies from fresh nodes.

**Expected:** The policy can place a task on another eligible tier when Edge is unavailable; once aggregate capacity is exhausted, remaining work is rejected. With these fixed demands, at most 11 tasks can be placed because CPU is the limiting resource.

**Actual:**
| Policy | Total | Placed | Rejected | QoS met | QoS missed | Mean simulated latency | Placements by node | Node CPU/RAM utilization |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| lowest-latency-first | 12 | 11 | 1 | 6 | 5 | 53.18 ms | edge-1: 1, fog-1: 2, cloud-1: 8 | edge-1: 100.0%/100.0%, fog-1: 100.0%/66.7%, cloud-1: 100.0%/100.0% |
| capacity-aware | 12 | 11 | 1 | 7 | 4 | 53.18 ms | edge-1: 1, fog-1: 2, cloud-1: 8 | edge-1: 100.0%/100.0%, fog-1: 100.0%/66.7%, cloud-1: 100.0%/100.0% |

Fallback placements after Edge became ineligible: lowest-latency-first: 10, capacity-aware: 2.

**Evidence:** `overload_results.csv`, `overload_summary.json`, `overload_trace.csv`, and `overload_chart.png`. The trace records Edge eligibility before each placement and marks fallback/rejection outcomes.

## 3. Tenant isolation

**Setup:** Store a task placement record under its owner tenant, verify the owner can read it, then request it using a different tenant ID.

**Expected:** The cross-tenant request returns a generic denial and no protected task contents.

**Actual:** Owner read=allowed; cross-tenant read=denied; response=`Task record unavailable.`; protected contents returned=`False`. Result: **pass**.

**Evidence:** `tenant_isolation.json`. It intentionally contains no protected task ID or task contents.

## 4. Capacity change

**Setup:** Re-run the seed-305 20-task workload with both policies. Increase Cloud RAM from 64 GB to 96 GB; keep CPU capacity, base latency, Edge, and Fog settings unchanged.

**Expected:** More RAM should increase placement capacity and reduce rejection counts. Placement changes can also alter simulated latency and QoS.

**Actual:**
| Policy | Baseline placed/rejected | Changed placed/rejected | Placed delta | Rejected delta | QoS met baseline/changed | Mean simulated latency baseline/changed | Cloud RAM used/capacity (util%) baseline/changed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| lowest-latency-first | 12/8 | 15/5 | +3 | -3 | 7/7 | 46.58/49.11 ms | 64/64 GB (100.0%)/96/96 GB (100.0%) |
| capacity-aware | 12/8 | 15/5 | +3 | -3 | 8/7 | 46.59/49.10 ms | 64/64 GB (100.0%)/96/96 GB (100.0%) |

**Evidence:** `capacity_change_comparison.json`, `capacity_changed_results.csv`, `capacity_changed_summary.json`, and `capacity_changed_chart.png`. The JSON records per-node utilization and the before/after capacity.
