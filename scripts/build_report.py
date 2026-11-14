"""Build the verified ARM 305 report PDF and its architecture SVG."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import sys

from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RESULTS = ROOT / "results" / "experiments"
OUTPUT = ROOT / "output" / "pdf" / "arm305_mini_project_report.pdf"
NAVY = colors.HexColor("#19334D")
BLUE = colors.HexColor("#3979A8")
TEAL = colors.HexColor("#2C8A86")
GREEN = colors.HexColor("#4E956C")
AMBER = colors.HexColor("#D29445")
PALE = colors.HexColor("#EEF3F7")
INK = colors.HexColor("#263644")
MUTED = colors.HexColor("#5B6B78")
RULE = colors.HexColor("#D4DEE6")
WHITE = colors.white


def add_box(drawing: Drawing, x: float, y: float, width: float, height: float,
            title: str, detail: str, fill: colors.Color) -> None:
    drawing.add(Rect(x, y, width, height, fillColor=fill,
                     strokeColor=colors.HexColor("#AFC0CD"), strokeWidth=0.8))
    drawing.add(String(x + 7, y + height - 14, title, fontName="Helvetica-Bold",
                      fontSize=8.2, fillColor=NAVY))
    drawing.add(String(x + 7, y + 7, detail, fontName="Helvetica", fontSize=6.8,
                      fillColor=INK))


def add_arrow(drawing: Drawing, x1: float, y1: float, x2: float, y2: float,
              color: colors.Color = BLUE) -> None:
    drawing.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.25))
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 5.5
    spread = 2.7
    bx = x2 - length * math.cos(angle)
    by = y2 - length * math.sin(angle)
    points = [
        x2, y2,
        bx + spread * math.sin(angle), by - spread * math.cos(angle),
        bx - spread * math.sin(angle), by + spread * math.cos(angle),
    ]
    drawing.add(Polygon(points, fillColor=color, strokeColor=color))


def architecture_drawing() -> Drawing:
    drawing = Drawing(490, 224)
    add_box(drawing, 5, 157, 70, 46, "User / CLI", "choose policy", PALE)
    add_box(drawing, 86, 157, 96, 46, "Seeded workload", "CPU / RAM / sensitivity", PALE)
    add_box(drawing, 193, 157, 102, 46, "Placement engine", "two deterministic rules", colors.HexColor("#DCEAF4"))
    add_box(drawing, 314, 91, 170, 116, "Simulated compute nodes", "capacity and latency", colors.HexColor("#F3F7FA"))
    add_box(drawing, 324, 168, 150, 29, "Edge", "8 CPU | 8 GB | 5 ms", colors.HexColor("#DCEAF4"))
    add_box(drawing, 324, 132, 150, 29, "Fog", "16 CPU | 24 GB | 20 ms", colors.HexColor("#E2F0ED"))
    add_box(drawing, 324, 96, 150, 29, "Cloud", "64 CPU | 64 GB | 50 ms", colors.HexColor("#F8EEDC"))
    add_box(drawing, 15, 7, 110, 30, "VM manager", "create reserves; stop releases", colors.HexColor("#F8EEDC"))
    add_box(drawing, 160, 32, 150, 40, "Tenant scoped records", "owners read their task records", colors.HexColor("#F3E8EC"))
    add_box(drawing, 350, 32, 130, 40, "Results", "CSV | JSON | QoS chart", colors.HexColor("#E3F0E7"))

    add_arrow(drawing, 75, 180, 86, 180)
    add_arrow(drawing, 182, 180, 193, 180)
    drawing.add(Line(295, 180, 309, 180, strokeColor=BLUE, strokeWidth=1.25))
    drawing.add(Line(309, 180, 309, 110, strokeColor=BLUE, strokeWidth=1.25))
    add_arrow(drawing, 309, 182, 324, 182)
    add_arrow(drawing, 309, 146, 324, 146)
    add_arrow(drawing, 309, 110, 324, 110)
    add_arrow(drawing, 125, 22, 300, 22, AMBER)
    drawing.add(Line(300, 22, 300, 96, strokeColor=AMBER, strokeWidth=1.25))
    add_arrow(drawing, 300, 96, 324, 110, AMBER)
    drawing.add(Line(399, 96, 399, 82, strokeColor=TEAL, strokeWidth=1.25))
    add_arrow(drawing, 399, 82, 310, 52, TEAL)
    add_arrow(drawing, 310, 52, 350, 52, GREEN)
    return drawing


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def styled_table(data: list[list], widths: list[float], font_size: float = 8.2) -> Table:
    header_style = ParagraphStyle(
        f"TableHeader{font_size}", fontName="Helvetica-Bold", fontSize=font_size,
        leading=font_size + 2, textColor=WHITE,
    )
    body_style = ParagraphStyle(
        f"TableBody{font_size}", fontName="Helvetica", fontSize=font_size,
        leading=font_size + 2, textColor=INK,
    )
    formatted = [
        [Paragraph(escape(str(value)), header_style if row_index == 0 else body_style) for value in row]
        for row_index, row in enumerate(data)
    ]
    table = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 2.2),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
        ("GRID", (0, 0), (-1, -1), 0.35, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def load_data() -> tuple[dict, dict, dict, dict, dict, int]:
    policy = json.loads((RESULTS / "policy_comparison.json").read_text(encoding="utf-8"))
    overload = json.loads((RESULTS / "overload_summary.json").read_text(encoding="utf-8"))
    capacity = json.loads((RESULTS / "capacity_change_comparison.json").read_text(encoding="utf-8"))
    tenant = json.loads((RESULTS / "tenant_isolation.json").read_text(encoding="utf-8"))
    task_rows = list(csv.DictReader((RESULTS / "policy_comparison.csv").open(encoding="utf-8")))
    fallback_rows = list(csv.DictReader((RESULTS / "overload_trace.csv").open(encoding="utf-8")))
    if len(task_rows) != policy["task_count"] * len(policy["runs"]):
        raise ValueError("Policy CSV does not match the verified summary task count.")
    if not tenant["result"] == "pass" or tenant["protected_contents_returned"]:
        raise ValueError("Tenant isolation evidence is not a passing, non-disclosing result.")
    fallback = {}
    for row in fallback_rows:
        if row["fallback_after_edge_unavailable"].lower() == "true":
            fallback[row["policy"]] = fallback.get(row["policy"], 0) + 1
    return policy, overload, capacity, tenant, {"fallback_counts": fallback}, len(task_rows)


def build_report() -> Path:
    DOCS.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    policy_data, overload_data, capacity_data, tenant_data, trace_data, csv_row_count = load_data()
    run_by_policy = {run["policy"]: run for run in policy_data["runs"]}
    overload_by_policy = {run["policy"]: run for run in overload_data["runs"]}
    capacity_by_policy = {row["policy"]: row for row in capacity_data["runs"]}

    diagram = architecture_drawing()
    renderSVG.drawToFile(diagram, str(DOCS / "architecture.svg"))

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25,
        leading=30, textColor=NAVY, alignment=TA_LEFT, spaceAfter=9,
    ))
    styles.add(ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=12,
        leading=16, textColor=TEAL, spaceAfter=15,
    ))
    styles.add(ParagraphStyle(
        "Section", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16,
        leading=20, textColor=NAVY, spaceBefore=1, spaceAfter=10,
    ))
    styles.add(ParagraphStyle(
        "Subsection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11,
        leading=14, textColor=TEAL, spaceBefore=8, spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        "BodyReport", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2,
        leading=13.3, textColor=INK, spaceAfter=7,
    ))
    styles.add(ParagraphStyle(
        "SmallReport", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.8,
        leading=10.5, textColor=MUTED, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10,
        leading=14, textColor=NAVY, backColor=PALE, borderColor=RULE,
        borderWidth=0.6, borderPadding=8, spaceBefore=4, spaceAfter=9,
    ))

    page_width, page_height = A4
    left_margin = 18 * mm
    right_margin = 18 * mm
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=left_margin, rightMargin=right_margin,
        topMargin=17 * mm, bottomMargin=16 * mm,
        title="ARM 305 Mini Project Report - CDEF Simulator",
        author="ARM 305 Mini Project",
        subject="Local simulation of task placement across Edge, Fog and Cloud nodes",
    )
    story = []
    body = styles["BodyReport"]
    small = styles["SmallReport"]
    section = styles["Section"]
    subsection = styles["Subsection"]

    # Page 1: purpose and verified headline results.
    story.extend([
        Spacer(1, 16 * mm),
        paragraph("ARM 305 Mini Project Report", styles["ReportTitle"]),
        paragraph("Cloud, Dev, Edge and Fog Task Simulator", styles["ReportSubtitle"]),
        paragraph("Project objective", subsection),
        paragraph(
            "This project builds a local Python simulator for assigning computing tasks to Edge, Fog, or Cloud nodes. "
            "It models CPU and RAM capacity, estimates simulated latency, compares two placement rules, tracks in-memory "
            "VM reservations, and checks tenant ownership before returning task records.", body
        ),
        paragraph("Abstract", subsection),
        paragraph(
            "The simulator runs without cloud accounts, network services, containers, hypervisors, or real virtual machines. "
            "A fixed-seed workload makes policy comparisons repeatable. Each accepted task reserves resources through the end "
            "of a run, so overload and utilization are deterministic. A 20-task run with seed 305 placed 12 tasks and rejected "
            "8 under both policies. Capacity-aware met 8 simulated QoS targets and lowest-latency-first met 7. Increasing Cloud "
            "RAM from 64 GB to 96 GB allowed each policy to place 3 additional tasks. These are model outputs, not hardware or "
            "network measurements.", body
        ),
        paragraph("Verified baseline", subsection),
    ])
    summary_rows = [["Policy", "Placed", "Rejected", "QoS met / missed", "Mean simulated latency"]]
    for name in ("lowest-latency-first", "capacity-aware"):
        run = run_by_policy[name]
        summary_rows.append([
            name,
            str(run["placed_count"]),
            str(run["rejected_count"]),
            f"{run['qos_met_count']} / {run['qos_missed_count']}",
            f"{run['mean_simulated_latency_ms']:.2f} ms",
        ])
    story.extend([
        styled_table(summary_rows, [110, 54, 54, 92, 145], 8.0),
        Spacer(1, 6 * mm),
        paragraph(
            "The results support a comparison of these two rules under the stated resource and latency assumptions. "
            "One seeded workload is useful for a classroom demonstration, but it does not establish that either policy "
            "is best for other task distributions.", body
        ),
        PageBreak(),
    ])

    # Page 2: architecture and run flow.
    story.extend([
        paragraph("1. System architecture", section),
        paragraph(
            "The command-line entry point creates a seeded workload and sends the same task objects to each placement policy. "
            "The placement engine checks both remaining CPU and RAM before selecting a node. VM reservations share the same "
            "node resource accounting. Results enter an in-memory tenant-scoped store, where the tenant check runs before a "
            "record is returned. The reporting layer writes per-task CSV, summary JSON, and charts.", body
        ),
        diagram,
        Spacer(1, 3 * mm),
        paragraph("Figure 1. Local task placement and results flow. All node activity is simulated.", small),
        paragraph("Run sequence", subsection),
        paragraph(
            "1. Generate tasks with CPU, RAM, tenant ID, and latency sensitivity. &nbsp; "
            "2. Evaluate eligible nodes using the selected policy. &nbsp; "
            "3. Reserve resources for accepted tasks and record simulated latency. &nbsp; "
            "4. Evaluate QoS separately from placement. &nbsp; "
            "5. Export per-task outcomes, totals, utilization, and charts.", body
        ),
        paragraph(
            "The diagram source is available as Mermaid and standalone SVG. The report and slides use the same architecture "
            "as the Python modules in <font name='Courier'>cdefsim</font>.", body
        ),
        PageBreak(),
    ])

    # Page 3: simulation inputs and assumptions.
    story.extend([
        paragraph("2. Nodes, tasks, and resource model", section),
        paragraph(
            "The default topology contains one node of each tier. CPU is measured in abstract simulation units, RAM in GB, "
            "and latency in milliseconds. The values below are configurable project assumptions; they were not supplied as "
            "course benchmark measurements.", body
        ),
    ])
    node_data = [["Node", "Tier", "CPU capacity", "RAM capacity", "Base latency"]]
    for node in policy_data["runs"][0]["nodes"]:
        node_data.append([
            node["node_id"], node["node_type"], str(node["cpu_capacity"]),
            f"{node['memory_capacity_gb']} GB", f"{node['base_latency_ms']} ms",
        ])
    story.extend([
        styled_table(node_data, [90, 70, 90, 90, 115], 8.2),
        paragraph("Workload and latency assumptions", subsection),
        paragraph(
            f"The default workload contains {policy_data['task_count']} tasks generated with random seed "
            f"{policy_data['random_seed']}. Task requirements are positive; generated CPU demand ranges from 1 to 8 units "
            f"and RAM demand from 1 to 12 GB. Each task has low, medium, or high latency sensitivity and one of two "
            f"simulated tenant IDs. Reusing the seed repeats the same inputs.", body
        ),
        paragraph(
            "For a candidate node, projected bottleneck utilization is the larger of post-placement CPU utilization and "
            "post-placement RAM utilization. Simulated latency is configured base latency plus 20 ms multiplied by that "
            "projected utilization. QoS targets are high &lt;= 25 ms, medium &lt;= 60 ms, and low &lt;= 100 ms. These thresholds and "
            "the load penalty are explicit assumptions and can be changed in the simulator.", body
        ),
        paragraph(
            "Accepted tasks reserve CPU and RAM until that policy run ends. Rejected tasks reserve nothing. Each independent "
            "policy run starts with fresh nodes, so final utilization equals peak utilization under this run model.",
            styles["Callout"],
        ),
        paragraph(
            "The simulation does not model instruction execution, memory access time, queue scheduling, network transport, "
            "or service duration. The latency estimate is a deterministic policy score, not a measured response time.", body
        ),
        PageBreak(),
    ])

    # Page 4: policies and controls.
    story.extend([
        paragraph("3. Placement rules and in-memory controls", section),
        paragraph("Placement policies", subsection),
        paragraph(
            "Both policies first require a node to have enough remaining CPU and RAM for the whole task. An individually "
            "oversized task is invalid; a valid task with no eligible node after previous reservations is rejected.", body
        ),
    ])
    policy_table = [
        ["Policy", "Selection order", "Tie-break / outcome"],
        ["Lowest-latency-first", "Lowest projected latency among eligible nodes", "Stable node ID; reject when no node fits"],
        ["Capacity-aware", "Lowest projected bottleneck utilization", "Projected latency, then stable node ID; reject when no node fits"],
    ]
    story.extend([
        styled_table(policy_table, [108, 185, 162], 7.7),
        paragraph("VM simulation", subsection),
        paragraph(
            "VM records contain a VM ID, host node, allocated CPU and RAM, and running or stopped status. Creating a VM "
            "validates its ID, host, and resource fit before reserving host capacity. Stopping a running VM releases those "
            "reservations; a repeated stop does not release resources twice. VM records are in memory only. The simulator does "
            "not start a hypervisor or create a real VM.", body
        ),
        paragraph("Tenant access check", subsection),
        paragraph(
            "Task records are stored with their owner tenant ID. A tenant can read its own records. Requests for another "
            "tenant's record and requests for a missing record return the same generic denial, so the response does not reveal "
            "the protected task contents or whether the ID exists. This is a teaching-level ownership check, not production "
            "authentication.", body
        ),
        paragraph("Implementation and repeatable checks", subsection),
        paragraph(
            "The implementation uses Python data classes and standard-library collections for nodes, tasks, VMs, and protected "
            "records. Matplotlib creates the results chart. The documented test command is "
            "<font name='Courier'>python -m unittest discover -s tests -v</font>; the current focused suite ran 19 tests and "
            "passed. It covers node eligibility, both policies and tie-breaks, overload, VM resource accounting, tenant denial, "
            "seeded workload, metrics, exports, and chart creation.", body
        ),
        PageBreak(),
    ])

    # Page 5: baseline policy comparison and actual chart.
    story.extend([
        paragraph("4. Policy comparison results", section),
        paragraph(
            "Both policies ran on the same 20 task inputs (seed 305) with fresh default nodes. Placement is counted separately "
            "from whether the placed task meets its sensitivity target.", body
        ),
    ])
    result_rows = [["Policy", "Placed", "Rejected", "QoS met", "QoS missed", "Mean latency"]]
    for name in ("lowest-latency-first", "capacity-aware"):
        run = run_by_policy[name]
        result_rows.append([
            name, str(run["placed_count"]), str(run["rejected_count"]),
            str(run["qos_met_count"]), str(run["qos_missed_count"]),
            f"{run['mean_simulated_latency_ms']:.2f} ms",
        ])
    story.extend([
        styled_table(result_rows, [119, 55, 59, 58, 67, 97], 8.0),
        Spacer(1, 4 * mm),
    ])
    chart_path = RESULTS / "policy_comparison_chart.png"
    content_width = page_width - left_margin - right_margin
    chart = Image(str(chart_path), width=content_width, height=content_width * 1170 / 3060)
    story.extend([
        chart,
        paragraph(
            "Figure 2. Placement counts, final/peak CPU and RAM utilization, and QoS outcomes for both policies. Rejections "
            "are shown separately; rejected tasks have no QoS result.", small
        ),
        paragraph(
            "Both policies placed 12 tasks and rejected 8, with the same node counts (Edge 3, Fog 2, Cloud 7). Their per-task "
            "choices differed: capacity-aware met one additional QoS target (8 versus 7), while mean simulated latency was "
            "46.59 ms versus 46.58 ms. These small differences describe this run only. The chart also shows RAM reaching "
            "100% on Cloud for both policies.", body
        ),
        PageBreak(),
    ])

    # Page 6: overload and access isolation evidence.
    story.extend([
        paragraph("5. Overload and tenant isolation", section),
        paragraph("Overload scenario", subsection),
        paragraph(
            "Twelve tasks each requested 8 CPU units and 8 GB RAM. Every task fit an empty node, but total demand was 96 CPU "
            "units against 88 units across Edge, Fog, and Cloud. CPU was the limiting resource, so at most 11 tasks could be "
            "placed. Both policies placed 11 and rejected 1.", body
        ),
    ])
    overload_rows = [["Policy", "Placed / rejected", "Edge / Fog / Cloud placements", "Fallback after Edge unavailable"]]
    for name in ("lowest-latency-first", "capacity-aware"):
        run = overload_by_policy[name]
        counts = run["placements_by_node"]
        overload_rows.append([
            name,
            f"{run['placed_count']} / {run['rejected_count']}",
            f"{counts['edge-1']} / {counts['fog-1']} / {counts['cloud-1']}",
            str(trace_data["fallback_counts"].get(name, 0)),
        ])
    story.extend([
        styled_table(overload_rows, [115, 85, 130, 120], 7.5),
        paragraph(
            "The per-task overload trace records whether Edge was eligible before each decision, the selected node or rejection, "
            "and the simulated latency. Once Edge was unavailable, lowest-latency-first assigned 10 tasks elsewhere; "
            "capacity-aware assigned 2 elsewhere under its utilization ranking.", body
        ),
        paragraph("Tenant isolation scenario", subsection),
        paragraph(
            f"The owner read its own task record. A cross-tenant read was {escape(tenant_data['cross_tenant_access'])} with the "
            f"generic response <font name='Courier'>{escape(tenant_data['denial_message'])}</font>. Protected task contents "
            f"returned: {str(tenant_data['protected_contents_returned']).lower()}. The evidence JSON deliberately contains no "
            f"protected task ID or task contents.", body
        ),
        paragraph(
            "The overload and access checks are separate demonstrations: overload tests resource eligibility and rejection, "
            "while tenant isolation tests whether a protected record is returned.", body
        ),
        PageBreak(),
    ])

    # Page 7: capacity experiment, limitations, reproduction.
    story.extend([
        paragraph("6. Capacity change and conclusions", section),
        paragraph(
            "The same seed-305 workload was rerun after increasing Cloud RAM from 64 GB to 96 GB. CPU capacity, base latency, "
            "Edge, and Fog remained unchanged. Each policy started with fresh nodes.", body
        ),
    ])
    capacity_rows = [["Policy", "Placed / rejected", "QoS met", "Mean latency", "Cloud RAM used / capacity"]]
    for name in ("lowest-latency-first", "capacity-aware"):
        item = capacity_by_policy[name]
        before = item["baseline"]
        after = item["capacity_changed"]
        before_cloud = next(node for node in before["node_utilization"] if node["node_id"] == "cloud-1")
        after_cloud = next(node for node in after["node_utilization"] if node["node_id"] == "cloud-1")
        capacity_rows.append([
            name,
            f"{before['placed_count']}/{before['rejected_count']} -> {after['placed_count']}/{after['rejected_count']}",
            f"{before['qos_met_count']} -> {after['qos_met_count']}",
            f"{before['mean_simulated_latency_ms']:.2f} -> {after['mean_simulated_latency_ms']:.2f} ms",
            f"{before_cloud['memory_used_gb']:.0f}/{before_cloud['memory_capacity_gb']:.0f} -> "
            f"{after_cloud['memory_used_gb']:.0f}/{after_cloud['memory_capacity_gb']:.0f} GB",
        ])
    story.extend([
        styled_table(capacity_rows, [105, 105, 55, 100, 85], 7.2),
        paragraph(
            "Each policy placed 3 more tasks and rejected 3 fewer after the RAM increase. Cloud RAM use rose from 64/64 GB to "
            "96/96 GB. Mean simulated latency increased by about 2.5 ms. QoS met stayed at 7 for lowest-latency-first and "
            "changed from 8 to 7 for capacity-aware. More placements did not guarantee more QoS passes because the latency "
            "targets and projected load changed the outcomes.", body
        ),
        paragraph("Limitations", subsection),
        paragraph(
            "The simulator is deterministic and intentionally small. Its capacities, latency penalty, and sensitivity targets "
            "are assumptions. It processes tasks in a fixed order, reserves each accepted task through the run, and does not "
            "model execution time, concurrency, network jitter, actual memory pressure, real tenants, or real virtual machines. "
            "Results must be described as simulated. More seeds and workload profiles would be needed for a broader policy study.", body
        ),
        paragraph("Reproduce the evidence", subsection),
        paragraph(
            "Install the packages in <font name='Courier'>requirements.txt</font>, run "
            "<font name='Courier'>python main.py --tasks 20 --seed 305</font>, then run "
            "<font name='Courier'>python scripts/run_experiments.py</font>. These commands regenerate the result data and "
            "four experiment records. Run <font name='Courier'>python -m unittest discover -s tests -v</font> for the 19 focused "
            "checks. The report and charts are stored under <font name='Courier'>output/pdf</font> and "
            "<font name='Courier'>results/experiments</font>.", body
        ),
        paragraph(
            "Conclusion: under the saved workload, both rules reached the same placement and rejection totals. Capacity-aware "
            "met one more QoS target in the baseline, while the capacity experiment showed that additional RAM improved "
            "acceptance but did not consistently improve QoS. The program provides a repeatable classroom model for explaining "
            "placement, resource limits, simulated latency, and tenant ownership.", body
        ),
    ])

    def page_decor(canvas, document):
        canvas.saveState()
        if document.page > 1:
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(MUTED)
            canvas.drawString(left_margin, page_height - 10 * mm, "ARM 305  |  CDEF task placement simulator")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(page_width - right_margin, 9 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=page_decor, onLaterPages=page_decor)
    return OUTPUT


if __name__ == "__main__":
    print(build_report())
