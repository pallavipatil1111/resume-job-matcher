const form = document.getElementById("match-form");
const fileInput = document.getElementById("resume-file");
const fileLabel = document.getElementById("file-label");
const resumeText = document.getElementById("resume-text");
const jobText = document.getElementById("job-text");
const errorBox = document.getElementById("form-error");
const button = document.getElementById("score-btn");
const results = document.getElementById("results");
let mode = "upload";

// ----- tabs: upload a PDF or paste text -----
const tabs = { upload: document.getElementById("tab-upload"), paste: document.getElementById("tab-paste") };
const panes = { upload: document.getElementById("pane-upload"), paste: document.getElementById("pane-paste") };
function selectTab(next) {
  mode = next;
  for (const key of Object.keys(tabs)) {
    tabs[key].setAttribute("aria-selected", String(key === next));
    panes[key].hidden = key !== next;
  }
}
tabs.upload.addEventListener("click", () => selectTab("upload"));
tabs.paste.addEventListener("click", () => selectTab("paste"));

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  fileLabel.textContent = file ? file.name : "Choose a PDF";
  fileInput.closest(".drop").classList.toggle("has-file", Boolean(file));
});

// ----- helpers -----
function fillList(id, items, emptyId) {
  const list = document.getElementById(id);
  list.replaceChildren(...items.map((t) => Object.assign(document.createElement("li"), { textContent: t })));
  if (emptyId) document.getElementById(emptyId).hidden = items.length > 0;
}
const pct = (v) => (v === null || v === undefined ? "–" : `${Math.round(v * 100)}%`);

function showResult(r) {
  document.getElementById("score").textContent = r.score;
  document.getElementById("ring").setAttribute("aria-label", `Match score ${r.score} out of 100`);
  const circumference = 2 * Math.PI * 52;
  document.getElementById("ring-value").style.strokeDashoffset = String(circumference * (1 - r.score / 100));
  document.getElementById("verdict").textContent = r.verdict;
  document.getElementById("coverage").textContent = pct(r.skill_coverage);
  document.getElementById("similarity").textContent = pct(Math.min(1, r.similarity / 0.35));
  fillList("missing-skills", r.missing_skills, "missing-none");
  fillList("matched-skills", r.matched_skills, "matched-none");
  fillList("missing-keywords", r.missing_keywords);
  fillList("suggestions", r.suggestions);
  results.hidden = false;
  results.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
}

// ----- submit -----
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorBox.textContent = "";

  const data = new FormData();
  if (mode === "upload") {
    if (!fileInput.files[0]) { errorBox.textContent = "Choose your resume PDF, or switch to Paste text."; return; }
    data.append("resume_file", fileInput.files[0]);
  } else {
    if (resumeText.value.trim().length < 100) { errorBox.textContent = "Paste your resume text, at least a few lines."; resumeText.focus(); return; }
    data.append("resume_text", resumeText.value);
  }
  if (jobText.value.trim().length < 80) { errorBox.textContent = "Paste the full job description, at least a few sentences."; jobText.focus(); return; }
  data.append("job_description", jobText.value);

  button.disabled = true;
  button.textContent = "Scoring…";
  try {
    const res = await fetch("/api/score", { method: "POST", body: data });
    const body = await res.json();
    if (!res.ok) { errorBox.textContent = body.error || "Something went wrong. Try again."; return; }
    showResult(body);
  } catch (err) {
    errorBox.textContent = "The server couldn't be reached. Check your connection and try again.";
  } finally {
    button.disabled = false;
    button.textContent = "Score my resume";
  }
});
