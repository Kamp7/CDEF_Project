import fs from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const WORKSPACE = "C:/Users/Kamleshwar Pandey/OneDrive/Desktop/CDEF_Project";
const BUILD_DIR = path.join(WORKSPACE, ".build/presentation");
const FINAL_PPTX = path.join(WORKSPACE, "output/presentation/arm305_mini_project_slides_submission.pptx");
const STAGE_WORKSPACE = "C:/Users/Kamleshwar Pandey/AppData/Local/Temp/arm305-presentation-stage";
const PRIVATE_DIR = path.join(STAGE_WORKSPACE, "build");
const STAGED_PPTX = path.join(STAGE_WORKSPACE, "output/arm305_mini_project_slides_submission_r3.pptx");
const SKILL_DIR = "C:/Users/Kamleshwar Pandey/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/Presentations";
const RUNTIME_NODE_MODULES = "C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules";
const RUNTIME_PYTHON = "C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe";
const ARTIFACT_MODULE = path.join(RUNTIME_NODE_MODULES, "@oai/artifact-tool/dist/artifact_tool.mjs");
const { FileBlob, Presentation, PresentationFile } = await import(pathToFileURL(ARTIFACT_MODULE).href);
const { applyPresentationChartFont, finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);

// This managed Windows filesystem blocks hard links. Preserve create-only output
// semantics with an exclusive byte-for-byte copy; the finalizer then hashes it.
const nativeLink = fs.link;
fs.link = async (source, destination) => {
  try {
    return await nativeLink(source, destination);
  } catch (error) {
    if (error?.code !== "EPERM" && error?.code !== "ENOTSUP") throw error;
    return await fs.copyFile(source, destination, fsConstants.COPYFILE_EXCL);
  }
};

const FONT = "Arial";
const C = {
  navy: "#19324D",
  navy2: "#244562",
  ink: "#233548",
  muted: "#5D7083",
  teal: "#188E8B",
  blue: "#3C78A8",
  gold: "#D49A32",
  red: "#C84C4C",
  green: "#438B62",
  pale: "#F4F7FA",
  paleBlue: "#E5EFF7",
  paleTeal: "#E4F2EF",
  paleGold: "#F8F0DF",
  line: "#D0DBE5",
  white: "#FFFFFF",
};

const evidence = await fs.readFile(path.join(WORKSPACE, "results/experiments/experiment_log.md"), "utf8");
for (const proof of [
  "lowest-latency-first | 20 | 12 | 8 | 7 | 5 | 46.58 ms",
  "capacity-aware | 20 | 12 | 8 | 8 | 4 | 46.59 ms",
  "Fallback placements after Edge became ineligible: lowest-latency-first: 10, capacity-aware: 2.",
  "Cloud RAM from 64 GB to 96 GB",
  "protected contents returned=`False`",
]) {
  if (!evidence.includes(proof)) throw new Error(`Verified experiment log missing expected evidence: ${proof}`);
}

await fs.mkdir(BUILD_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
await fs.mkdir(PRIVATE_DIR, { recursive: true });
await fs.mkdir(path.dirname(STAGED_PPTX), { recursive: true });
const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

function shape(slide, geometry, name, x, y, w, h, fill = "none", lineFill = "none", lineWidth = 0) {
  return slide.shapes.add({
    geometry,
    name,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
  });
}

function text(slide, name, value, x, y, w, h, style = {}) {
  const box = shape(slide, "textbox", name, x, y, w, h);
  box.text = value;
  box.text.style = {
    typeface: FONT,
    fontSize: 18,
    color: C.ink,
    verticalAlignment: "top",
    alignment: "left",
    autoFit: "shrinkText",
    wrap: "square",
    insets: 0,
    ...style,
  };
  return box;
}

function panel(slide, name, x, y, w, h, fill = C.white, border = C.line) {
  return shape(slide, "roundRect", name, x, y, w, h, fill, border, 1.2);
}

function arrow(slide, name, x, y, w, h, color = C.blue, vertical = false) {
  return shape(slide, vertical ? "downArrow" : "rightArrow", name, x, y, w, h, color, "none", 0);
}

function header(slide, title, page) {
  text(slide, `section-${page}`, "ARM 305  /  CDEF TASK PLACEMENT SIMULATOR", 56, 24, 620, 24,
    { fontSize: 12, bold: true, color: C.teal, verticalAlignment: "middle" });
  text(slide, `title-${page}`, title, 56, 56, 1168, 58,
    { fontSize: 34, bold: true, color: C.navy, verticalAlignment: "middle" });
  shape(slide, "rect", `header-rule-${page}`, 56, 126, 1168, 2, C.line);
  text(slide, `page-${page}`, `${page} / 6`, 1150, 684, 74, 18,
    { fontSize: 11, color: C.muted, alignment: "right", verticalAlignment: "middle" });
}

function table(slide, name, x, y, w, h, values, widths, bodyFont = 13) {
  const tbl = slide.tables.add({
    rows: values.length,
    columns: values[0].length,
    left: x,
    top: y,
    width: w,
    height: h,
    columnWidths: widths,
    values,
  });
  tbl.styleOptions = { headerRow: true, bandedRows: true };
  tbl.borders.assign({ style: "solid", fill: C.line, width: 1 });
  for (let r = 0; r < values.length; r += 1) {
    const rowRange = tbl.cells.block({ row: r, column: 0, rowCount: 1, columnCount: values[r].length });
    rowRange.textStyle.fontSize = bodyFont;
    rowRange.textStyle.bold = r === 0;
    rowRange.textStyle.color = r === 0 ? C.white : C.ink;
    rowRange.textStyle.typeface = FONT;
    for (let c = 0; c < values[r].length; c += 1) {
      const cell = tbl.getCell(r, c);
      cell.fill = r === 0 ? C.navy : (r % 2 === 0 ? C.pale : C.white);
    }
    tbl.rows[r].height = h / values.length;
  }
  return tbl;
}

function chart(slide, title, pos, categories, series, yMax, yUnit, colors, yMajor = undefined) {
  const obj = slide.charts.add("bar", {
    position: pos,
    title,
    titlePlacement: "aboveChart",
    titleTextStyle: { fontSize: 17, bold: true, fill: C.navy },
    categories,
    series: series.map((entry, index) => ({ ...entry, fill: colors[index] })),
    hasLegend: true,
    legend: { position: "bottom", overlay: false, textStyle: { fontSize: 11 } },
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 110, overlap: 0 },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { fontSize: 10, bold: true } },
    xAxis: { textStyle: { fontSize: 10 } },
    yAxis: {
      min: 0,
      max: yMax,
      majorUnit: yMajor,
      title: { text: yUnit, textStyle: { fontSize: 11 } },
      textStyle: { fontSize: 10 },
      majorGridlines: { style: "solid", fill: C.line, width: 1 },
    },
    chartFill: C.white,
    chartLine: { style: "solid", fill: C.line, width: 1 },
    plotAreaFill: C.white,
    plotAreaLine: { style: "solid", fill: "none", width: 0 },
  });
  applyPresentationChartFont(obj, { fontFamily: FONT });
  return obj;
}

// Slide 1: title and baseline snapshot.
{
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  shape(slide, "rect", "cover-accent", 0, 0, 15, 720, C.teal);
  text(slide, "cover-eyebrow", "ARM 305  |  MINI PROJECT", 64, 54, 550, 30,
    { fontSize: 15, bold: true, color: "#83D3CC", verticalAlignment: "middle" });
  text(slide, "cover-title", "Cloud, Dev,\nEdge and Fog", 64, 118, 660, 195,
    { fontSize: 56, bold: true, color: C.white, verticalAlignment: "middle" });
  text(slide, "cover-subtitle", "A local task placement simulator", 68, 330, 630, 42,
    { fontSize: 25, color: "#D8E4ED", verticalAlignment: "middle" });
  text(slide, "cover-objective", "Compare two placement rules across simulated Edge, Fog and Cloud resources,\nthen report latency, utilization, overload and tenant ownership checks.",
    68, 398, 660, 82, { fontSize: 18, color: "#D8E4ED" });

  const tierRows = [
    { y: 104, name: "EDGE", sub: "8 CPU  ·  8 GB RAM  ·  5 ms", fill: C.paleBlue, ink: C.navy },
    { y: 224, name: "FOG", sub: "16 CPU  ·  24 GB RAM  ·  20 ms", fill: C.paleTeal, ink: C.navy },
    { y: 344, name: "CLOUD", sub: "64 CPU  ·  64 GB RAM  ·  50 ms", fill: C.paleGold, ink: C.navy },
  ];
  for (const [i, row] of tierRows.entries()) {
    panel(slide, `cover-node-${i}`, 818, row.y, 390, 94, row.fill, "#DCE5ED");
    text(slide, `cover-node-label-${i}`, row.name, 842, row.y + 16, 300, 28,
      { fontSize: 19, bold: true, color: row.ink, verticalAlignment: "middle" });
    text(slide, `cover-node-spec-${i}`, row.sub, 842, row.y + 48, 340, 24,
      { fontSize: 16, color: C.ink, verticalAlignment: "middle" });
  }
  shape(slide, "rect", "cover-summary-band", 64, 548, 1144, 100, "#244562");
  const kpis = [
    ["20", "seeded tasks"],
    ["12 placed / 8 rejected", "both baseline policies"],
    ["8 / 7 QoS met", "capacity-aware / lowest-latency-first"],
  ];
  const kx = [90, 390, 780];
  const kw = [250, 340, 390];
  kpis.forEach(([value, label], i) => {
    text(slide, `cover-kpi-value-${i}`, value, kx[i], 564, kw[i], 34,
      { fontSize: i === 0 ? 31 : 24, bold: true, color: C.white, verticalAlignment: "middle" });
    text(slide, `cover-kpi-label-${i}`, label, kx[i], 602, kw[i], 24,
      { fontSize: 14, color: "#D8E4ED", verticalAlignment: "middle" });
  });
  text(slide, "cover-footnote", "Seed 305  ·  All capacity, latency, utilization and outcomes shown here are simulated.", 68, 668, 950, 22,
    { fontSize: 12, color: "#C3D2DE", verticalAlignment: "middle" });
  slide.speakerNotes.text = "Objective: demonstrate a locally runnable CDEF placement model. Baseline is the verified 20-task workload generated with seed 305. Both policies accepted 12 and rejected 8; capacity-aware met 8 simulated QoS targets and lowest-latency-first met 7. These are model outputs, not hardware or network benchmarks. Evidence: results/experiments/experiment_log.md and results/experiments/policy_comparison.json.";
}

// Slide 2: editable architecture diagram.
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  header(slide, "Architecture: placement, resources and results", 2);
  const blocks = [
    { x: 56, y: 192, w: 196, h: 112, title: "User / CLI", body: "Choose policy\nRun seeded tasks", fill: C.paleBlue },
    { x: 292, y: 192, w: 220, h: 112, title: "Workload generator", body: "CPU · RAM · tenant\nlatency sensitivity", fill: C.pale },
    { x: 554, y: 192, w: 230, h: 112, title: "Placement engine", body: "Eligibility +\none deterministic rule", fill: C.paleTeal },
  ];
  blocks.forEach((b, i) => {
    panel(slide, `architecture-flow-${i}`, b.x, b.y, b.w, b.h, b.fill);
    text(slide, `architecture-flow-title-${i}`, b.title, b.x + 16, b.y + 16, b.w - 32, 28,
      { fontSize: 17, bold: true, color: C.navy, verticalAlignment: "middle" });
    text(slide, `architecture-flow-body-${i}`, b.body, b.x + 16, b.y + 52, b.w - 32, 44,
      { fontSize: 15, color: C.ink });
  });
  arrow(slide, "arrow-cli-workload", 256, 233, 28, 24);
  arrow(slide, "arrow-workload-placement", 518, 233, 28, 24);
  arrow(slide, "arrow-placement-nodes", 790, 233, 40, 24);

  panel(slide, "architecture-node-group", 846, 154, 366, 286, C.pale, C.line);
  text(slide, "architecture-nodes-title", "Simulated resource tiers", 864, 165, 330, 26,
    { fontSize: 17, bold: true, color: C.navy, verticalAlignment: "middle" });
  const nodeRows = [
    ["Edge", "8 CPU / 8 GB / 5 ms", C.paleBlue],
    ["Fog", "16 CPU / 24 GB / 20 ms", C.paleTeal],
    ["Cloud", "64 CPU / 64 GB / 50 ms", C.paleGold],
  ];
  nodeRows.forEach(([name, specs, fill], i) => {
    const yy = 201 + i * 56;
    panel(slide, `architecture-node-${i}`, 864, yy, 330, 44, fill, C.line);
    text(slide, `architecture-node-name-${i}`, name, 878, yy + 7, 82, 28,
      { fontSize: 16, bold: true, color: C.navy, verticalAlignment: "middle" });
    text(slide, `architecture-node-specs-${i}`, specs, 968, yy + 7, 218, 28,
      { fontSize: 13, color: C.ink, verticalAlignment: "middle" });
  });

  const lower = [
    { x: 56, y: 456, w: 300, h: 102, title: "VM manager", body: "Create reserves host CPU/RAM.\nStop releases the reservation.", fill: C.paleGold },
    { x: 412, y: 456, w: 320, h: 102, title: "Tenant-scoped records", body: "Owner check runs before task data\nis returned to the caller.", fill: "#F7EBEB" },
    { x: 886, y: 456, w: 326, h: 102, title: "Results", body: "Per-task CSV · summary JSON\nQoS and utilization charts", fill: C.paleTeal },
  ];
  lower.forEach((b, i) => {
    panel(slide, `architecture-lower-${i}`, b.x, b.y, b.w, b.h, b.fill);
    text(slide, `architecture-lower-title-${i}`, b.title, b.x + 16, b.y + 14, b.w - 32, 28,
      { fontSize: 17, bold: true, color: C.navy, verticalAlignment: "middle" });
    text(slide, `architecture-lower-body-${i}`, b.body, b.x + 16, b.y + 48, b.w - 32, 42,
      { fontSize: 14, color: C.ink });
  });
  text(slide, "vm-resource-link-label", "VM reservations share node capacity", 366, 388, 460, 20,
    { fontSize: 12, bold: true, color: C.gold, alignment: "center", verticalAlignment: "middle" });
  shape(slide, "rect", "vm-resource-stem", 204, 430, 4, 26, C.gold);
  arrow(slide, "arrow-vm-resources", 206, 410, 640, 20, C.gold);
  arrow(slide, "arrow-records-results", 752, 492, 118, 22, C.teal);
  arrow(slide, "arrow-nodes-results", 1000, 440, 26, 12, C.blue, true);
  text(slide, "architecture-sim-note", "Accepted tasks reserve resources until the run ends; each independent policy run starts with fresh nodes.", 56, 610, 1125, 32,
    { fontSize: 15, color: C.muted, verticalAlignment: "middle" });
  slide.speakerNotes.text = "Walk from the CLI and deterministic workload into the placement engine. The engine rejects nodes that lack either CPU or RAM, then runs one of two ranking rules. VM allocations share the node accounting. Task results are stored by tenant and exports are generated locally. All three tiers and all resource use are simulated. Diagram content matches docs/architecture.mmd and docs/architecture.svg.";
}

// Slide 3: models and policy rules.
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  header(slide, "Task model, node capacity and placement rules", 3);
  const nodes = [
    { x: 56, name: "EDGE", cpu: "8 CPU", ram: "8 GB RAM", lat: "5 ms base latency", fill: C.paleBlue },
    { x: 448, name: "FOG", cpu: "16 CPU", ram: "24 GB RAM", lat: "20 ms base latency", fill: C.paleTeal },
    { x: 840, name: "CLOUD", cpu: "64 CPU", ram: "64 GB RAM", lat: "50 ms base latency", fill: C.paleGold },
  ];
  nodes.forEach((n, i) => {
    panel(slide, `model-node-${i}`, n.x, 154, 360, 116, n.fill, C.line);
    text(slide, `model-node-name-${i}`, n.name, n.x + 20, 168, 320, 28,
      { fontSize: 19, bold: true, color: C.navy, verticalAlignment: "middle" });
    text(slide, `model-node-cpu-${i}`, `${n.cpu}   ·   ${n.ram}`, n.x + 20, 202, 320, 24,
      { fontSize: 16, color: C.ink, verticalAlignment: "middle" });
    text(slide, `model-node-latency-${i}`, n.lat, n.x + 20, 232, 320, 20,
      { fontSize: 14, color: C.muted, verticalAlignment: "middle" });
  });
  panel(slide, "task-model-panel", 56, 302, 540, 310, C.pale, C.line);
  text(slide, "task-model-heading", "Task and simulated QoS inputs", 80, 322, 492, 34,
    { fontSize: 22, bold: true, color: C.navy, verticalAlignment: "middle" });
  text(slide, "task-model-copy", "Each task carries:\n\nCPU and RAM requirement\nTenant ID and task ID\nLow / medium / high latency sensitivity\n\nSeed 305 produces the same 20 tasks each run. Accepted tasks reserve CPU/RAM until the run ends; rejected tasks reserve nothing.",
    80, 374, 480, 212, { fontSize: 17, color: C.ink });

  panel(slide, "latency-assumption-panel", 56, 628, 1168, 40, C.paleBlue, C.line);
  text(slide, "latency-assumption", "Assumed sensitivity targets: high ≤ 25 ms  ·  medium ≤ 60 ms  ·  low ≤ 100 ms. Simulated latency = base latency + load penalty.", 72, 633, 1138, 28,
    { fontSize: 14, bold: true, color: C.navy, verticalAlignment: "middle" });

  panel(slide, "policy-rules-panel", 628, 302, 596, 310, C.white, C.line);
  text(slide, "policy-rules-heading", "Two deterministic policies", 652, 322, 540, 34,
    { fontSize: 22, bold: true, color: C.navy, verticalAlignment: "middle" });
  panel(slide, "policy-lowlat-card", 652, 372, 250, 196, C.paleBlue, C.line);
  text(slide, "policy-lowlat-title", "Lowest-latency-first", 670, 390, 216, 32,
    { fontSize: 17, bold: true, color: C.navy, verticalAlignment: "middle" });
  text(slide, "policy-lowlat-body", "1  Check CPU and RAM fit\n2  Rank eligible nodes by projected latency\n3  Tie-break by stable node ID\n4  Reject only when none fit", 670, 430, 216, 122,
    { fontSize: 14, color: C.ink });
  panel(slide, "policy-capacity-card", 926, 372, 274, 196, C.paleTeal, C.line);
  text(slide, "policy-capacity-title", "Capacity-aware", 944, 390, 238, 32,
    { fontSize: 17, bold: true, color: C.navy, verticalAlignment: "middle" });
  text(slide, "policy-capacity-body", "1  Check CPU and RAM fit\n2  Rank by lowest projected bottleneck utilization\n3  Tie-break by projected latency, then node ID\n4  Reject only when none fit", 944, 430, 238, 122,
    { fontSize: 14, color: C.ink });
  slide.speakerNotes.text = "The capacities and base latencies are configurable project assumptions, not course-provided benchmark values. Tasks are processed in fixed order. For projected load, capacity-aware ranks a node by the larger of its post-placement CPU and RAM utilization. Lowest-latency-first ranks by configured latency plus the projected load penalty. Both require sufficient remaining CPU and RAM. QoS targets are explicit assumptions and placement success is reported separately from target success. Evidence: cdefsim/models.py, cdefsim/policies.py, and the README assumptions.";
}

// Slide 4: baseline comparison, editable summary table and native charts.
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  header(slide, "Baseline comparison: same 20 tasks, seed 305", 4);
  text(slide, "baseline-subtitle", "Each policy starts with fresh nodes; acceptance and QoS success are counted separately.", 56, 136, 1168, 24,
    { fontSize: 15, color: C.muted, verticalAlignment: "middle" });
  table(slide, "baseline-policy-comparison", 56, 166, 1168, 100, [
    ["Policy", "Placed", "Rejected", "QoS met / missed", "Mean simulated latency", "Edge / Fog / Cloud"],
    ["Lowest-latency-first", "12", "8", "7 / 5", "46.58 ms", "3 / 2 / 7"],
    ["Capacity-aware", "12", "8", "8 / 4", "46.59 ms", "3 / 2 / 7"],
  ], [270, 105, 110, 180, 215, 288], 13);
  chart(slide, "Task outcomes (count)", { left: 56, top: 286, width: 535, height: 340 },
    ["Placed", "Rejected", "QoS met", "QoS missed"], [
      { name: "Lowest-latency-first", values: [12, 8, 7, 5] },
      { name: "Capacity-aware", values: [12, 8, 8, 4] },
    ], 15, "Tasks", [C.blue, C.teal], 5);
  chart(slide, "Final/peak node utilization (%)", { left: 612, top: 286, width: 612, height: 340 },
    ["Edge CPU", "Edge RAM", "Fog CPU", "Fog RAM", "Cloud CPU", "Cloud RAM"], [
      { name: "Lowest-latency-first", values: [87.5, 87.5, 62.5, 87.5, 57.8, 100] },
      { name: "Capacity-aware", values: [87.5, 87.5, 56.2, 87.5, 59.4, 100] },
    ], 100, "% of capacity", [C.blue, C.teal], 25);
  text(slide, "baseline-summary-note", "Capacity-aware met one more QoS target; both policies placed the same tasks by tier. Cloud RAM reached 100% under both.", 56, 638, 1120, 28,
    { fontSize: 14, bold: true, color: C.navy, verticalAlignment: "middle" });
  slide.speakerNotes.text = "Setup: seed 305, 20 identical task objects, fresh default nodes for each policy. Actual: both placed 12, rejected 8, and used the same Edge/Fog/Cloud placement counts 3/2/7. Lowest-latency-first met 7 QoS targets with mean simulated latency 46.58 ms; capacity-aware met 8 at 46.59 ms. CPU/RAM utilization percent by Edge/Fog/Cloud: lowest-latency-first 87.5/87.5, 62.5/87.5, 57.8/100; capacity-aware 87.5/87.5, 56.2/87.5, 59.4/100. Evidence: results/experiments/policy_comparison.csv, policy_comparison.json, policy_comparison_chart.png.";
}

// Slide 5: required overload and capacity-change experiments.
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  header(slide, "Experiments: overload and capacity change", 5);
  text(slide, "experiment-subtitle", "For each scenario: setup → expected behavior → measured result (simulated).", 56, 136, 1168, 24,
    { fontSize: 15, color: C.muted, verticalAlignment: "middle" });
  panel(slide, "overload-panel", 56, 174, 564, 476, C.pale, C.line);
  panel(slide, "capacity-panel", 640, 174, 584, 476, C.pale, C.line);
  text(slide, "overload-heading", "Overload / fallback", 78, 190, 520, 32,
    { fontSize: 21, bold: true, color: C.navy, verticalAlignment: "middle" });
  text(slide, "overload-setup", "Setup: 12 tasks × 8 CPU / 8 GB; demand 96 CPU vs 88 total.\nExpected: route to another eligible tier, then reject at capacity.\nActual: both policies placed 11 and rejected 1.", 78, 231, 520, 78,
    { fontSize: 14, color: C.ink });
  table(slide, "overload-evidence", 78, 317, 520, 96, [
    ["Policy", "Placed / rejected", "Edge / Fog / Cloud", "Fallback"],
    ["Lowest-latency-first", "11 / 1", "1 / 2 / 8", "10"],
    ["Capacity-aware", "11 / 1", "1 / 2 / 8", "2"],
  ], [176, 118, 144, 82], 11);
  chart(slide, "Placed tasks by tier", { left: 78, top: 426, width: 520, height: 205 },
    ["Edge", "Fog", "Cloud"], [
      { name: "Lowest-latency-first", values: [1, 2, 8] },
      { name: "Capacity-aware", values: [1, 2, 8] },
    ], 10, "Tasks", [C.blue, C.teal], 2);

  text(slide, "capacity-heading", "Cloud RAM increased", 662, 190, 536, 32,
    { fontSize: 21, bold: true, color: C.navy, verticalAlignment: "middle" });
  text(slide, "capacity-setup", "Setup: same seed-305 workload; Cloud RAM 64 → 96 GB.\nExpected: more placements; latency/QoS can shift.\nActual: both placed 3 more (12 → 15); mean latency rose ~2.5 ms.", 662, 231, 536, 78,
    { fontSize: 14, color: C.ink });
  table(slide, "capacity-evidence", 662, 317, 536, 96, [
    ["Policy", "Placed / rejected", "QoS met", "Mean latency"],
    ["Lowest-latency-first", "12/8 → 15/5", "7 → 7", "46.58 → 49.11 ms"],
    ["Capacity-aware", "12/8 → 15/5", "8 → 7", "46.59 → 49.10 ms"],
  ], [178, 146, 83, 129], 11);
  chart(slide, "Placed tasks before / after RAM increase", { left: 662, top: 426, width: 536, height: 205 },
    ["Lowest-latency-first", "Capacity-aware"], [
      { name: "64 GB Cloud RAM", values: [12, 12] },
      { name: "96 GB Cloud RAM", values: [15, 15] },
    ], 18, "Tasks", [C.blue, C.gold], 3);
  slide.speakerNotes.text = "Overload setup: 12 tasks each need 8 CPU and 8 GB RAM; total CPU demand is 96 vs 88 available. Expected at most 11 can be placed, with fallback to another eligible tier and then rejection. Actual both policies placed 11, rejected 1, and used Edge/Fog/Cloud counts 1/2/8. After Edge became ineligible, lowest-latency-first placed 10 elsewhere and capacity-aware placed 2 elsewhere under its ranking. Capacity experiment setup: rerun seed 305, increase only Cloud RAM from 64 to 96 GB. Expected acceptance to improve; latency and QoS may shift. Actual both placed 15/rejected 5, up 3 placed. Mean latency became 49.11 and 49.10 ms. QoS met was 7 for lowest-latency-first and 7 for capacity-aware. Evidence: overload_results.csv, overload_summary.json, overload_trace.csv, capacity_change_comparison.json, capacity_changed_results.csv, capacity_changed_summary.json, all under results/experiments/.";
}

// Slide 6: VM, tenant protection, tests, and reproducible demo.
{
  const slide = presentation.slides.add();
  slide.background.fill = C.white;
  header(slide, "VM lifecycle, tenant checks and reproducibility", 6);
  panel(slide, "vm-panel", 56, 154, 548, 188, C.paleGold, C.line);
  text(slide, "vm-heading", "In-memory VM simulation", 78, 171, 504, 32,
    { fontSize: 21, bold: true, color: C.navy, verticalAlignment: "middle" });
  text(slide, "vm-copy", "Record: VM ID · host node · CPU · RAM · status\nCreate: validate unique ID, known host, positive allocation and fit; reserve node capacity.\nStop: release allocation once and mark stopped. No hypervisor or real VM is started.",
    78, 216, 504, 110, { fontSize: 16, color: C.ink });

  panel(slide, "tenant-panel", 56, 360, 548, 282, "#F8EEEE", "#E5CACA");
  text(slide, "tenant-heading", "Tenant isolation experiment", 78, 378, 504, 32,
    { fontSize: 21, bold: true, color: C.navy, verticalAlignment: "middle" });
  text(slide, "tenant-setup", "Setup: owner reads its stored task; a different tenant requests it.", 78, 423, 504, 42,
    { fontSize: 15, color: C.ink });
  text(slide, "tenant-expected", "Expected: deny without returning protected contents.", 78, 474, 504, 32,
    { fontSize: 15, color: C.ink });
  shape(slide, "roundRect", "tenant-result-badge", 78, 522, 504, 88, "#F1DADA", "#E5CACA", 1);
  text(slide, "tenant-actual", "Actual: owner allowed · cross-tenant denied\nGeneric response: “Task record unavailable.”\nProtected contents returned: false", 96, 532, 468, 70,
    { fontSize: 17, bold: true, color: C.navy, verticalAlignment: "middle" });

  panel(slide, "verification-panel", 632, 154, 592, 488, C.pale, C.line);
  text(slide, "verification-heading", "Verification and demo", 656, 171, 544, 32,
    { fontSize: 21, bold: true, color: C.navy, verticalAlignment: "middle" });
  text(slide, "test-summary", "19 focused unittest checks passed. Coverage includes node eligibility, policy rules and ties, overload/rejection, VM resource accounting, tenant denial, seeded workload, metrics, exports and chart generation.",
    656, 216, 544, 93, { fontSize: 16, color: C.ink });
  text(slide, "limitations-heading", "Model limits", 656, 326, 544, 28,
    { fontSize: 17, bold: true, color: C.teal, verticalAlignment: "middle" });
  text(slide, "limitations-copy", "Tasks run in a fixed sequence; accepted work reserves resources until the run ends. No execution time, queueing, network transport, real VM, or hardware benchmark is modeled. Targets, capacity and latency penalty are explicit assumptions.",
    656, 360, 544, 82, { fontSize: 15, color: C.ink });
  text(slide, "repro-heading", "Repeat the run", 656, 460, 544, 28,
    { fontSize: 17, bold: true, color: C.teal, verticalAlignment: "middle" });
  shape(slide, "roundRect", "repro-command-box", 656, 496, 544, 126, C.navy, C.navy);
  text(slide, "repro-commands", "python -m pip install -r requirements.txt\npython main.py --tasks 20 --seed 305\npython scripts/run_experiments.py\npython -m unittest discover -s tests -v",
    676, 511, 504, 98, { fontSize: 15, color: C.white, verticalAlignment: "middle" });
  slide.speakerNotes.text = "VM records are in memory only and account against the same node CPU/RAM pool. Tenant access is an ownership check rather than authentication. The cross-tenant response matches the missing-record response and returns no task contents. The current test suite had 19 passing checks when the report was built. To reproduce, install requirements, run the seeded CLI, run the experiment generator, and run unittest. Limitations should be stated clearly in the viva: this is a deterministic classroom simulation, not a live cloud deployment or benchmark. Evidence: results/experiments/tenant_isolation.json and the test run recorded during report generation.";
}

const draftPath = path.join(PRIVATE_DIR, "arm305_slides_draft.pptx");
const draft = await PresentationFile.exportPptx(presentation);
await draft.save(draftPath);

const requirements = {
  explicitTotalSlideCount: 6,
  requiredNativeTableOwnerSlides: [4, 5],
  requiredNativeChartOwnerSlides: [4, 5],
  materializeLiteralChartWorkbooks: true,
  nativeChartTargetApplication: "powerpoint",
};
const result = await finalizePresentation({
  ...requirements,
  workspaceDir: STAGE_WORKSPACE,
  candidatePath: draftPath,
  finalPath: STAGED_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit",
    ...requirements.requiredNativeTableOwnerSlides.flatMap((n) => ["--require-native-table-slide", String(n)])],
  requiredNativeTableOwnerSlides: requirements.requiredNativeTableOwnerSlides,
  fontPolicy: { basis: "design", families: [FONT] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(PRIVATE_DIR, "arm305_mini_project_slides_submission_r3.validation.json"),
});

// Render every slide from the finalized package for visual inspection.
await fs.copyFile(STAGED_PPTX, FINAL_PPTX);
await fs.copyFile(path.join(PRIVATE_DIR, "arm305_mini_project_slides_submission_r3.validation.json"), path.join(BUILD_DIR, "arm305_mini_project_slides_submission.validation.json"));
const finalPresentation = await PresentationFile.importPptx(await FileBlob.load(FINAL_PPTX));
const renderedDir = path.join(BUILD_DIR, "final-slide-renders");
await fs.mkdir(renderedDir, { recursive: true });
for (const [index, slide] of finalPresentation.slides.items.entries()) {
  const png = await finalPresentation.export({ slide, format: "png", scale: 1 });
  const file = path.join(renderedDir, `slide-${String(index + 1).padStart(2, "0")}.png`);
  await fs.writeFile(file, new Uint8Array(await png.arrayBuffer()));
}
console.log(JSON.stringify({ finalPath: FINAL_PPTX, draftPath, stagedFinalPath: STAGED_PPTX, slideCount: finalPresentation.slides.items.length, finalizer: result }, null, 2));
