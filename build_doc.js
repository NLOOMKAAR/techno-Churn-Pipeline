const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, ImageRun, AlignmentType, BorderStyle, PageBreak,
} = require("docx");

const C = "charts";
const S = "logs/api_test_evidence/screenshots";

function img(path, width, height) {
  return new ImageRun({ type: "png", data: fs.readFileSync(path), transformation: { width, height } });
}
function h(text, level = HeadingLevel.HEADING_1) {
  return new Paragraph({ text, heading: level, spacing: { before: 300, after: 150 } });
}
function p(text, opts = {}) {
  return new Paragraph({ children: [new TextRun({ text, ...opts })], spacing: { after: 150 } });
}
function bullet(text) {
  return new Paragraph({ text, bullet: { level: 0 }, spacing: { after: 60 } });
}
function caption(text) {
  return new Paragraph({
    children: [new TextRun({ text, italics: true, size: 18, color: "555555" })],
    alignment: AlignmentType.CENTER, spacing: { after: 240 },
  });
}
function imgPara(path, w, h_) {
  return new Paragraph({ children: [img(path, w, h_)], alignment: AlignmentType.CENTER, spacing: { after: 80 } });
}

const cellBorders = {
  top: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
  bottom: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
  left: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
  right: { style: BorderStyle.SINGLE, size: 2, color: "CCCCCC" },
};
function cell(text, opts = {}) {
  return new TableCell({
    width: { size: opts.width || 2000, type: WidthType.DXA },
    shading: opts.header ? { type: ShadingType.CLEAR, fill: "2C3E50" } : undefined,
    borders: cellBorders,
    children: [new Paragraph({
      children: [new TextRun({ text, bold: !!opts.header, color: opts.header ? "FFFFFF" : "000000", size: 20 })],
    })],
  });
}
function table(headerCells, rows, widths) {
  return new Table({
    width: { size: 9000, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({ children: headerCells.map((t, i) => cell(t, { header: true, width: widths[i] })) }),
      ...rows.map(r => new TableRow({ children: r.map((t, i) => cell(String(t), { width: widths[i] })) })),
    ],
  });
}

const doc = new Document({
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 } } },
    children: [
      // ---------------- TITLE PAGE ----------------
      new Paragraph({ text: "AIMLCZG549 - API-Driven Cloud Native Solutions", heading: HeadingLevel.TITLE, alignment: AlignmentType.CENTER, spacing: { before: 800, after: 100 } }),
      new Paragraph({ text: "Assignment I - Project Report", heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, spacing: { after: 400 } }),
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { after: 100 },
        children: [new TextRun({ text: "Cloud-Native Telecom Customer Churn DataOps Pipeline", bold: true, size: 28 })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER, spacing: { after: 600 },
        children: [new TextRun({ text: "Project: Telco Customer Churn DataOps Pipeline", size: 22, color: "C0392B" })],
      }),
      p("Group Members and Contributions", { bold: true, size: 22 }),
      table(
        ["Name", "BITS ID", "Contribution"],
        [
          ["Oomkaar NL", "2025af05057", "Data ingestion, pre-processing, EDA, DataOps scheduling/logging, Docker/cloud deployment, API design & testing (all activities)"],
          ["<Member 2 Name>", "<ID>", "<Fill in if group has additional members>"],
          ["<Member 3 Name>", "<ID>", "<Fill in if group has additional members>"],
          ["<Member 4 Name>", "<ID>", "<Fill in if group has additional members>"],
        ],
        [3000, 1800, 4200]
      ),
      caption("(Assignment allows groups of 2-4 members. Add remaining teammates' names/IDs/contributions, or remove unused rows if submitting with fewer members; confirm your program allows solo submission before removing rows.)"),
      new Paragraph({ children: [new PageBreak()] }),

      // ---------------- 1. BUSINESS UNDERSTANDING ----------------
      h("1. Business Understanding (Activity 1.1)"),
      p("A telecom operator wants to proactively identify customers who are likely to churn " +
        "(cancel their subscription) so that retention teams can intervene with targeted offers " +
        "before the customer actually leaves. Customer acquisition costs substantially more than " +
        "retention, so an early-warning system based on account, billing, and service-usage " +
        "attributes has direct commercial value. This project builds an automated, containerized, " +
        "cloud-deployable data pipeline that ingests customer data, cleans and prepares it, runs " +
        "exploratory analysis to surface the strongest churn drivers, and exposes the entire " +
        "pipeline's operational state through REST APIs and a live dashboard."),

      // ---------------- 2. DATA INGESTION ----------------
      h("2. Data Ingestion (Activity 1.2)"),
      p("Dataset: IBM \u201cTelco Customer Churn\u201d dataset, originally published on Kaggle " +
        "(https://www.kaggle.com/datasets/blastchar/telco-customer-churn). It contains 7,043 " +
        "customer records across 21 columns, which is sufficient for a meaningful churn-prediction " +
        "experiment (26.5% positive class / churn rate)."),
      p("Because Kaggle's own download API requires an authenticated kaggle.json token - impractical " +
        "inside an automated, unattended cloud pipeline - the ingestion script (generate_data.py) " +
        "pulls the identical public CSV over HTTPS from a GitHub mirror, and automatically falls back " +
        "to a bundled local copy of the same file if network access is unavailable, so the DataOps " +
        "schedule (Section 5) never breaks."),
      table(
        ["Property", "Value"],
        [
          ["Source", "Kaggle - Telco Customer Churn (IBM sample dataset)"],
          ["Rows ingested", "7,043"],
          ["Columns", "21 (raw) -> 24 after preprocessing/normalization"],
          ["Target variable", "Churn (Yes / No)"],
          ["Class balance", "26.54% Yes / 73.46% No"],
        ],
        [3000, 6000]
      ),

      // ---------------- 3. PRE-PROCESSING ----------------
      h("3. Data Pre-processing (Activity 1.3)"),
      p("Implemented in preprocessing.py, executed automatically as the first stage of every " +
        "pipeline run:"),
      bullet("Summary statistics - describe() computed over all numeric columns (count, mean, std, min/max, quartiles)."),
      bullet("Missing-value detection - the raw dataset has 11 records (0.16%) where TotalCharges arrives as a blank string, a classic real-world data-quality issue in this dataset."),
      bullet("Data-type correction - TotalCharges is coerced from object/string to numeric (float) before any statistics are computed."),
      bullet("Imputation - missing numeric values are filled with the column median (robust to skew/outliers)."),
      bullet("Normalization - tenure, MonthlyCharges and TotalCharges are min-max scaled into new *_norm columns for downstream modelling."),
      p("Missing-value report captured by a real pipeline run:", { bold: true }),
      table(
        ["Column", "Missing Count", "Missing %"],
        [["TotalCharges", "11", "0.16%"]],
        [4000, 2500, 2500]
      ),

      // ---------------- 4. EDA ----------------
      new Paragraph({ children: [new PageBreak()] }),
      h("4. Exploratory Data Analysis (Activity 1.4)"),
      p("Implemented in eda.py: tenure binning, label-encoding of all categorical features, a " +
        "correlation matrix over encoded + numeric features, RandomForest-based feature importance, " +
        "and six univariate/bivariate visualizations, all regenerated automatically on every pipeline run."),
      p("Top correlations with churn (encoded features):", { bold: true }),
      table(
        ["Feature", "Correlation with Churn"],
        [
          ["Contract_enc", "0.397"],
          ["tenure", "0.352"],
          ["tenure_bin_enc", "0.345"],
          ["OnlineSecurity_enc", "0.289"],
          ["TechSupport_enc", "0.282"],
        ],
        [5000, 4000]
      ),
      p("Top feature importances (RandomForestClassifier):", { bold: true }),
      table(
        ["Feature", "Importance"],
        [
          ["Contract_enc", "0.169"],
          ["tenure", "0.156"],
          ["MonthlyCharges", "0.112"],
          ["TotalCharges", "0.106"],
          ["OnlineSecurity_enc", "0.081"],
        ],
        [5000, 4000]
      ),
      p("Interpretation: contract type is the single strongest churn driver by a wide margin - " +
        "month-to-month customers churn far more than one/two-year contract holders - followed by " +
        "tenure and monthly billing amount, consistent with well-known findings on this dataset."),

      imgPara(`${C}/01_churn_distribution.png`, 260, 208),
      caption("Fig 1. Univariate - Churn class distribution"),
      imgPara(`${C}/02_monthly_charges_hist.png`, 260, 208),
      caption("Fig 2. Univariate - Monthly charges distribution"),
      imgPara(`${C}/03_churn_by_tenure_bin.png`, 280, 204),
      caption("Fig 3. Bivariate - Churn rate by tenure bin"),
      imgPara(`${C}/04_churn_by_contract.png`, 300, 225),
      caption("Fig 4. Bivariate - Churn proportion by contract type"),
      imgPara(`${C}/05_correlation_heatmap.png`, 380, 326),
      caption("Fig 5. Correlation heatmap (encoded features)"),
      imgPara(`${C}/06_feature_importance.png`, 340, 283),
      caption("Fig 6. Top 10 feature importances (RandomForest)"),

      // ---------------- 5. DATAOPS ----------------
      new Paragraph({ children: [new PageBreak()] }),
      h("5. DataOps - Scheduling, Logging & Dashboard (Activity 1.5)"),
      p("pipeline.py automates Activities 1.3 and 1.4 into a single repeatable run: every execution " +
        "is timestamped, logged to logs/pipeline.log (human-readable) and appended as a structured " +
        "JSON record to logs/run_history.json (machine-readable, consumed by the API and dashboard)."),
      p("scheduler.py uses APScheduler's BackgroundScheduler with an interval trigger of exactly " +
        "2 minutes to satisfy the DataOps scheduling requirement. Sample log excerpt from an actual " +
        "run of this project, showing genuine ~2-minute spacing between automated runs:", { bold: true }),
      ...[
        "2026-09-25 09:49:30 | Scheduler STARTED: dataops_pipeline_job will run every 2 minutes",
        "2026-09-25 09:49:32 | [run-20260925T094930] Pipeline run ENDED | status=SUCCESS | duration=2.09s",
        "2026-09-25 09:51:32 | [run-20260925T095130] Pipeline run ENDED | status=SUCCESS | duration=1.96s",
        "2026-09-25 09:53:32 | [run-20260925T095330] Pipeline run ENDED | status=SUCCESS | duration=2.00s",
      ].map(line => new Paragraph({
        children: [new TextRun({ text: line, font: "Courier New", size: 18, color: "22AA55" })],
        shading: { type: ShadingType.CLEAR, fill: "1E1E1E" },
        spacing: { after: 0 },
      })),
      p(""),
      p("Consecutive runs land 120 seconds apart (09:49:32 \u2192 09:51:32 \u2192 09:53:32), confirming " +
        "the interval trigger fires correctly on schedule (this fixes an earlier bug where passing " +
        "next_run_time=None to APScheduler's add_job() left the job paused instead of scheduling it " +
        "for now + interval)."),
      p("The dashboard (GET /dashboard) renders this run history as an auto-refreshing HTML page:"),
      imgPara(`${C}/07_dashboard_screenshot.png`, 380, 330),
      caption("Fig 7. Live DataOps dashboard - run history, status, duration, and top churn drivers"),

      // ---------------- 6. DEPLOYMENT ----------------
      h("6. Containerization & Cloud Deployment"),
      p("The application is packaged as a single Docker image (Dockerfile). entrypoint.sh starts " +
        "the APScheduler background worker (scheduler.py) and the FastAPI server (uvicorn) together " +
        "in one container, which is how the image is meant to run on a managed container platform:"),
      bullet("Google Cloud Run: gcloud run deploy --image ... --min-instances=1 --port 8000"),
      bullet("AWS ECS Fargate: push image to ECR, run as a Fargate service behind an ALB, health-check on /health"),
      bullet("Azure Container Apps: az containerapp up --source . --ingress external --target-port 8000"),
      p("A live cloud-hosted dashboard snapshot (Figure 7's data, hosted at a public URL rather than " +
        "localhost) is available here for grading/demo purposes:"),
      p("https://claude.ai/artifact/YNwYnEhqVwWeUypunmbvuF", { bold: true, color: "2C6E8E" }),
      p("For a fully production-style deployment where the dashboard/API run continuously and self-" +
        "refresh on the same 2-minute schedule, the group should deploy the Docker image above to " +
        "their own Google Cloud Run / AWS ECS / Azure Container Apps account (exact one-line deploy " +
        "commands are in README.md) and capture a screenshot of that live URL for the final submission.", { italics: true }),

      // ---------------- 7. API ACCESS ----------------
      new Paragraph({ children: [new PageBreak()] }),
      h("7. API Access (Sub-Objective 2)"),
      p("7.1 / 7.2 - Application details exposed via API (Activities 3.1, 3.2)", { bold: true }),
      p("The FastAPI application (api/main.py) exposes the following application/deployment/flow " +
        "details as REST endpoints - well above the minimum of four required:"),
      table(
        ["#", "Endpoint", "Application Detail Exposed"],
        [
          ["1", "GET /api/app/info", "App name, version, environment, deployment target, uptime"],
          ["2", "GET /api/app/flow", "Pipeline stage/flow definition & schedule"],
          ["3", "GET /api/pipeline/runs", "Full DataOps run history"],
          ["4", "GET /api/pipeline/latest", "Latest run's status & metrics"],
          ["5", "GET /api/dataset/info", "Dataset schema, row/column counts, churn rate"],
          ["6", "GET /api/eda/feature-importance", "Latest churn-driver feature importances"],
          ["7", "GET /health", "Liveness/readiness probe"],
        ],
        [700, 3300, 5000]
      ),
      p(""),
      p("7.3 - API Testing and Documentation (Activity 3.3)", { bold: true }),
      p("Every endpoint was tested with curl against the live running service; HTTP status codes " +
        "and JSON response bodies were captured for each call, including a negative test against a " +
        "non-existent route to confirm correct 404 handling. A Postman collection " +
        "(postman_collection.json) is also provided for interactive re-testing."),

      imgPara(`${S}/health.png`, 380, 98),
      caption("GET /health -> 200 OK"),
      imgPara(`${S}/api_app_info.png`, 380, 172),
      caption("GET /api/app/info -> 200 OK"),
      imgPara(`${S}/api_app_flow.png`, 380, 403),
      caption("GET /api/app/flow -> 200 OK"),
      imgPara(`${S}/api_dataset_info.png`, 380, 393),
      caption("GET /api/dataset/info -> 200 OK"),
      imgPara(`${S}/api_eda_feature-importance.png`, 380, 298),
      caption("GET /api/eda/feature-importance -> 200 OK"),
      imgPara(`${S}/api_pipeline_latest.png`, 380, 498),
      caption("GET /api/pipeline/latest -> 200 OK"),
      imgPara(`${S}/api_pipeline_runs_compact.png`, 380, 550),
      caption("GET /api/pipeline/runs?limit=2 -> 200 OK"),
      imgPara(`${S}/negative_test_404.png`, 380, 88),
      caption("Negative test: GET /api/nonexistent -> 404 Not Found (correct error handling verified)"),

      // ---------------- 8. CONCLUSION ----------------
      new Paragraph({ children: [new PageBreak()] }),
      h("8. Conclusion"),
      p("This project delivers an end-to-end, cloud-deployable DataOps pipeline for telecom churn " +
        "analysis: real public data ingestion, automated pre-processing and EDA, a 2-minute scheduled " +
        "DataOps loop with structured logging and a live dashboard, and a documented, tested REST API " +
        "surface exposing application, pipeline, dataset and model-insight details. Contract type, " +
        "tenure, and monthly charges emerged as the dominant churn drivers, actionable findings a " +
        "retention team could use directly."),
      p("A short video walkthrough of the running pipeline, dashboard and API is included as a " +
        "separate submission per the assignment's video-demo requirement.", { italics: true }),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("Assignment1_Telco_Churn_Report.docx", buf);
  console.log("Written Assignment1_Telco_Churn_Report.docx");
});
