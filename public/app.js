// Sales Sherlock — orchestrator
//
// Flow:
//   POST /api/research          -> dossier + sources
//   POST /api/section x 8 (parallel) for sections 1-7 + 9
//   POST /api/section (psychographic, sequential) with prior_sections
//   POST /api/section (executive_read, synthesis) with all 9 priors
//   POST /api/render            -> rendered HTML
//
// Each step emits stepper updates so the user sees progress through
// the 60-90s pipeline rather than a dead spinner.

const PARALLEL_SECTIONS = [
  ["company_overview",       "Company overview"],
  ["company_history",        "Company history"],
  ["investment_ownership",   "Investment & ownership"],
  ["growth_revenue_signals", "Growth & revenue signals"],
  ["industry_competitive",   "Industry & competitive"],
  ["contact_professional",   "Contact professional profile"],
  ["contact_personal",       "Contact personal profile"],
  ["hooks_and_risks",        "Hooks & risks"],
];
const PRIOR_SECTION_HEADINGS = {
  company_overview:        "Company Overview",
  company_history:         "Company History",
  investment_ownership:    "Investment and Ownership",
  growth_revenue_signals:  "Growth and Revenue Signals",
  industry_competitive:    "Industry and Competitive Landscape",
  contact_professional:    "Contact Professional Profile",
  contact_personal:        "Contact Personal and Public Profile",
  hooks_and_risks:         "Conversational Hooks and Risks",
  psychographic:           "Psychographic and Decision-Making Profile",
};

// Order in which the nine prior sections are stitched together for the
// executive_read synthesis call. Mirrors the final brief reading order.
const EXECUTIVE_READ_PRIOR_ORDER = [
  "company_overview",
  "company_history",
  "investment_ownership",
  "growth_revenue_signals",
  "industry_competitive",
  "contact_professional",
  "contact_personal",
  "psychographic",
  "hooks_and_risks",
];

const $ = (id) => document.getElementById(id);
const form          = $("briefForm");
const linkedinEl    = $("linkedin");
const charcountEl   = $("charcount");
const generateBtn   = $("generate");
const progressEl    = $("progress");
const stepsEl       = $("steps");
const resultEl      = $("result");
const briefFrame    = $("briefFrame");
const alertEl       = $("alert");
const apolloWrap    = $("apolloToggleWrap");
const keyStatus     = $("keyStatus");

let lastHtml = null;
let lastMd = null;
let lastSources = [];

// ---------- char counter ----------
linkedinEl.addEventListener("input", updateCharCount);
function updateCharCount() {
  const n = linkedinEl.value.trim().length;
  charcountEl.textContent =
    n + " chars" + (n < 800 ? " (need at least 800)" : " — sufficient");
  charcountEl.classList.toggle("warn", n < 800);
}
updateCharCount();

// ---------- env probe ----------
fetch("/api/health").then(r => r.json()).then(env => {
  if (env.has_anthropic_key) {
    keyStatus.textContent = "API key live";
    keyStatus.classList.remove("missing");
  } else {
    keyStatus.textContent = "API key missing";
    keyStatus.classList.add("missing");
    showAlert("Server is missing ANTHROPIC_API_KEY. Set it in Vercel and redeploy before generating a brief.");
  }
  if (env.has_apollo_key) apolloWrap.style.display = "flex";
}).catch(() => {
  keyStatus.textContent = "health check failed";
  keyStatus.classList.add("missing");
});

// ---------- stepper ----------
const SEARCH_KINDS = [
  ["news",             "Searching: recent news"],
  ["funding",          "Searching: funding & ownership"],
  ["jobs",             "Searching: open jobs"],
  ["linkedin_company", "Searching: LinkedIn company page"],
  ["interviews",       "Searching: interviews & talks"],
];

function buildStepper(useWebSearch) {
  stepsEl.innerHTML = "";
  const steps = [
    { id: "parse", label: "Parsing paste & fetching company site" },
  ];
  if (useWebSearch) {
    for (const [k, label] of SEARCH_KINDS) {
      steps.push({ id: "search-" + k, label });
    }
  }
  for (const [id, label] of PARALLEL_SECTIONS) {
    steps.push({ id: "sec-" + id, label: "Writing: " + label });
  }
  steps.push({ id: "sec-psychographic", label: "Synthesizing: Psychographic & decision-making profile" });
  steps.push({ id: "sec-executive_read", label: "Synthesizing: Executive read (page 1)" });
  steps.push({ id: "render", label: "Rendering brief" });
  for (const s of steps) {
    const el = document.createElement("div");
    el.className = "step";
    el.id = "step-" + s.id;
    el.innerHTML = `<span class="dot"></span><span>${s.label}</span>`;
    stepsEl.appendChild(el);
  }
  progressEl.classList.add("active");
}
function setStep(id, state) {
  const el = $("step-" + id);
  if (!el) return;
  el.classList.remove("run", "done", "err");
  el.classList.add(state);
}

// ---------- alert ----------
function showAlert(msg, kind = "err") {
  alertEl.textContent = msg;
  alertEl.classList.remove("err", "warn");
  alertEl.classList.add(kind);
  alertEl.classList.add("active");
}
function clearAlert() { alertEl.classList.remove("active"); }

// ---------- main flow ----------
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearAlert();

  const linkedin_text = linkedinEl.value.trim();
  if (linkedin_text.length < 800) {
    showAlert("LinkedIn paste is too thin. Need at least 800 characters and the About + Experience sections.");
    return;
  }

  const useWebSearch = $("webSearch").checked;
  const useApollo    = $("apollo") ? $("apollo").checked : false;

  const payload = {
    linkedin_text,
    company:     $("company").value.trim(),
    context:     $("context").value.trim() || "Discovery call",
    positioning: $("positioning").value.trim() || null,
    no_apollo:   !useApollo,
    no_web_search: !useWebSearch,
  };

  generateBtn.disabled = true;
  generateBtn.textContent = "Generating...";
  resultEl.classList.remove("active");
  buildStepper(useWebSearch);

  try {
    setStep("parse", "run");
    const research = await postJSON("/api/research", payload);
    setStep("parse", "done");

    const dossier = research.dossier;

    // Web search stage: orchestrated client-side, batched 2 at a time
    // to stay under the per-minute token cap on Anthropic. Each /api/search
    // is one Haiku web_search and finishes in ~10s.
    if (useWebSearch) {
      const SEARCH_BATCH = 2;
      const contactName = dossier?.linkedin?.name || null;
      for (let i = 0; i < SEARCH_KINDS.length; i += SEARCH_BATCH) {
        const batch = SEARCH_KINDS.slice(i, i + SEARCH_BATCH);
        await Promise.all(batch.map(async ([kind]) => {
          setStep("search-" + kind, "run");
          try {
            const r = await postJSON("/api/search", {
              kind,
              company: payload.company,
              contact_name: contactName,
            });
            for (const h of r.hits || []) {
              const id = "S" + (dossier.sources.length + 1);
              dossier.sources.push({
                id,
                kind,
                url: h.url,
                title: h.title,
                content: h.summary,
                fetched_at: new Date().toISOString().slice(0, 10),
              });
            }
            setStep("search-" + kind, "done");
          } catch (err) {
            // Non-fatal: a missing category is fine.
            setStep("search-" + kind, "err");
          }
        }));
      }
    }

    // Run sections in batches of 3 to stay under the per-minute token cap.
    // 8 parallel section calls × ~5K input tokens each is 40K instant burst,
    // which exceeds the Sonnet 30K-tokens-per-minute developer-tier limit.
    const BATCH_SIZE = 3;
    const sectionEntries = [];
    for (let i = 0; i < PARALLEL_SECTIONS.length; i += BATCH_SIZE) {
      const batch = PARALLEL_SECTIONS.slice(i, i + BATCH_SIZE);
      const batchResults = await Promise.all(batch.map(async ([sid]) => {
        setStep("sec-" + sid, "run");
        try {
          const r = await postJSON("/api/section", {
            section_id: sid,
            dossier,
            prior_sections: "",
          });
          setStep("sec-" + sid, "done");
          return [sid, r.body];
        } catch (err) {
          setStep("sec-" + sid, "err");
          throw err;
        }
      }));
      sectionEntries.push(...batchResults);
    }
    const sections = Object.fromEntries(sectionEntries);

    // Build prior_sections for the psychographic call.
    const priorParts = PARALLEL_SECTIONS.map(([sid]) => {
      const heading = PRIOR_SECTION_HEADINGS[sid];
      return `### ${heading}\n\n${sections[sid] || ""}`;
    });
    const prior_sections = priorParts.join("\n\n");

    setStep("sec-psychographic", "run");
    const psy = await postJSON("/api/section", {
      section_id: "psychographic",
      dossier,
      prior_sections,
    });
    setStep("sec-psychographic", "done");
    sections.psychographic = psy.body;

    // Executive read: synthesizes all nine prior sections into the
    // page-one card (quick stats, three priorities, entry hypothesis,
    // three high-leverage questions). Best-effort: a failure here
    // shouldn't kill the brief, just thin out page 1.
    setStep("sec-executive_read", "run");
    const execPriorParts = EXECUTIVE_READ_PRIOR_ORDER
      .filter((sid) => sections[sid])
      .map((sid) => `### ${PRIOR_SECTION_HEADINGS[sid]}\n\n${sections[sid]}`);
    try {
      const execRead = await postJSON("/api/section", {
        section_id: "executive_read",
        dossier,
        prior_sections: execPriorParts.join("\n\n"),
      });
      sections.executive_read = execRead.body;
      setStep("sec-executive_read", "done");
    } catch (err) {
      console.warn("Executive read failed; continuing without it.", err);
      setStep("sec-executive_read", "err");
    }

    setStep("render", "run");
    const [htmlR, mdR] = await Promise.all([
      postJSON("/api/render", { dossier, sections, format: "html" }),
      postJSON("/api/render", { dossier, sections, format: "md" }),
    ]);
    setStep("render", "done");

    lastHtml = htmlR.content;
    lastMd = mdR.content;
    lastSources = dossier.sources || [];

    showResult(lastHtml);
  } catch (err) {
    showAlert(err.message || String(err));
    console.error(err);
  } finally {
    generateBtn.disabled = false;
    generateBtn.textContent = "Generate brief";
  }
});

async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    let detail = "Request failed: " + resp.status;
    try {
      const err = await resp.json();
      detail = err.detail || JSON.stringify(err);
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return resp.json();
}

function showResult(html) {
  // Drop the rendered brief into the iframe via document.write so styles live.
  const doc = briefFrame.contentDocument;
  doc.open();
  doc.write(html);
  doc.close();
  resultEl.classList.add("active");
  resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------- result actions ----------
$("copyHtml").addEventListener("click", async () => {
  if (!lastHtml) return;
  await navigator.clipboard.writeText(lastHtml);
  $("copyHtml").textContent = "Copied!";
  setTimeout(() => $("copyHtml").textContent = "Copy HTML", 1400);
});
$("downloadHtml").addEventListener("click", () => {
  if (!lastHtml) return;
  download("brief.html", lastHtml, "text/html");
});
$("downloadMd").addEventListener("click", () => {
  if (!lastMd) return;
  download("brief.md", lastMd, "text/markdown");
});
$("printBrief").addEventListener("click", () => {
  if (briefFrame.contentWindow) briefFrame.contentWindow.print();
});
$("newBrief").addEventListener("click", () => {
  resultEl.classList.remove("active");
  progressEl.classList.remove("active");
  window.scrollTo({ top: 0, behavior: "smooth" });
});

function download(filename, text, mime) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
}
