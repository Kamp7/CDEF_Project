import fs from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { pathToFileURL } from "node:url";

const PROJECT = "C:/Users/Kamleshwar Pandey/OneDrive/Desktop/CDEF_Project";
const BUILD_DIR = path.join(PROJECT, ".build/presentation_explainer");
const FINAL_PPTX = path.join(PROJECT, "output/presentation/arm305_project_explainer_english_final_v3.pptx");
const STAGE_ROOT = "C:/Users/Kamleshwar Pandey/AppData/Local/Temp/arm305-project-explainer-stage-v4";
const STAGE_BUILD = path.join(STAGE_ROOT, "build");
const STAGE_PPTX = path.join(STAGE_ROOT, "output/arm305_project_explainer_english_final_v3.pptx");
const SKILL_DIR = "C:/Users/Kamleshwar Pandey/.codex/plugins/cache/openai-primary-runtime/presentations/26.1112.11217/skills/Presentations";
const RUNTIME_ROOT = "C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies";
const RUNTIME_NODE_MODULES = path.join(RUNTIME_ROOT, "node/node_modules");
const RUNTIME_PYTHON = path.join(RUNTIME_ROOT, "python/python.exe");
const ARTIFACT_TOOL = path.join(RUNTIME_NODE_MODULES, "@oai/artifact-tool/dist/artifact_tool.mjs");

const { FileBlob, Presentation, PresentationFile } = await import(pathToFileURL(ARTIFACT_TOOL).href);
const { applyPresentationChartFont, finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);

// This managed Windows filesystem rejects hard links. Use a create-only copy
// for the finalizer publish step; it still verifies the copied file hash.
const originalLink = fs.link;
fs.link = async (source, destination) => {
  try {
    return await originalLink(source, destination);
  } catch (error) {
    if (error?.code !== "EPERM" && error?.code !== "ENOTSUP") throw error;
    return await fs.copyFile(source, destination, fsConstants.COPYFILE_EXCL);
  }
};

const COLORS = {
  navy: "#19324D",
  ink: "#25384A",
  muted: "#5B6F80",
  teal: "#188E8B",
  blue: "#4779A6",
  gold: "#D49A32",
  red: "#C85656",
  green: "#3F8A66",
  pale: "#F3F6F8",
  paleBlue: "#E7F0F7",
  paleTeal: "#E5F2EF",
  paleGold: "#F8F0DF",
  paleRed: "#F8EBEB",
  border: "#D1DCE5",
  white: "#FFFFFF",
};
const FONT = "Arial";

async function jsonFile(relative) {
  return JSON.parse(await fs.readFile(path.join(PROJECT, relative), "utf8"));
}

const baselineData = await jsonFile("results/experiments/policy_comparison.json");
const overloadData = await jsonFile("results/experiments/overload_summary.json");
const capacityData = await jsonFile("results/experiments/capacity_change_comparison.json");
const tenantData = await jsonFile("results/experiments/tenant_isolation.json");
const experimentLog = await fs.readFile(path.join(PROJECT, "results/experiments/experiment_log.md"), "utf8");
const fallbackLog = experimentLog.match(/Fallback placements after Edge became ineligible: lowest-latency-first: (\d+), capacity-aware: (\d+)\./);
if (!fallbackLog) throw new Error("Experiment log does not contain the verified fallback totals.");
const fallbackCounts = {
  "lowest-latency-first": Number(fallbackLog[1]),
  "capacity-aware": Number(fallbackLog[2]),
};
const baselineByPolicy = Object.fromEntries(baselineData.runs.map((run) => [run.policy, run]));
const overloadByPolicy = Object.fromEntries(overloadData.runs.map((run) => [run.policy, run]));
const capacityByPolicy = Object.fromEntries(capacityData.runs.map((run) => [run.policy, run]));
if (baselineData.task_count !== 20 || baselineByPolicy["lowest-latency-first"]?.placed_count !== 12 || baselineByPolicy["capacity-aware"]?.qos_met_count !== 8) {
  throw new Error("Baseline evidence does not match the verified 20-task comparison.");
}
if (overloadData.task_count !== 12 || overloadByPolicy["lowest-latency-first"]?.placed_count !== 11 || tenantData.protected_contents_returned !== false) {
  throw new Error("Overload or tenant evidence does not match the verified experiment records.");
}
if (capacityByPolicy["lowest-latency-first"]?.capacity_changed?.placed_count !== 15 || capacityByPolicy["capacity-aware"]?.capacity_changed?.qos_met_count !== 7) {
  throw new Error("Capacity-change evidence does not match the verified comparison.");
}

await fs.mkdir(BUILD_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
await fs.mkdir(STAGE_BUILD, { recursive: true });
await fs.mkdir(path.dirname(STAGE_PPTX), { recursive: true });
try {
  await fs.access(FINAL_PPTX);
  throw new Error("Refusing to overwrite an existing explainer presentation.");
} catch (error) {
  if (error?.code !== "ENOENT") throw error;
}

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });

function addShape(slide, geometry, name, x, y, w, h, fill = "none", stroke = "none", strokeWidth = 0) {
  return slide.shapes.add({
    geometry,
    name,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: stroke, width: strokeWidth },
  });
}

function addText(slide, name, value, x, y, w, h, style = {}) {
  const shape = addShape(slide, "textbox", name, x, y, w, h);
  shape.text = value;
  shape.text.style = {
    typeface: FONT,
    fontSize: 18,
    color: COLORS.ink,
    alignment: "left",
    verticalAlignment: "top",
    autoFit: "shrinkText",
    wrap: "square",
    insets: 0,
    ...style,
  };
  return shape;
}

function addArrow(slide, name, x, y, w, h, color = COLORS.blue, vertical = false) {
  return addShape(slide, vertical ? "downArrow" : "rightArrow", name, x, y, w, h, color);
}

function addHeader(slide, title, page) {
  addText(slide, `title-${page}`, title, 56, 52, 1168, 58,
    { fontSize: 34, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addShape(slide, "rect", `rule-${page}`, 56, 121, 1168, 2, COLORS.border);
  addText(slide, `page-${page}`, `${page} / 7`, 1150, 684, 74, 18,
    { fontSize: 11, color: COLORS.muted, alignment: "right", verticalAlignment: "middle" });
}

function addTable(slide, x, y, w, h, rows, columnWidths, bodyFont = 13) {
  const table = slide.tables.add({
    rows: rows.length,
    columns: rows[0].length,
    left: x,
    top: y,
    width: w,
    height: h,
    columnWidths,
    values: rows,
  });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: COLORS.border, width: 1 });
  for (let row = 0; row < rows.length; row += 1) {
    const rowRange = table.cells.block({ row, column: 0, rowCount: 1, columnCount: rows[row].length });
    rowRange.textStyle.fontSize = bodyFont;
    rowRange.textStyle.bold = row === 0;
    rowRange.textStyle.color = row === 0 ? COLORS.white : COLORS.ink;
    rowRange.textStyle.typeface = FONT;
    for (let col = 0; col < rows[row].length; col += 1) {
      const cell = table.getCell(row, col);
      cell.fill = row === 0 ? COLORS.navy : (row % 2 === 0 ? COLORS.pale : COLORS.white);
    }
    table.rows[row].height = h / rows.length;
  }
  return table;
}

function addChart(slide, title, position, categories, series, maximum, yTitle, colors, majorUnit = undefined) {
  const chart = slide.charts.add("bar", {
    position,
    title,
    titlePlacement: "aboveChart",
    titleTextStyle: { fontSize: 16, bold: true, fill: COLORS.navy },
    categories,
    series: series.map((item, index) => ({ ...item, fill: colors[index] })),
    hasLegend: true,
    legend: { position: "bottom", overlay: false, textStyle: { fontSize: 10 } },
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 105, overlap: 0 },
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: yTitle.includes("%") ? "0.0" : "0", textStyle: { fontSize: 10, bold: true } },
    xAxis: { textStyle: { fontSize: 10 } },
    yAxis: {
      min: 0,
      max: maximum,
      majorUnit,
      title: { text: yTitle, textStyle: { fontSize: 10 } },
      textStyle: { fontSize: 10 },
      majorGridlines: { style: "solid", fill: COLORS.border, width: 1 },
    },
    chartFill: COLORS.white,
    chartLine: { style: "solid", fill: COLORS.border, width: 1 },
    plotAreaFill: COLORS.white,
    plotAreaLine: { style: "solid", fill: "none", width: 0 },
  });
  applyPresentationChartFont(chart, { fontFamily: FONT });
  return chart;
}

function round2(value) {
  return Number(value).toFixed(2);
}

// Slide 1: minimal cover.
{
  const slide = deck.slides.add();
  slide.background.fill = COLORS.navy;
  addShape(slide, "rect", "cover-accent", 0, 0, 16, 720, COLORS.teal);
  addText(slide, "cover-kicker", "ARM 305  |  CLOUD, DEV, EDGE AND FOG", 68, 58, 780, 28,
    { fontSize: 15, bold: true, color: "#91D9D3", verticalAlignment: "middle" });
  addText(slide, "cover-title", "Task Placement\nSimulator", 68, 130, 680, 170,
    { fontSize: 58, bold: true, color: COLORS.white, verticalAlignment: "middle" });
  addText(slide, "cover-subtitle", "A beginner's guide to how the project works", 72, 323, 700, 42,
    { fontSize: 25, color: "#D7E3EC", verticalAlignment: "middle" });
  addText(slide, "cover-objective", "The simulator places computing tasks on Edge, Fog or Cloud nodes, then reports resource use and simulated service quality.",
    72, 394, 650, 82, { fontSize: 19, color: "#D7E3EC" });
  const facts = [
    { x: 72, width: 250, value: "20", label: "repeatable tasks" },
    { x: 380, width: 300, value: "3 tiers", label: "Edge, Fog and Cloud" },
    { x: 738, width: 350, value: "2 policies", label: "latency and capacity" },
  ];
  for (const [index, fact] of facts.entries()) {
    addShape(slide, "rect", `cover-fact-rule-${index}`, fact.x, 552, fact.width, 3,
      [COLORS.teal, COLORS.blue, COLORS.gold][index]);
    addText(slide, `cover-fact-value-${index}`, fact.value, fact.x, 570, fact.width, 38,
      { fontSize: 26, bold: true, color: COLORS.white, verticalAlignment: "middle" });
    addText(slide, `cover-fact-label-${index}`, fact.label, fact.x, 612, fact.width, 24,
      { fontSize: 15, color: "#D7E3EC", verticalAlignment: "middle" });
  }
  addText(slide, "cover-simulation-note", "All capacity, latency, utilization and outcome figures are simulated.", 72, 668, 750, 20,
    { fontSize: 12, color: "#C7D5E0", verticalAlignment: "middle" });
  slide.speakerNotes.text = "Opening: This project is a local simulator for a small cloud computing problem. A workload contains tasks that need CPU and memory. The program chooses an Edge, Fog or Cloud node for each task using one of two rules, then reports whether the task fit and whether its simulated latency met a target. Everything in this presentation comes from saved project runs. These numbers are simulation outputs, not measurements from a real computer or network. Source: README.md and results/experiments/experiment_log.md.";
}

// Slide 2: basic vocabulary and node tiers.
{
  const slide = deck.slides.add();
  slide.background.fill = COLORS.white;
  addHeader(slide, "The tasks, nodes and resources", 2);
  addText(slide, "tiers-intro", "A task asks for compute. A node supplies it.", 56, 137, 1168, 28,
    { fontSize: 17, color: COLORS.muted, verticalAlignment: "middle" });
  addText(slide, "tier-table-heading", "Default simulated tiers", 56, 178, 530, 30,
    { fontSize: 21, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addTable(slide, 56, 220, 530, 208, [
    ["Node", "CPU capacity", "RAM", "Base latency"],
    ["Edge", "8 units", "8 GB", "5 ms"],
    ["Fog", "16 units", "24 GB", "20 ms"],
    ["Cloud", "64 units", "64 GB", "50 ms"],
  ], [118, 150, 95, 167], 13);
  addText(slide, "tier-note", "Edge is closest to the user. Fog sits in the middle. Cloud models a larger, more distant resource pool.", 56, 445, 530, 72,
    { fontSize: 16, color: COLORS.ink });

  addText(slide, "glossary-heading", "The words used in the results", 640, 178, 584, 30,
    { fontSize: 21, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  const glossary = [
    ["Task", "One request with CPU, RAM, tenant and latency sensitivity."],
    ["CPU and RAM", "Processing capacity and working memory. CPU is an abstract simulation unit."],
    ["Latency", "Estimated response delay, shown in milliseconds."],
    ["QoS target", "Maximum allowed simulated latency for a sensitivity level."],
    ["Seed", "A fixed input that makes the generated workload repeatable."],
  ];
  glossary.forEach(([term, definition], index) => {
    const yy = 222 + index * 60;
    addShape(slide, "rect", `glossary-rule-${index}`, 640, yy + 2, 5, 44,
      [COLORS.teal, COLORS.blue, COLORS.gold, COLORS.red, COLORS.green][index]);
    addText(slide, `glossary-term-${index}`, term, 660, yy, 160, 24,
      { fontSize: 15, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
    addText(slide, `glossary-definition-${index}`, definition, 820, yy, 392, 48,
      { fontSize: 14, color: COLORS.ink, verticalAlignment: "middle" });
  });
  addText(slide, "tier-assumption", "These capacities and base latencies are configurable project assumptions, not real benchmark values.", 56, 568, 1168, 42,
    { fontSize: 15, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  slide.speakerNotes.text = "Explain the vocabulary before discussing the algorithm. A task is like a job ticket that says how much processing and memory it needs. A node is one place where the job could run. Edge means close to the user and usually lower delay, Fog means an intermediate layer, and Cloud means a larger pool with a higher configured base delay. The CPU values are abstract units, not physical cores or GHz. RAM is in gigabytes. Latency is measured in milliseconds. QoS means Quality of Service; here it means whether the estimated latency stays under a chosen target. Seed 305 lets us regenerate the same 20 tasks. The capacity and latency values are assumptions chosen for this simulator. Source: cdefsim/models.py, cdefsim/workloads.py, README.md.";
}

// Slide 3: system architecture and run sequence.
{
  const slide = deck.slides.add();
  slide.background.fill = COLORS.white;
  addHeader(slide, "How the simulator works", 3);
  const flow = [
    { x: 56, width: 178, title: "CLI", body: "Choose task count\nand seed", fill: COLORS.paleBlue },
    { x: 280, width: 226, title: "Workload generator", body: "Create task IDs,\nresource needs and tenants", fill: COLORS.pale },
    { x: 554, width: 222, title: "Placement engine", body: "Check fit and apply\none policy", fill: COLORS.paleTeal },
  ];
  flow.forEach((item, index) => {
    addShape(slide, "roundRect", `flow-box-${index}`, item.x, 186, item.width, 108, item.fill, COLORS.border, 1);
    addText(slide, `flow-title-${index}`, item.title, item.x + 14, 202, item.width - 28, 28,
      { fontSize: 17, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
    addText(slide, `flow-body-${index}`, item.body, item.x + 14, 241, item.width - 28, 42,
      { fontSize: 14, color: COLORS.ink });
  });
  addArrow(slide, "flow-arrow-1", 239, 225, 34, 24, COLORS.blue);
  addArrow(slide, "flow-arrow-2", 511, 225, 34, 24, COLORS.blue);
  addArrow(slide, "flow-arrow-3", 780, 225, 38, 24, COLORS.blue);

  addShape(slide, "roundRect", "node-pool", 832, 154, 380, 222, COLORS.pale, COLORS.border, 1);
  addText(slide, "node-pool-heading", "Simulated node pool", 852, 166, 340, 28,
    { fontSize: 18, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  const tiers = [
    ["Edge", "Lowest base delay", COLORS.paleBlue],
    ["Fog", "Middle tier", COLORS.paleTeal],
    ["Cloud", "Largest capacity", COLORS.paleGold],
  ];
  tiers.forEach(([name, note, fill], index) => {
    const yy = 207 + index * 50;
    addShape(slide, "roundRect", `flow-node-${index}`, 852, yy, 340, 40, fill, COLORS.border, 1);
    addText(slide, `flow-node-name-${index}`, name, 866, yy + 7, 110, 26,
      { fontSize: 15, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
    addText(slide, `flow-node-note-${index}`, note, 976, yy + 7, 200, 26,
      { fontSize: 13, color: COLORS.ink, verticalAlignment: "middle" });
  });

  const bottomBlocks = [
    { x: 56, w: 316, title: "VM manager", body: "VM create reserves node resources.\nVM stop releases them.", fill: COLORS.paleGold },
    { x: 450, w: 316, title: "Tenant check", body: "Check the record owner\nbefore returning task data.", fill: COLORS.paleRed },
    { x: 844, w: 368, title: "Results", body: "Per-task CSV, summary JSON\nand a labeled chart.", fill: COLORS.paleTeal },
  ];
  bottomBlocks.forEach((item, index) => {
    addShape(slide, "roundRect", `flow-bottom-${index}`, item.x, 456, item.w, 92, item.fill, COLORS.border, 1);
    addText(slide, `flow-bottom-title-${index}`, item.title, item.x + 16, 469, item.w - 32, 26,
      { fontSize: 17, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
    addText(slide, `flow-bottom-body-${index}`, item.body, item.x + 16, 503, item.w - 32, 36,
      { fontSize: 14, color: COLORS.ink });
  });
  addText(slide, "vm-resource-label", "VM allocations share the node CPU and RAM pool", 120, 391, 600, 20,
    { fontSize: 12, bold: true, color: COLORS.gold, alignment: "center", verticalAlignment: "middle" });
  addShape(slide, "rect", "vm-resource-stem", 210, 430, 4, 26, COLORS.gold);
  addArrow(slide, "vm-resource-arrow", 212, 410, 608, 20, COLORS.gold);
  addArrow(slide, "node-results-arrow", 1016, 380, 26, 62, COLORS.blue, true);
  addArrow(slide, "tenant-results-arrow", 774, 490, 60, 20, COLORS.teal);
  addText(slide, "workflow-note", "Accepted tasks reserve resources until the run ends. Each policy starts with fresh nodes.", 56, 594, 1168, 30,
    { fontSize: 15, color: COLORS.muted, verticalAlignment: "middle" });
  slide.speakerNotes.text = "Walk through the architecture in order. The command line calls the seeded workload generator. The placement engine tests each task against the remaining CPU and RAM on the nodes, then ranks the eligible options. Accepted tasks reserve resources until that run finishes. The comparison starts a fresh set of nodes for each policy, which keeps the experiment fair. The VM manager uses the same simulated node capacity. A tenant ownership check gates protected task records before the results are returned. The reporting module writes per-task CSV, summary JSON and a chart. Source: main.py, cdefsim/workloads.py, cdefsim/placement.py, cdefsim/engine.py, cdefsim/vms.py, cdefsim/security.py, cdefsim/reporting.py.";
}

// Slide 4: eligibility, policies, formula and QoS assumptions.
{
  const slide = deck.slides.add();
  slide.background.fill = COLORS.white;
  addHeader(slide, "Placement rules and simulated QoS", 4);
  addText(slide, "eligibility-label", "Every policy uses the same first check", 56, 142, 1168, 28,
    { fontSize: 18, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addShape(slide, "roundRect", "eligibility-task", 56, 184, 260, 84, COLORS.paleBlue, COLORS.border, 1);
  addText(slide, "eligibility-task-title", "Task requirements", 74, 197, 224, 26,
    { fontSize: 16, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addText(slide, "eligibility-task-body", "Required CPU and RAM", 74, 230, 224, 26,
    { fontSize: 15, color: COLORS.ink, verticalAlignment: "middle" });
  addArrow(slide, "eligibility-arrow", 326, 212, 52, 26, COLORS.blue);
  addShape(slide, "roundRect", "eligibility-check", 388, 184, 390, 84, COLORS.pale, COLORS.border, 1);
  addText(slide, "eligibility-check-title", "Can a node fit both?", 408, 197, 350, 26,
    { fontSize: 16, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addText(slide, "eligibility-check-body", "Remaining CPU ≥ request and remaining RAM ≥ request", 408, 230, 350, 26,
    { fontSize: 14, color: COLORS.ink, verticalAlignment: "middle" });
  addArrow(slide, "eligible-arrow", 790, 212, 48, 26, COLORS.teal);
  addShape(slide, "roundRect", "eligibility-outcome", 850, 184, 374, 84, COLORS.paleTeal, COLORS.border, 1);
  addText(slide, "eligibility-outcome-title", "Eligible nodes are ranked", 870, 197, 334, 26,
    { fontSize: 16, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addText(slide, "eligibility-outcome-body", "If none fit, reject the task", 870, 230, 334, 26,
    { fontSize: 14, color: COLORS.ink, verticalAlignment: "middle" });

  addShape(slide, "rect", "policy-divider", 640, 294, 2, 174, COLORS.border);
  addText(slide, "llf-heading", "Lowest-latency-first", 56, 302, 540, 32,
    { fontSize: 22, bold: true, color: COLORS.blue, verticalAlignment: "middle" });
  addText(slide, "llf-body", "Among eligible nodes, choose the one with the lowest projected latency.\n\nTie-break: stable node ID.", 56, 348, 540, 100,
    { fontSize: 17, color: COLORS.ink });
  addText(slide, "capacity-heading", "Capacity-aware", 680, 302, 540, 32,
    { fontSize: 22, bold: true, color: COLORS.teal, verticalAlignment: "middle" });
  addText(slide, "capacity-body", "Choose the node with the lowest projected bottleneck utilization.\n\nTie-break: projected latency, then stable node ID.", 680, 348, 540, 100,
    { fontSize: 17, color: COLORS.ink });

  addShape(slide, "roundRect", "latency-formula-band", 56, 484, 1168, 70, COLORS.navy, COLORS.navy, 1);
  addText(slide, "latency-formula", "Projected bottleneck = the higher of CPU% and RAM% after placement\nSimulated latency = base latency + 20 ms × projected bottleneck", 80, 495, 1120, 50,
    { fontSize: 17, bold: true, color: COLORS.white, verticalAlignment: "middle" });
  addText(slide, "qos-targets", "QoS assumptions: high ≤ 25 ms     medium ≤ 60 ms     low ≤ 100 ms", 56, 576, 1168, 30,
    { fontSize: 17, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addText(slide, "qos-note", "Sensitivity is checked after placement. It does not change the policy ranking.", 56, 613, 1168, 28,
    { fontSize: 15, color: COLORS.muted, verticalAlignment: "middle" });
  slide.speakerNotes.text = "Both policies first require one node to have enough remaining CPU and RAM. A task that cannot fit on any node is rejected. Lowest-latency-first chooses the eligible node with the lowest base latency plus projected load penalty. Capacity-aware chooses the eligible node that will have the lowest bottleneck utilization after the task is placed. The bottleneck is the larger of projected CPU and RAM percentages. If capacity-aware ties, projected latency comes next, then node ID. The model adds a 20 millisecond penalty at full bottleneck utilization. QoS targets are assumptions: high sensitivity has a 25 ms target, medium 60 ms, low 100 ms. The task sensitivity does not affect ranking in this implementation; it is used to evaluate the final result. Source: cdefsim/placement.py, cdefsim/engine.py, README.md.";
}

// Slide 5: baseline comparison table and native charts.
{
  const slide = deck.slides.add();
  slide.background.fill = COLORS.white;
  addHeader(slide, "Baseline policy comparison", 5);
  addText(slide, "baseline-context", "Same 20 tasks with seed 305. Each policy starts with fresh nodes.", 56, 136, 1168, 24,
    { fontSize: 15, color: COLORS.muted, verticalAlignment: "middle" });
  const llf = baselineByPolicy["lowest-latency-first"];
  const ca = baselineByPolicy["capacity-aware"];
  addTable(slide, 56, 168, 1168, 94, [
    ["Policy", "Placed", "Rejected", "QoS met / missed", "Mean latency", "Edge / Fog / Cloud"],
    ["Lowest-latency-first", String(llf.placed_count), String(llf.rejected_count), `${llf.qos_met_count} / ${llf.qos_missed_count}`, `${round2(llf.mean_simulated_latency_ms)} ms`, "3 / 2 / 7"],
    ["Capacity-aware", String(ca.placed_count), String(ca.rejected_count), `${ca.qos_met_count} / ${ca.qos_missed_count}`, `${round2(ca.mean_simulated_latency_ms)} ms`, "3 / 2 / 7"],
  ], [252, 96, 104, 170, 190, 356], 12);

  addChart(slide, "Placement and QoS totals", { left: 56, top: 284, width: 535, height: 326 },
    ["Placed", "Rejected", "QoS met", "QoS missed"], [
      { name: "Lowest-latency-first", values: [llf.placed_count, llf.rejected_count, llf.qos_met_count, llf.qos_missed_count] },
      { name: "Capacity-aware", values: [ca.placed_count, ca.rejected_count, ca.qos_met_count, ca.qos_missed_count] },
    ], 15, "Tasks", [COLORS.blue, COLORS.teal], 5);

  const utilCategories = ["Edge CPU", "Edge RAM", "Fog CPU", "Fog RAM", "Cloud CPU", "Cloud RAM"];
  const getUtil = (run, nodeId, key) => run.nodes.find((n) => n.node_id === nodeId)[key];
  addChart(slide, "Final CPU and RAM utilization", { left: 612, top: 284, width: 612, height: 326 }, utilCategories, [
    { name: "Lowest-latency-first", values: [
      getUtil(llf, "edge-1", "cpu_utilization_percent"), getUtil(llf, "edge-1", "memory_utilization_percent"),
      getUtil(llf, "fog-1", "cpu_utilization_percent"), getUtil(llf, "fog-1", "memory_utilization_percent"),
      getUtil(llf, "cloud-1", "cpu_utilization_percent"), getUtil(llf, "cloud-1", "memory_utilization_percent"),
    ] },
    { name: "Capacity-aware", values: [
      getUtil(ca, "edge-1", "cpu_utilization_percent"), getUtil(ca, "edge-1", "memory_utilization_percent"),
      getUtil(ca, "fog-1", "cpu_utilization_percent"), getUtil(ca, "fog-1", "memory_utilization_percent"),
      getUtil(ca, "cloud-1", "cpu_utilization_percent"), getUtil(ca, "cloud-1", "memory_utilization_percent"),
    ] },
  ], 100, "% of capacity", [COLORS.blue, COLORS.teal], 25);
  addText(slide, "baseline-takeaway", "Capacity-aware met one more QoS target. Both policies placed 12 tasks, and Cloud RAM reached 100%.", 56, 626, 1168, 28,
    { fontSize: 15, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  slide.speakerNotes.text = `Explain both charts. The policies use the same 20 input tasks. They each place 12 and reject 8. Their tier counts are Edge 3, Fog 2 and Cloud 7. Lowest-latency-first meets 7 QoS targets and misses 5. Capacity-aware meets 8 and misses 4. The mean simulated latency is ${round2(llf.mean_simulated_latency_ms)} ms versus ${round2(ca.mean_simulated_latency_ms)} ms. The utilization chart separates CPU and RAM by node. Cloud RAM is fully reserved for both policies. Fog CPU utilization differs, even though the number of placed tasks per tier is the same, because the task resource sizes differ. Rejections are not QoS misses; QoS is evaluated only for placed tasks. These findings describe this seed and this model, not a universal winner. Source: results/experiments/policy_comparison.json and policy_comparison.csv.`;
}

// Slide 6: overload and capacity-change experiments.
{
  const slide = deck.slides.add();
  slide.background.fill = COLORS.white;
  addHeader(slide, "Overload and capacity change experiments", 6);
  addShape(slide, "rect", "experiment-divider", 632, 150, 2, 500, COLORS.border);
  const overloadLlf = overloadByPolicy["lowest-latency-first"];
  const overloadCa = overloadByPolicy["capacity-aware"];
  addText(slide, "overload-heading", "Overload and fallback", 56, 150, 548, 32,
    { fontSize: 21, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addText(slide, "overload-setup", "Setup: 12 tasks each need 8 CPU and 8 GB RAM.\nTotal CPU demand is 96 units. Total CPU capacity is 88.", 56, 194, 548, 58,
    { fontSize: 14, color: COLORS.ink });
  addText(slide, "overload-result", "Expected: place at most 11, then reject.\nActual: both policies placed 11 and rejected 1.\nEdge / Fog / Cloud placements: 1 / 2 / 8.", 56, 259, 548, 78,
    { fontSize: 15, bold: true, color: COLORS.ink });
  addTable(slide, 56, 346, 548, 86, [
    ["Policy", "Placed / rejected", "Fallback after Edge full"],
    ["Lowest-latency-first", `${overloadLlf.placed_count} / ${overloadLlf.rejected_count}`, String(fallbackCounts["lowest-latency-first"])],
    ["Capacity-aware", `${overloadCa.placed_count} / ${overloadCa.rejected_count}`, String(fallbackCounts["capacity-aware"])],
  ], [215, 166, 167], 11);
  addChart(slide, "Successful fallback placements", { left: 56, top: 444, width: 548, height: 190 },
    ["Lowest-latency-first", "Capacity-aware"], [{ name: "Fallback tasks", values: [fallbackCounts["lowest-latency-first"], fallbackCounts["capacity-aware"]] }],
    12, "Tasks", [COLORS.gold], 3);

  const capacityLlf = capacityByPolicy["lowest-latency-first"];
  const capacityCa = capacityByPolicy["capacity-aware"];
  addText(slide, "capacity-heading", "More Cloud RAM", 662, 150, 544, 32,
    { fontSize: 21, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addText(slide, "capacity-setup", "Setup: same seed-305 workload. Cloud RAM changed from 64 GB to 96 GB.", 662, 194, 544, 44,
    { fontSize: 14, color: COLORS.ink });
  addText(slide, "capacity-result", "Expected: more tasks may fit. QoS can still change.\nActual: each policy placed 3 more tasks.", 662, 246, 544, 50,
    { fontSize: 15, bold: true, color: COLORS.ink });
  addTable(slide, 662, 306, 544, 126, [
    ["Policy", "Placed / rejected", "QoS met", "Mean latency"],
    ["Lowest-latency-first", `${capacityLlf.baseline.placed_count}/${capacityLlf.baseline.rejected_count} → ${capacityLlf.capacity_changed.placed_count}/${capacityLlf.capacity_changed.rejected_count}`, `${capacityLlf.baseline.qos_met_count} → ${capacityLlf.capacity_changed.qos_met_count}`, `${round2(capacityLlf.baseline.mean_simulated_latency_ms)} → ${round2(capacityLlf.capacity_changed.mean_simulated_latency_ms)} ms`],
    ["Capacity-aware", `${capacityCa.baseline.placed_count}/${capacityCa.baseline.rejected_count} → ${capacityCa.capacity_changed.placed_count}/${capacityCa.capacity_changed.rejected_count}`, `${capacityCa.baseline.qos_met_count} → ${capacityCa.capacity_changed.qos_met_count}`, `${round2(capacityCa.baseline.mean_simulated_latency_ms)} → ${round2(capacityCa.capacity_changed.mean_simulated_latency_ms)} ms`],
  ], [170, 150, 83, 141], 10.5);
  addChart(slide, "Placed tasks before and after", { left: 662, top: 444, width: 544, height: 190 },
    ["Lowest-latency-first", "Capacity-aware"], [
      { name: "Cloud RAM 64 GB", values: [capacityLlf.baseline.placed_count, capacityCa.baseline.placed_count] },
      { name: "Cloud RAM 96 GB", values: [capacityLlf.capacity_changed.placed_count, capacityCa.capacity_changed.placed_count] },
    ], 18, "Tasks", [COLORS.blue, COLORS.teal], 3);
  slide.speakerNotes.text = `Overload setup: 12 tasks each request 8 CPU units and 8 GB. Total CPU demand is 96, while Edge, Fog and Cloud together have 88 units. CPU is the limiting resource. Both policies place 11, reject one, and end with Edge/Fog/Cloud counts 1/2/8. The fallback trace shows why the fallback totals differ. Lowest-latency-first uses Edge for its first task, so 10 later successful tasks go to another tier after Edge fills. Capacity-aware keeps Edge eligible while it first uses less-loaded Fog and Cloud; it fills Edge later, so only 2 successful tasks follow Edge becoming unavailable. In the capacity experiment, the same 20 tasks run after Cloud RAM increases from 64 to 96 GB. Both policies place 15 instead of 12. Mean latency rises to about 49.1 ms. Capacity-aware QoS met count drops from 8 to 7. More accepted tasks do not guarantee more tasks meet a latency target. Source: results/experiments/overload_summary.json, overload_trace.csv and capacity_change_comparison.json.`;
}

// Slide 7: VM and tenant demonstrations, limits and reproducible commands.
{
  const slide = deck.slides.add();
  slide.background.fill = COLORS.white;
  addHeader(slide, "VM simulation, tenant access and limits", 7);
  addShape(slide, "rect", "controls-divider", 640, 150, 2, 340, COLORS.border);
  addText(slide, "vm-heading", "VM resource lifecycle", 56, 154, 548, 32,
    { fontSize: 21, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  const stages = [
    { x: 56, w: 150, title: "Create", fill: COLORS.paleGold },
    { x: 234, w: 166, title: "Running", fill: COLORS.paleTeal },
    { x: 428, w: 176, title: "Stop", fill: COLORS.paleBlue },
  ];
  stages.forEach((stage, index) => {
    addShape(slide, "roundRect", `vm-stage-${index}`, stage.x, 204, stage.w, 48, stage.fill, COLORS.border, 1);
    addText(slide, `vm-stage-title-${index}`, stage.title, stage.x + 12, 214, stage.w - 24, 28,
      { fontSize: 16, bold: true, color: COLORS.navy, alignment: "center", verticalAlignment: "middle" });
  });
  addArrow(slide, "vm-stage-arrow-1", 207, 216, 22, 22, COLORS.gold);
  addArrow(slide, "vm-stage-arrow-2", 402, 216, 22, 22, COLORS.blue);
  addText(slide, "vm-copy", "Create checks the VM ID, host and resource fit, then reserves CPU and RAM. Stop releases the reservation and marks the record stopped.", 56, 270, 548, 78,
    { fontSize: 15, color: COLORS.ink });
  addText(slide, "vm-record-fields", "Record fields: VM ID, host node, CPU, RAM and status", 56, 354, 548, 34,
    { fontSize: 14, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addText(slide, "vm-no-real", "The simulator creates no real VM or hypervisor process.", 56, 394, 548, 32,
    { fontSize: 14, color: COLORS.muted, verticalAlignment: "middle" });

  addText(slide, "tenant-heading", "Tenant ownership check", 678, 154, 526, 32,
    { fontSize: 21, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addText(slide, "tenant-owner", "Record owner requests its task", 678, 207, 526, 28,
    { fontSize: 16, bold: true, color: COLORS.green, verticalAlignment: "middle" });
  addText(slide, "tenant-owner-result", "Allowed", 678, 237, 526, 24,
    { fontSize: 14, color: COLORS.ink, verticalAlignment: "middle" });
  addShape(slide, "rect", "tenant-divider", 678, 273, 526, 2, COLORS.border);
  addText(slide, "tenant-other", "A different tenant requests the same task", 678, 290, 526, 28,
    { fontSize: 16, bold: true, color: COLORS.red, verticalAlignment: "middle" });
  addText(slide, "tenant-other-result", "Denied: “Task record unavailable.”\nProtected task contents returned: false", 678, 327, 526, 54,
    { fontSize: 15, color: COLORS.ink });
  addText(slide, "tenant-note", "The same generic denial is used for missing and unauthorized records.", 678, 390, 526, 40,
    { fontSize: 14, color: COLORS.muted });

  addShape(slide, "roundRect", "limitations-band", 56, 510, 1168, 58, COLORS.paleBlue, COLORS.border, 1);
  addText(slide, "limitations", "Model limits: fixed task order, run-long reservations, assumed latency targets, no real execution, network or hardware measurements.", 76, 522, 1128, 34,
    { fontSize: 14, bold: true, color: COLORS.navy, verticalAlignment: "middle" });
  addText(slide, "tests-line", "19 focused tests passed across placement, overload, VM accounting, tenant access and exports.", 56, 585, 1168, 26,
    { fontSize: 15, bold: true, color: COLORS.teal, verticalAlignment: "middle" });
  addShape(slide, "roundRect", "demo-command-panel", 56, 620, 1168, 48, COLORS.navy, COLORS.navy, 1);
  addText(slide, "demo-command", "Demo command:  python main.py --tasks 20 --seed 305     Experiments command:  python scripts/run_experiments.py", 76, 630, 1128, 28,
    { fontSize: 15, bold: true, color: COLORS.white, verticalAlignment: "middle" });
  slide.speakerNotes.text = "A VM is represented only by an in-memory record. It stores a VM ID, host node, CPU, RAM and running or stopped status. Create rejects duplicate IDs, unknown hosts, invalid allocations and requests that do not fit. A successful create reserves node resources. Stop releases resources once. For tenant protection, the store returns a record only when the requesting tenant matches its owner. A cross-tenant or missing-record request produces the same generic message, which avoids revealing task contents or whether the ID exists. This is a basic ownership check, not production authentication. The project has 19 focused unittest checks. To run the demo, use the command on the slide from the project folder; the experiment generator reproduces the four saved scenarios. Main limits: tasks are processed in fixed order, accepted tasks reserve resources until run end, no task code or network traffic is executed, and the latency/QoS values are assumptions. Source: cdefsim/vms.py, cdefsim/security.py, tests/test_core.py, tests/test_reporting.py, README.md.";
}

const draftPath = path.join(STAGE_BUILD, "arm305_project_explainer_english_final_v3_draft.pptx");
await (await PresentationFile.exportPptx(deck)).save(draftPath);

const requirements = {
  explicitTotalSlideCount: 7,
  requiredNativeTableOwnerSlides: [2, 5, 6],
  requiredNativeChartOwnerSlides: [5, 6],
  materializeLiteralChartWorkbooks: true,
  nativeChartTargetApplication: "powerpoint",
};
const validationReceipt = path.join(STAGE_BUILD, "arm305_project_explainer_english_final_v3.validation.json");
const finalizerResult = await finalizePresentation({
  ...requirements,
  workspaceDir: STAGE_ROOT,
  candidatePath: draftPath,
  finalPath: STAGE_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit",
    ...requirements.requiredNativeTableOwnerSlides.flatMap((n) => ["--require-native-table-slide", String(n)])],
  requiredNativeTableOwnerSlides: requirements.requiredNativeTableOwnerSlides,
  fontPolicy: { basis: "design", families: [FONT] },
  verifyArtifactToolImport: true,
  receiptPath: validationReceipt,
});

await fs.copyFile(STAGE_PPTX, FINAL_PPTX);
const finalHash = createHash("sha256").update(await fs.readFile(FINAL_PPTX)).digest("hex");
if (finalHash !== finalizerResult.finalSha256) throw new Error("Final PowerPoint differs from the validated staged file.");
await fs.copyFile(validationReceipt, path.join(BUILD_DIR, "arm305_project_explainer_english_final_v3.validation.json"));

const finalDeck = await PresentationFile.importPptx(await FileBlob.load(FINAL_PPTX));
const renderDir = path.join(BUILD_DIR, "final-slide-renders");
await fs.mkdir(renderDir, { recursive: true });
for (const [index, slide] of finalDeck.slides.items.entries()) {
  const png = await finalDeck.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(path.join(renderDir, `slide-${String(index + 1).padStart(2, "0")}.png`), new Uint8Array(await png.arrayBuffer()));
}
console.log(JSON.stringify({
  finalPath: FINAL_PPTX,
  slideCount: finalDeck.slides.items.length,
  sha256: finalHash,
  packageStatus: finalizerResult.packageIntegrity?.status,
  layoutWarnings: finalizerResult.presentationLayout?.warning_count,
  chartCount: finalizerResult.packageIntegrity?.chart_count,
  validationReceipt: path.join(BUILD_DIR, "arm305_project_explainer_english_final_v3.validation.json"),
}, null, 2));
