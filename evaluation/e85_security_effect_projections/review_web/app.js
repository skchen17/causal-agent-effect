const state = { rows: [], states: [], selected: null, filter: "all", query: "" };
const roles = ["", "resource", "target_principal", "operation", "payload", "amount_or_quantity", "visibility", "commit_mode", "provenance", "control_source", "temporal", "credential", "compound_trigger", "other_security_relevant"];
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const byId = id => document.getElementById(id);

function toast(message) { const el = byId("toast"); el.textContent = message; el.style.display = "block"; setTimeout(() => el.style.display = "none", 3500); }
function toolState(row) { return state.states.find(x => x.tool_instance_key === row.tool_instance_key)?.status || "unreviewed"; }

function renderList() {
  const q = state.query.toLowerCase();
  const rows = state.rows.filter(row => {
    const status = toolState(row);
    return (state.filter === "all" || status === state.filter) && `${row.suite} ${row.tool_name}`.toLowerCase().includes(q);
  });
  byId("tool-list").innerHTML = rows.map(row => `<button class="tool-link" data-key="${esc(row.tool_instance_key)}" data-state="${toolState(row)}"><strong>${esc(row.tool_name)}</strong><small>${esc(row.suite)} · ${toolState(row)}</small></button>`).join("");
  document.querySelectorAll(".tool-link").forEach(button => button.onclick = () => { state.selected = button.dataset.key; renderReview(); });
}

function options(values, current) { return values.map(value => `<option value="${esc(value)}" ${value === current ? "selected" : ""}>${esc(value || "Select role")}</option>`).join(""); }

function renderReview() {
  const row = state.rows.find(x => x.tool_instance_key === state.selected);
  if (!row) return;
  const r = row.review;
  const fields = row.schema_fields.map((field, i) => {
    const review = r.field_reviews[i];
    return `<div class="review-row field-review" data-index="${i}"><div><strong>${esc(field.name)}</strong><br><small>${field.required ? "required" : `default=${esc(JSON.stringify(field.default))}`}<br>candidate: ${esc(field.candidate_security_role)}</small></div><select class="field-decision">${options(["PENDING","SECURITY_RELEVANT","NON_SECURITY","UNCERTAIN"], review.decision)}</select><select class="field-role">${options(roles, review.role)}</select><textarea class="field-rationale" placeholder="Implementation/state-grounded rationale">${esc(review.rationale)}</textarea></div>`;
  }).join("");
  const projections = row.candidate_effect_projections.map((p, i) => {
    const review = r.projection_reviews[i];
    return `<div class="projection projection-review" data-index="${i}"><h4>${esc(p.projection_id)} · ${esc(p.effect)}</h4><dl>${Object.entries(p).filter(([k]) => k !== "projection_id").map(([k,v]) => `<dt>${esc(k)}</dt><dd>${esc(Array.isArray(v) ? v.join(", ") : v)}</dd>`).join("")}</dl><div class="review-row"><div><strong>Projection decision</strong></div><select class="projection-decision">${options(["PENDING","APPROVE","REJECT","UNCERTAIN"], review.decision)}</select><div></div><textarea class="projection-rationale" placeholder="Cite implementation or state path">${esc(review.rationale)}</textarea></div></div>`;
  }).join("");
  const checks = [
    ["implementation_inspected","Implementation inspected"], ["state_mutation_paths_verified","State mutation paths verified"],
    ["defaults_reviewed","Defaults/omissions reviewed"], ["interactions_reviewed","Interactions reviewed"],
    ["expansions_reviewed","Resource/target expansion reviewed"], ["negative_controls_reviewed","Negative controls reviewed"],
    ["no_attack_outcomes_or_method_labels_used","No attack outcomes or method labels used"], ["no_missing_security_effects_confirmed","No missing security effects (required for APPROVE)"],
  ].map(([key,label]) => `<label><input type="checkbox" data-check="${key}" ${r[key] ? "checked" : ""}>${esc(label)}</label>`).join("");
  const evidence = row.candidate_field_counterfactual_evidence.map(e => `${e.field}: ${e.status}${e.base_error ? " · base error" : ""}${e.mutated_error ? " · mutation error" : ""}`).join("\n") || "No suite-specific field evidence row.";
  byId("review-pane").innerHTML = `<article class="review"><div class="review-head"><div><h2>${esc(row.tool_name)}</h2><p class="subtitle">${esc(row.suite)} · AgentDojo ${esc(row.agentdojo_benchmark_version)}</p></div><span class="status">${toolState(row)}</span></div><div class="panel"><h3>Tool evidence</h3><p>${esc(row.tool_description)}</p><p><strong>Source:</strong> ${esc(row.source_evidence.relative_path)}:${row.source_evidence.start_line} · function SHA-256 ${esc(row.source_evidence.function_source_sha256.slice(0,16))}...</p><details><summary>Controlled field evidence</summary><pre>${esc(evidence)}</pre></details><details><summary>Frozen implementation</summary><pre class="source">${esc(row.source_evidence.function_source)}</pre></details></div><div class="panel"><h3>Field classifications</h3>${fields}</div><div class="panel"><h3>Candidate effect projections</h3>${projections}</div><div class="panel"><h3>Independent review confirmations</h3><div class="check-grid">${checks}</div><div class="meta-grid" style="margin-top:12px"><label>Reviewer anonymous ID<input id="reviewer-id" value="${esc(r.reviewer_anonymous_id)}"></label><label>Review date<input id="review-date" type="date" value="${esc(r.review_date)}"></label></div><div class="meta-grid" style="margin-top:12px"><label>Overall decision<select id="overall-decision">${options(["PENDING","APPROVE","REJECT","UNCERTAIN"], r.overall_decision)}</select></label><label>Notes<textarea id="notes">${esc(r.notes)}</textarea></label></div><label>Overall rationale<textarea id="overall-rationale">${esc(r.rationale)}</textarea></label></div><div class="actions"><button id="validate">Validate packet</button><button id="save" class="primary">Save this review</button></div></article>`;
  byId("save").onclick = saveReview; byId("validate").onclick = validateAll;
}

function collectReview(row) {
  const review = structuredClone(row.review);
  review.reviewer_anonymous_id = byId("reviewer-id").value.trim(); review.review_date = byId("review-date").value;
  review.overall_decision = byId("overall-decision").value; review.rationale = byId("overall-rationale").value.trim(); review.notes = byId("notes").value.trim();
  document.querySelectorAll("[data-check]").forEach(el => review[el.dataset.check] = el.checked);
  document.querySelectorAll(".field-review").forEach(el => { const i = Number(el.dataset.index); review.field_reviews[i].decision = el.querySelector(".field-decision").value; review.field_reviews[i].role = el.querySelector(".field-role").value; review.field_reviews[i].rationale = el.querySelector(".field-rationale").value.trim(); });
  document.querySelectorAll(".projection-review").forEach(el => { const i = Number(el.dataset.index); review.projection_reviews[i].decision = el.querySelector(".projection-decision").value; review.projection_reviews[i].rationale = el.querySelector(".projection-rationale").value.trim(); });
  return review;
}

async function saveReview() {
  const row = state.rows.find(x => x.tool_instance_key === state.selected); const review = collectReview(row);
  const response = await fetch(`/api/review/${encodeURIComponent(row.suite)}/${encodeURIComponent(row.tool_name)}`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({review})});
  const data = await response.json(); if (!response.ok) return toast(data.error || "Save failed");
  Object.assign(row, data.row); state.states = data.states; renderProgress(data.progress); renderList(); renderReview(); toast("Review saved locally.");
}
async function validateAll() { const response = await fetch("/api/validate", {method:"POST"}); const data = await response.json(); toast(`${data.status}: ${data.n_errors || 0} validation errors`); }
function renderProgress(p) { byId("progress").textContent = `${p.completed}/${p.total} reviewed · ${p.approved} approved · ${p.rejected} rejected/uncertain`; }

async function boot() { const data = await (await fetch("/api/bootstrap")).json(); state.rows = data.rows; state.states = data.states; state.selected = data.rows[0]?.tool_instance_key || null; renderProgress(data.progress); renderList(); if (state.selected) renderReview(); }
byId("search").oninput = e => { state.query = e.target.value; renderList(); };
document.querySelectorAll("#filters button").forEach(button => button.onclick = () => { document.querySelectorAll("#filters button").forEach(x => x.classList.remove("active")); button.classList.add("active"); state.filter = button.dataset.filter; renderList(); });
boot().catch(error => toast(error.message));
