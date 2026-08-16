"use strict";

const app = {
  rows: [],
  taskStates: [],
  catalog: null,
  progress: null,
  currentIndex: 0,
  dirty: false,
  filteredIndices: [],
};

const statusLabels = {
  unreviewed: "未审查",
  in_progress: "进行中",
  accepted: "已接受",
  reviewed_rejected: "已拒绝",
};

const $ = (selector) => document.querySelector(selector);

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function todayLocal() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
}

function markDirty() {
  app.dirty = true;
  $("#save-state").textContent = "未保存";
}

function splitLines(value) {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function normalizeReview(binding) {
  const review = binding.review || {};
  review.decision = review.decision || "PENDING";
  review.rationale = review.rationale || "";
  review.source_spans = Array.isArray(review.source_spans) ? review.source_spans : [];
  review.canonical_transform = review.canonical_transform || "";
  review.resolver = review.resolver && typeof review.resolver === "object" ? review.resolver : {};
  binding.review = review;
  return review;
}

function progressComplete(progress) {
  const counts = progress.status_counts || {};
  return (counts.accepted || 0) + (counts.reviewed_rejected || 0);
}

function updateProgress(progress) {
  app.progress = progress;
  const complete = progressComplete(progress);
  $("#task-progress").textContent = `${complete} / ${progress.task_count}`;
  $("#progress-bar").style.width = `${progress.task_count ? 100 * complete / progress.task_count : 0}%`;
  $("#download-output").classList.toggle("disabled", !progress.reviewed_packet_exists);
}

function taskDisplayTitle(row) {
  return row.candidate_task_goal || row.original_task || `${row.suite}/${row.user_task_id}`;
}

function renderTaskList() {
  const search = $("#task-search").value.trim().toLowerCase();
  const suite = $("#suite-filter").value;
  const status = $("#status-filter").value;
  const list = $("#task-list");
  list.replaceChildren();
  app.filteredIndices = [];

  app.rows.forEach((row, index) => {
    const state = app.taskStates[index];
    const haystack = `${row.suite} ${row.user_task_id} ${row.original_task} ${row.candidate_task_goal || ""}`.toLowerCase();
    if (suite !== "all" && row.suite !== suite) return;
    if (status !== "all" && state.status !== status) return;
    if (search && !haystack.includes(search)) return;
    app.filteredIndices.push(index);

    const button = element("button", `task-item${index === app.currentIndex ? " active" : ""}`);
    button.type = "button";
    button.dataset.index = String(index);
    button.setAttribute("aria-current", index === app.currentIndex ? "true" : "false");
    button.addEventListener("click", () => navigateTo(index));

    button.append(element("span", `status-dot ${state.status}`));
    const copy = element("span", "task-item-copy");
    copy.append(element("span", "task-item-title", taskDisplayTitle(row)));
    copy.append(element("span", "task-item-subtitle", `${row.suite} · ${row.user_task_id}`));
    button.append(copy);
    button.append(element("span", "task-item-count", `${state.decided_bindings}/${state.binding_count}`));
    list.append(button);
  });

  if (!app.filteredIndices.length) {
    list.append(element("div", "empty-state", "没有符合筛选条件的任务。"));
  }
}

function fact(label, content, full = false) {
  const wrapper = element("div", `fact${full ? " full" : ""}`);
  wrapper.append(element("span", "fact-label", label));
  if (content instanceof Node) wrapper.append(content);
  else wrapper.append(element("p", "", content || "未提供"));
  return wrapper;
}

function bindingClientErrors(binding) {
  const review = normalizeReview(binding);
  const errors = [];
  if (!["APPROVE", "REJECT"].includes(review.decision)) errors.push("请选择批准或拒绝");
  if (!review.rationale.trim()) errors.push("必须填写判断理由");
  if (review.decision !== "APPROVE") return errors;

  if (binding.mode === "exact") {
    if (!review.source_spans.length && !review.canonical_transform.trim()) {
      errors.push("批准 exact 字段需要原任务文本片段或规范化转换说明");
    }
  } else if (binding.mode === "resolve") {
    const resolver = review.resolver || {};
    if (!resolver.read_tool) errors.push("必须选择只读解析工具");
    const query = resolver.query_constraint || {};
    const args = query.arguments || {};
    const tool = (((app.catalog || {}).suites || {})[app.rows[app.currentIndex].suite] || {})[resolver.read_tool];
    if (tool) {
      for (const fieldName of tool.required_parameter_fields || []) {
        if (!args[fieldName]) errors.push(`解析查询缺少必填字段 ${fieldName}`);
      }
    }
    Object.entries(args).forEach(([name, constraint]) => {
      if (constraint.mode === "exact" && (!Array.isArray(constraint.values) || !constraint.values.length)) {
        errors.push(`查询字段 ${name} 的 exact 值不能为空`);
      }
    });
    const projection = resolver.output_projection || {};
    if (!app.catalog.projection_kinds.includes(projection.kind)) errors.push("必须选择输出投影类型");
    if (["record_field", "record_list_field"].includes(projection.kind) && !String(projection.field || "").trim()) {
      errors.push("记录投影必须填写字段名");
    }
    if (!Number.isInteger(resolver.max_cardinality) || resolver.max_cardinality < 1 || resolver.max_cardinality > 100) {
      errors.push("最大返回数量必须为 1–100 的整数");
    }
  }
  return errors;
}

function allBindingsApprovedAndValid(row) {
  return row.candidate_bindings.every((binding) => {
    const review = normalizeReview(binding);
    return review.decision === "APPROVE" && bindingClientErrors(binding).length === 0;
  });
}

function refreshTaskAcceptance() {
  const row = app.rows[app.currentIndex];
  const acceptRadio = document.querySelector('input[name="task-accepted"][value="true"]');
  const canAccept = allBindingsApprovedAndValid(row);
  acceptRadio.disabled = !canAccept;
  if (!canAccept && acceptRadio.checked) {
    acceptRadio.checked = false;
    row.human_review.accepted = false;
    markDirty();
  }
}

function renderExactFields(binding, container) {
  const review = normalizeReview(binding);
  const grid = element("div", "mode-fields-grid");
  const spansLabel = element("label", "field-label");
  spansLabel.append(element("span", "", "原任务中的依据文本（每行一项）"));
  const spans = document.createElement("textarea");
  spans.rows = 3;
  spans.value = review.source_spans.join("\n");
  spans.placeholder = "粘贴原始任务中的原文片段";
  spans.addEventListener("input", () => {
    review.source_spans = splitLines(spans.value);
    markDirty();
    refreshBindingError(binding, container.closest(".binding-card"));
    refreshTaskAcceptance();
  });
  spansLabel.append(spans);
  grid.append(spansLabel);

  const transformLabel = element("label", "field-label");
  transformLabel.append(element("span", "", "规范化转换（可选）"));
  const transform = document.createElement("input");
  transform.type = "text";
  transform.value = review.canonical_transform;
  transform.placeholder = "例如 ISO_DATE、LOWERCASE_EMAIL；不可引入新权限";
  transform.addEventListener("input", () => {
    review.canonical_transform = transform.value;
    markDirty();
    refreshBindingError(binding, container.closest(".binding-card"));
    refreshTaskAcceptance();
  });
  transformLabel.append(transform);
  grid.append(transformLabel);
  container.append(grid);
  container.append(element("p", "form-hint", "至少填写一段原任务依据，或说明仅做不扩权的规范化转换。"));
}

function eligibleReadTools(suite) {
  const tools = (app.catalog.suites || {})[suite] || {};
  return Object.entries(tools)
    .filter(([, spec]) => spec.eligible_as_authorized_read === true)
    .sort(([left], [right]) => left.localeCompare(right));
}

function defaultResolver() {
  return {
    read_tool: "",
    query_constraint: { arguments: {}, allow_additional_arguments: false },
    output_projection: { kind: "", field: "" },
    max_cardinality: 1,
  };
}

function ensureResolver(review) {
  // Preserve object identity: select/input listeners retain this object while
  // client validation runs. Replacing it would make subsequent edits update a
  // stale resolver and appear to reset after the form redraws.
  if (!review.resolver || typeof review.resolver !== "object") review.resolver = defaultResolver();
  const resolver = review.resolver;
  if (typeof resolver.read_tool !== "string") resolver.read_tool = "";
  if (!resolver.query_constraint || typeof resolver.query_constraint !== "object") {
    resolver.query_constraint = { arguments: {}, allow_additional_arguments: false };
  }
  if (!resolver.query_constraint.arguments || typeof resolver.query_constraint.arguments !== "object") {
    resolver.query_constraint.arguments = {};
  }
  resolver.query_constraint.allow_additional_arguments = false;
  if (!resolver.output_projection || typeof resolver.output_projection !== "object") {
    resolver.output_projection = { kind: "", field: "" };
  }
  if (typeof resolver.output_projection.kind !== "string") resolver.output_projection.kind = "";
  if (typeof resolver.output_projection.field !== "string") resolver.output_projection.field = "";
  if (!Number.isInteger(resolver.max_cardinality)) resolver.max_cardinality = 1;
  return resolver;
}

function resetResolverForTool(resolver, toolName, suite) {
  resolver.read_tool = toolName;
  resolver.query_constraint = { arguments: {}, allow_additional_arguments: false };
  const tool = ((app.catalog.suites || {})[suite] || {})[toolName];
  if (tool) {
    for (const fieldName of tool.required_parameter_fields || []) {
      resolver.query_constraint.arguments[fieldName] = { mode: "exact", values: [] };
    }
  }
}

function renderQueryRows(binding, host, rerender) {
  const row = app.rows[app.currentIndex];
  const review = normalizeReview(binding);
  const resolver = ensureResolver(review);
  const tool = ((app.catalog.suites || {})[row.suite] || {})[resolver.read_tool];
  if (!tool) return;
  const queryFields = element("div", "query-fields");
  const args = resolver.query_constraint.arguments;
  const required = new Set(tool.required_parameter_fields || []);

  for (const fieldName of tool.parameter_fields || []) {
    const queryRow = element("div", "query-row");
    const include = document.createElement("input");
    include.type = "checkbox";
    include.checked = Boolean(args[fieldName]);
    include.disabled = required.has(fieldName);
    if (required.has(fieldName) && !args[fieldName]) args[fieldName] = { mode: "exact", values: [] };
    include.addEventListener("change", () => {
      if (include.checked) args[fieldName] = { mode: "exact", values: [] };
      else delete args[fieldName];
      markDirty();
      rerender();
    });
    queryRow.append(include);

    const nameWrap = element("div", "");
    nameWrap.append(element("span", "query-name", fieldName));
    if (required.has(fieldName)) nameWrap.append(element("span", "required-label", " 必填"));
    queryRow.append(nameWrap);

    const mode = document.createElement("select");
    ["exact", "forbidden"].forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value === "exact" ? "固定值" : "禁止传入";
      mode.append(option);
    });
    mode.disabled = !args[fieldName];
    mode.value = args[fieldName]?.mode || "exact";
    mode.addEventListener("change", () => {
      args[fieldName] = mode.value === "exact" ? { mode: "exact", values: [] } : { mode: "forbidden" };
      markDirty();
      rerender();
    });
    queryRow.append(mode);

    if (args[fieldName]?.mode === "exact") {
      const values = document.createElement("textarea");
      values.rows = 2;
      values.placeholder = "每行一个允许值";
      values.value = (args[fieldName].values || []).join("\n");
      values.addEventListener("input", () => {
        args[fieldName].values = splitLines(values.value);
        markDirty();
        refreshBindingError(binding, host.closest(".binding-card"));
        refreshTaskAcceptance();
      });
      queryRow.append(values);
    } else {
      queryRow.append(element("span", "form-hint", args[fieldName] ? "该查询参数不得出现" : "未加入查询"));
    }
    queryFields.append(queryRow);
  }
  host.append(queryFields);
}

function renderResolveFields(binding, container) {
  const row = app.rows[app.currentIndex];
  const review = normalizeReview(binding);
  const resolver = ensureResolver(review);
  const rerender = () => {
    container.replaceChildren();
    renderResolveFields(binding, container);
    refreshBindingError(binding, container.closest(".binding-card"));
    refreshTaskAcceptance();
  };

  const grid = element("div", "resolver-grid");
  const toolLabel = element("label", "field-label");
  toolLabel.append(element("span", "", "只读解析工具"));
  const toolSelect = document.createElement("select");
  const blank = document.createElement("option");
  blank.value = "";
  blank.textContent = "请选择冻结目录中的只读工具";
  toolSelect.append(blank);
  eligibleReadTools(row.suite).forEach(([toolName]) => {
    const option = document.createElement("option");
    option.value = toolName;
    option.textContent = toolName;
    toolSelect.append(option);
  });
  toolSelect.value = resolver.read_tool;
  toolSelect.addEventListener("change", () => {
    resetResolverForTool(resolver, toolSelect.value, row.suite);
    markDirty();
    rerender();
  });
  toolLabel.append(toolSelect);
  grid.append(toolLabel);

  const projectionLabel = element("label", "field-label");
  projectionLabel.append(element("span", "", "输出投影"));
  const projectionSelect = document.createElement("select");
  const projectionBlank = document.createElement("option");
  projectionBlank.value = "";
  projectionBlank.textContent = "选择类型";
  projectionSelect.append(projectionBlank);
  app.catalog.projection_kinds.forEach((kind) => {
    const option = document.createElement("option");
    option.value = kind;
    option.textContent = kind;
    projectionSelect.append(option);
  });
  projectionSelect.value = resolver.output_projection.kind;
  projectionSelect.addEventListener("change", () => {
    resolver.output_projection.kind = projectionSelect.value;
    if (!["record_field", "record_list_field"].includes(projectionSelect.value)) resolver.output_projection.field = "";
    markDirty();
    rerender();
  });
  projectionLabel.append(projectionSelect);
  grid.append(projectionLabel);

  const cardinalityLabel = element("label", "field-label");
  cardinalityLabel.append(element("span", "", "最大返回数量"));
  const cardinality = document.createElement("input");
  cardinality.type = "number";
  cardinality.min = "1";
  cardinality.max = "100";
  cardinality.value = String(resolver.max_cardinality || 1);
  cardinality.addEventListener("input", () => {
    resolver.max_cardinality = Number(cardinality.value);
    markDirty();
    refreshBindingError(binding, container.closest(".binding-card"));
    refreshTaskAcceptance();
  });
  cardinalityLabel.append(cardinality);
  grid.append(cardinalityLabel);
  container.append(grid);

  if (["record_field", "record_list_field"].includes(resolver.output_projection.kind)) {
    const fieldLabel = element("label", "field-label");
    fieldLabel.style.marginTop = "12px";
    fieldLabel.append(element("span", "", "投影字段名"));
    const projectionField = document.createElement("input");
    projectionField.type = "text";
    projectionField.value = resolver.output_projection.field || "";
    projectionField.placeholder = "只返回该记录字段";
    projectionField.addEventListener("input", () => {
      resolver.output_projection.field = projectionField.value;
      markDirty();
      refreshBindingError(binding, container.closest(".binding-card"));
      refreshTaskAcceptance();
    });
    fieldLabel.append(projectionField);
    container.append(fieldLabel);
  }

  renderQueryRows(binding, container, rerender);
  container.append(element("p", "form-hint", "查询只允许显式参数；附加参数始终关闭。解析工具不能产生副作用或访问外部网页。"));
}

function refreshBindingError(binding, card) {
  if (!card) return;
  const target = card.querySelector(".binding-error");
  const errors = bindingClientErrors(binding);
  target.textContent = errors.join("；");
  target.hidden = errors.length === 0;
  card.classList.toggle("approved", binding.review.decision === "APPROVE");
  card.classList.toggle("rejected", binding.review.decision === "REJECT");
}

function renderBinding(binding, index) {
  const review = normalizeReview(binding);
  const card = element("article", "binding-card");
  const header = element("div", "binding-header");
  const identity = element("div", "binding-identity");
  identity.append(element("span", "binding-index", `字段 ${index + 1}`));
  identity.append(element("span", "code-label", binding.tool_name));
  identity.append(element("span", "code-label", binding.field));
  header.append(identity);
  header.append(element("span", "mode-label", binding.mode));
  card.append(header);

  const body = element("div", "binding-body");
  const facts = element("div", "binding-facts");
  facts.append(fact("候选意图", binding.proposed_intent, true));
  if ((binding.proposed_values || []).length) {
    const values = element("div", "value-list");
    binding.proposed_values.forEach((value) => values.append(element("span", "value-chip", String(value))));
    facts.append(fact("候选值", values));
  }
  if (binding.candidate_resolver_id) facts.append(fact("候选 resolver ID", binding.candidate_resolver_id));
  body.append(facts);

  const decision = element("div", "decision-row");
  const segmented = element("div", "segmented");
  [
    ["APPROVE", "批准", "approve"],
    ["REJECT", "拒绝", "reject"],
  ].forEach(([value, labelText, className]) => {
    const label = element("label", className);
    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = `binding-decision-${index}`;
    radio.value = value;
    radio.checked = review.decision === value;
    radio.addEventListener("change", () => {
      review.decision = value;
      markDirty();
      const modeFields = card.querySelector(".mode-fields");
      modeFields.hidden = value !== "APPROVE" || binding.mode === "forbidden";
      refreshBindingError(binding, card);
      refreshTaskAcceptance();
    });
    label.append(radio, element("span", "", labelText));
    segmented.append(label);
  });
  decision.append(segmented);

  const rationaleLabel = element("label", "field-label");
  rationaleLabel.append(element("span", "", "判断理由"));
  const rationale = document.createElement("textarea");
  rationale.rows = 3;
  rationale.value = review.rationale;
  rationale.placeholder = "说明该字段为何被原始任务授权，或为何必须拒绝";
  rationale.addEventListener("input", () => {
    review.rationale = rationale.value;
    markDirty();
    refreshBindingError(binding, card);
    refreshTaskAcceptance();
  });
  rationaleLabel.append(rationale);
  decision.append(rationaleLabel);
  body.append(decision);

  const modeFields = element("div", "mode-fields");
  modeFields.hidden = review.decision !== "APPROVE" || binding.mode === "forbidden";
  if (binding.mode === "exact") renderExactFields(binding, modeFields);
  if (binding.mode === "resolve") renderResolveFields(binding, modeFields);
  body.append(modeFields);

  const error = element("div", "binding-error");
  error.hidden = true;
  body.append(error);
  card.append(body);
  refreshBindingError(binding, card);
  return card;
}

function setStatusPill(state) {
  const pill = $("#task-status");
  pill.className = `status-pill ${state.status}`;
  pill.textContent = statusLabels[state.status];
}

function renderTask() {
  const row = app.rows[app.currentIndex];
  const state = app.taskStates[app.currentIndex];
  if (!row) return;
  window.history.replaceState(null, "", `#${row.suite}/${row.user_task_id}`);
  $("#loading").hidden = true;
  $("#task-view").hidden = false;
  $("#task-kicker").textContent = `${row.suite} / ${row.user_task_id}`;
  $("#task-title").textContent = taskDisplayTitle(row);
  $("#original-task").textContent = row.original_task;
  $("#candidate-goal").textContent = row.candidate_task_goal || "没有可用的候选任务目标。";
  setStatusPill(state);

  const warning = $("#plan-warning");
  warning.hidden = row.pre_output_plan_available;
  warning.textContent = row.pre_output_plan_available ? "" : "该任务没有预输出计划。请确认空权限清单是否应被接受；不要自行补充模板外的权限。";

  $("#binding-count").textContent = `${row.candidate_bindings.length} 个字段；${state.decided_bindings} 个已有决定`;
  const list = $("#binding-list");
  list.replaceChildren();
  row.candidate_bindings.forEach((binding, index) => list.append(renderBinding(binding, index)));
  $("#empty-bindings").hidden = row.candidate_bindings.length !== 0;

  const human = row.human_review;
  $("#original-only-confirmed").checked = human.original_task_only_confirmed === true;
  $("#task-notes").value = human.notes || "";
  document.querySelectorAll('input[name="task-accepted"]').forEach((radio) => { radio.checked = false; });
  if (state.status === "accepted") document.querySelector('input[name="task-accepted"][value="true"]').checked = true;
  if (state.status === "reviewed_rejected") document.querySelector('input[name="task-accepted"][value="false"]').checked = true;
  refreshTaskAcceptance();

  $("#previous-task").disabled = app.currentIndex === 0;
  $("#next-task").disabled = app.currentIndex === app.rows.length - 1;
  $("#save-state").textContent = "";
  app.dirty = false;
  renderTaskList();
  window.requestAnimationFrame(() => $("#review-main").scrollTo({ top: 0, behavior: "instant" }));
}

function navigateTo(index) {
  if (index === app.currentIndex) return;
  if (app.dirty && !window.confirm("当前任务有未保存修改。确定离开吗？")) return;
  app.currentIndex = index;
  renderTask();
}

function taskClientErrors(row) {
  const human = row.human_review;
  const errors = [];
  if (!String(human.reviewer_anonymous_id || "").trim()) errors.push("缺少匿名审查者 ID");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(human.review_date || "")) errors.push("缺少有效审查日期");
  if (!human.original_task_only_confirmed) errors.push("必须确认只使用原始任务作为审查依据");
  row.candidate_bindings.forEach((binding, index) => {
    bindingClientErrors(binding).forEach((message) => errors.push(`字段 ${index + 1}：${message}`));
  });
  if (human.accepted && !allBindingsApprovedAndValid(row)) errors.push("存在未批准或填写不完整的字段，任务不能接受");
  return errors;
}

function syncTaskControls() {
  const row = app.rows[app.currentIndex];
  row.human_review.reviewer_anonymous_id = $("#global-reviewer-id").value.trim();
  row.human_review.review_date = $("#global-review-date").value;
  row.human_review.original_task_only_confirmed = $("#original-only-confirmed").checked;
  row.human_review.notes = $("#task-notes").value;
  const selected = document.querySelector('input[name="task-accepted"]:checked');
  row.human_review.accepted = selected ? selected.value === "true" : false;
}

async function saveCurrent(moveNext = false) {
  syncTaskControls();
  const row = app.rows[app.currentIndex];
  const errors = taskClientErrors(row);
  const errorBox = $("#task-errors");
  errorBox.hidden = errors.length === 0;
  errorBox.textContent = errors.length ? `当前仍可保存为草稿，但尚不能通过完整验证：${errors.join("；")}` : "";
  $("#save-state").textContent = "保存中...";
  $("#save-task").disabled = true;
  $("#save-next").disabled = true;
  try {
    const response = await fetch("/api/save-task", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        suite: row.suite,
        task_id: row.user_task_id,
        binding_reviews: row.candidate_bindings.map((binding) => binding.review),
        human_review: row.human_review,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "保存失败");
    app.rows[app.currentIndex] = payload.row;
    app.taskStates[app.currentIndex] = payload.task_state;
    updateProgress(payload.progress);
    app.dirty = false;
    $("#save-state").textContent = errors.length ? "草稿已保存" : "已保存";
    showToast(errors.length ? "已保存草稿；仍有必填项" : "当前任务已保存");
    renderTaskList();
    setStatusPill(payload.task_state);
    if (moveNext && app.currentIndex < app.rows.length - 1) {
      app.currentIndex += 1;
      renderTask();
    }
  } catch (error) {
    $("#save-state").textContent = "保存失败";
    showToast(error.message);
  } finally {
    $("#save-task").disabled = false;
    $("#save-next").disabled = false;
  }
}

function renderValidation(summary) {
  const host = $("#validation-summary");
  host.replaceChildren();
  const passed = summary.status === "passed";
  host.append(element("p", passed ? "validation-pass" : "validation-fail", passed ? "验证通过：97 个任务均已编译。" : `尚未通过：${summary.n_errors || 0} 个问题。`));
  host.append(element("p", "", `状态：${summary.status}`));
  if (summary.compiled_trusted_manifests !== undefined) {
    host.append(element("p", "", `已编译可信清单：${summary.compiled_trusted_manifests} / ${summary.template_rows}`));
  }
  if ((summary.errors || []).length) {
    const list = element("ol", "validation-errors");
    summary.errors.forEach((message) => list.append(element("li", "", message)));
    host.append(list);
  }
}

async function validateAll() {
  const dialog = $("#validation-dialog");
  renderValidation({ status: "running", n_errors: 0, errors: [] });
  dialog.showModal();
  try {
    const response = await fetch("/api/validate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "验证请求失败");
    renderValidation(payload);
  } catch (error) {
    renderValidation({ status: "request_failed", n_errors: 1, errors: [error.message] });
  }
}

function attachStaticEvents() {
  ["#task-search", "#suite-filter", "#status-filter"].forEach((selector) => {
    $(selector).addEventListener(selector === "#task-search" ? "input" : "change", renderTaskList);
  });
  $("#global-reviewer-id").addEventListener("input", (event) => {
    localStorage.setItem("e84-reviewer-id", event.target.value);
    markDirty();
  });
  $("#global-review-date").addEventListener("change", (event) => {
    localStorage.setItem("e84-review-date", event.target.value);
    markDirty();
  });
  $("#original-only-confirmed").addEventListener("change", markDirty);
  $("#task-notes").addEventListener("input", markDirty);
  document.querySelectorAll('input[name="task-accepted"]').forEach((radio) => {
    radio.addEventListener("change", markDirty);
  });
  $("#save-task").addEventListener("click", () => saveCurrent(false));
  $("#save-next").addEventListener("click", () => saveCurrent(true));
  $("#previous-task").addEventListener("click", () => navigateTo(app.currentIndex - 1));
  $("#next-task").addEventListener("click", () => navigateTo(app.currentIndex + 1));
  $("#validate-all").addEventListener("click", validateAll);
  $("#close-validation").addEventListener("click", () => $("#validation-dialog").close());
  window.addEventListener("beforeunload", (event) => {
    if (!app.dirty) return;
    event.preventDefault();
    event.returnValue = "";
  });
}

async function initialize() {
  attachStaticEvents();
  $("#global-reviewer-id").value = localStorage.getItem("e84-reviewer-id") || "";
  $("#global-review-date").value = localStorage.getItem("e84-review-date") || todayLocal();
  try {
    const response = await fetch("/api/bootstrap", { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "无法载入审查包");
    app.rows = payload.rows;
    app.taskStates = payload.task_states;
    app.catalog = payload.resolver_catalog;
    updateProgress(payload.progress);
    const requestedKey = window.location.hash.slice(1);
    const requestedIndex = app.rows.findIndex((row) => `${row.suite}/${row.user_task_id}` === requestedKey);
    const firstIncomplete = app.taskStates.findIndex((state) => !["accepted", "reviewed_rejected"].includes(state.status));
    app.currentIndex = requestedIndex >= 0 ? requestedIndex : (firstIncomplete >= 0 ? firstIncomplete : 0);
    renderTask();
  } catch (error) {
    $("#loading").textContent = `载入失败：${error.message}`;
  }
}

initialize();
