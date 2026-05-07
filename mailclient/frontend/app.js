const state = {
  socket: null,
  connection: null,
  config: null,
  selectedEmailUid: null,
};

const LANGUAGE_OPTIONS = [
  { code: "EN", label: "English" }, { code: "ES", label: "Spanish" },
  { code: "FR", label: "French" }, { code: "DE", label: "German" },
  { code: "IT", label: "Italian" }, { code: "PT", label: "Portuguese" },
];

const COUNTRY_OPTIONS = [
  { code: "MX", label: "Mexico" }, { code: "US", label: "United States" },
  { code: "CA", label: "Canada" }, { code: "ES", label: "Spain" },
  { code: "FR", label: "France" }, { code: "DE", label: "Germany" },
];

const appView = document.getElementById("app-view");
const configStatus = document.getElementById("config-status");
const emailTableBody = document.getElementById("email-table-body");
const mailboxLabel = document.getElementById("mailbox-label");
const refreshButton = document.getElementById("refresh-button");
const emailDetailPanel = document.getElementById("email-detail-panel");
const emailDetailStatus = document.getElementById("email-detail-status");
const debugStatus = document.getElementById("debug-status");
const markSpamButton = document.getElementById("mark-spam-button");
const markHamButton = document.getElementById("mark-ham-button");
const clearDatabaseButton = document.getElementById("clear-database-button");

const analyzeAiButton = document.getElementById("analyze-ai-button");
const aiResultPanel = document.getElementById("ai-result-panel");
const aiProbabilityRing = document.getElementById("ai-probability-ring");
const aiReasoning = document.getElementById("ai-reasoning");

initialize();

function initialize() {
  populateSelectOptions("allowed-languages", LANGUAGE_OPTIONS);
  populateSelectOptions("allowed-countries", COUNTRY_OPTIONS);
  connectSocket();
  bindEvents();
}

function connectSocket() {
  sendCommand("connect", {});
}

function bindEvents() {
  refreshButton.addEventListener("click", () => {
    if (state.connection) {
      sendCommand("connect", { connection: state.connection });
    }
  });

  const configForm = document.getElementById("config-form");
  const clearDatabaseButton = document.getElementById("clear-database-button");

  if (configForm) {
    configForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const payload = {
        allowed_languages: Array.from(document.getElementById("allowed-languages").selectedOptions).map((o) => o.value),
        allowed_countries: Array.from(document.getElementById("allowed-countries").selectedOptions).map((o) => o.value),
        duplicate_subject_threshold: parseInt(document.getElementById("duplicate-threshold").value, 10),
        allow_links: document.getElementById("allow-links").checked,
        allow_undisclosed: document.getElementById("allow-undisclosed").checked,
      };
      sendCommand("save_config", payload);
    });
  }

  document.querySelectorAll("[data-section-target]").forEach((button) => {
    button.addEventListener("click", () => setActiveSection(button.dataset.sectionTarget));
  });

  // Manual marking buttons
  markSpamButton.addEventListener("click", () => {
    if (!state.selectedEmailUid) return;
    showAlert(emailDetailStatus, "Marking as SPAM...", "info");
    sendCommand("mark_mitl", { uid: state.selectedEmailUid, label: "SPAM" });
  });
  
  markHamButton.addEventListener("click", () => {
    if (!state.selectedEmailUid) return;
    showAlert(emailDetailStatus, "Marking as HAM...", "info");
    sendCommand("mark_mitl", { uid: state.selectedEmailUid, label: "HAM" });
  });

  const recalcButton = document.getElementById("recalculate-tech-score-button");
  if (recalcButton) {
    recalcButton.addEventListener("click", (e) => {
      e.stopPropagation();
      if (!state.selectedEmailUid) return;
      showAlert(emailDetailStatus, "Recalculating tech score...", "info");
      sendCommand("get_email_detail", { uid: state.selectedEmailUid });
    });
  }

  analyzeAiButton.addEventListener("click", () => {
    if (!state.selectedEmailUid) return;
    showAlert(emailDetailStatus, "Analyzing email with local AI...", "info");
    aiResultPanel.classList.add("d-none");
    sendCommand("analyze_ai", { uid: state.selectedEmailUid });
  });

  clearDatabaseButton.addEventListener("click", () => clearDatabaseWithConfirmation());
}

async function sendCommand(command, payload) {
  try {
    const response = await fetch(`${window.location.pathname.replace(/\/$/, '')}/api/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command, payload }),
    });
    const message = await response.json();
    processResponse(message);
  } catch (error) {
    console.error("Fetch error:", error);
  }
}

function processResponse(message) {
  if (message.event === "config_loaded") {
    state.config = message.config;
    populateForms(message.config);
    return;
  }

  if (message.event === "connect_result") {
    if (!message.success) {
      return;
    }
    state.config = message.config;
    state.connection = message.config.connection;
    populateForms(message.config);
    renderEmails(message.emails || []);
    emailDetailPanel.classList.add("d-none");
    mailboxLabel.textContent = `Connected as: ${state.connection.username}`;
    
    // Load config and emails automatically
    sendCommand("get_config", {});
    return;
  }

  if (message.event === "config_saved") {
    if (!message.success) {
      showAlert(configStatus, message.error || "Could not save config.", "danger");
      return;
    }
    state.config = message.config;
    populateForms(message.config);
    showAlert(configStatus, "Configuration saved successfully.", "success");
    return;
  }

  if (message.event === "email_detail") {
    if (!message.success) {
      showAlert(emailDetailStatus, message.error || "Could not load email details.", "danger");
      return;
    }
    renderEmailDetail(message.email);
    showAlert(emailDetailStatus, "Email loaded.", "success");
    return;
  }

  if (message.event === "ai_analyzed") {
    if (!message.success) {
      showAlert(emailDetailStatus, message.error || "Could not analyze email.", "danger");
      return;
    }
    showAlert(emailDetailStatus, "AI Analysis complete and saved.", "success");
    renderAiResult(message);
    // Update AI badge in list if it exists
    const row = document.querySelector(`.email-row[data-email-uid="${state.selectedEmailUid}"]`);
    if (row) {
        const badge = row.querySelector('.badge-score-ai');
        if (badge) {
            const prob = message.spam_probability;
            badge.textContent = prob;
            badge.className = `badge badge-score-ai ${prob > 75 ? 'bg-danger' : prob > 35 ? 'bg-warning text-dark' : 'bg-success'}`;
        }
    }
    return;
  }

  if (message.event === "mitl_marked") {
    if (!message.success) {
      showAlert(emailDetailStatus, message.error || "Could not save tag.", "danger");
      return;
    }
    const tag = message.mitl_tag;
    showAlert(emailDetailStatus, `Email successfully tagged as ${tag} and saved to database.`, "success");
    // Update MITL badge in list if it exists
    const row = document.querySelector(`.email-row[data-email-uid="${state.selectedEmailUid}"]`);
    if (row) {
        const badge = row.querySelector('.badge-score-mitl');
        if (badge) {
            badge.textContent = tag;
            badge.className = `badge badge-score-mitl ${tag === 'SPAM' ? 'bg-danger' : 'bg-success'}`;
        }
    }
    return;
  }

  if (message.event === "database_cleared") {
    if (!message.success) {
      showAlert(debugStatus, message.error || "Could not clear database.", "danger");
      return;
    }
    document.getElementById("clear-database-confirmation").value = "";
    showAlert(debugStatus, "Local mail database cleared successfully.", "success");
    return;
  }

  if (!message.success && message.error) {
    console.error("Server Error:", message.error);
  }
}

function populateForms(config) {
  // Only config form remains
  const allowedLangs = document.getElementById("allowed-languages");
  if (allowedLangs && config.preferences?.allowed_languages) {
    Array.from(allowedLangs.options).forEach((opt) => {
      opt.selected = config.preferences.allowed_languages.includes(opt.value);
    });
  }

  const allowedCountries = document.getElementById("allowed-countries");
  if (allowedCountries && config.preferences?.allowed_countries) {
    Array.from(allowedCountries.options).forEach((opt) => {
      opt.selected = config.preferences.allowed_countries.includes(opt.value);
    });
  }

  const dupThreshold = document.getElementById("duplicate-threshold");
  if (dupThreshold && config.preferences?.duplicate_subject_threshold) {
    dupThreshold.value = config.preferences.duplicate_subject_threshold;
  }

  const allowLinks = document.getElementById("allow-links");
  if (allowLinks && config.preferences?.allow_links !== undefined) {
    allowLinks.checked = config.preferences.allow_links;
  }

  const allowUndisclosed = document.getElementById("allow-undisclosed");
  if (allowUndisclosed && config.preferences?.allow_undisclosed !== undefined) {
    allowUndisclosed.checked = config.preferences.allow_undisclosed;
  }
}

function populateSelectOptions(elementId, options) {
  const select = document.getElementById(elementId);
  select.innerHTML = options
    .map((option) => `<option value="${option.code}">${option.label} (${option.code})</option>`)
    .join("");
}

function setMultiSelectValues(elementId, values) {
  const selectedValues = new Set(values || []);
  Array.from(document.getElementById(elementId).options).forEach((option) => {
    option.selected = selectedValues.has(option.value);
  });
}

function getMultiSelectValues(elementId) {
  return Array.from(document.getElementById(elementId).selectedOptions).map((option) => option.value);
}

function renderEmails(emails) {
  state.selectedEmailUid = null;

  if (!emails.length) {
    emailTableBody.innerHTML = `<tr><td colspan="4" class="text-center text-muted py-5">No emails found in the inbox.</td></tr>`;
    return;
  }

  emailTableBody.innerHTML = emails
    .map(
      (email) => {
        const ts = email.tech_score !== undefined && email.tech_score !== null ? email.tech_score : "?";
        const tsClass = ts === "?" ? "bg-secondary" : (ts >= 7 ? "bg-success" : (ts >= 4 ? "bg-warning text-dark" : "bg-danger"));
        
        const ais = email.ai_score !== undefined && email.ai_score !== null ? email.ai_score : "?";
        const aisClass = ais === "?" ? "bg-secondary" : (ais > 75 ? "bg-danger" : (ais > 35 ? "bg-warning text-dark" : "bg-success"));
        
        const mitl = email.mitl_tag || "?";
        const mitlClass = mitl === "?" ? "bg-secondary" : (mitl === "SPAM" ? "bg-danger" : "bg-success");
        
        return `
        <tr class="email-row" data-email-uid="${email.uid}">
          <td class="text-center"><span class="badge ${tsClass} badge-score-tech" id="table-score-tech-${email.uid}">${ts}</span></td>
          <td class="text-center"><span class="badge ${aisClass} badge-score-ai" id="table-score-ai-${email.uid}">${ais}</span></td>
          <td class="text-center"><span class="badge ${mitlClass} badge-score-mitl" id="table-score-mitl-${email.uid}">${mitl}</span></td>
          <td class="fw-semibold">${escapeHtml(email.subject)}</td>
          <td class="text-secondary">${escapeHtml(email.from)}</td>
          <td class="text-secondary small">${escapeHtml(email.date)}</td>
        </tr>
      `
      }
    )
    .join("");

  document.querySelectorAll(".email-row").forEach((row) => {
    row.addEventListener("click", () => selectEmail(row.dataset.emailUid, row));
  });
}

function selectEmail(uid, rowElement) {
  state.selectedEmailUid = Number(uid);
  document.querySelectorAll(".email-row").forEach((row) => {
    row.classList.toggle("table-active", row === rowElement);
  });

  emailDetailPanel.classList.remove("d-none");
  document.getElementById("hero-subject").textContent = "Loading email details...";
  document.getElementById("hero-score-badge").textContent = "...";
  document.getElementById("email-body-content").textContent = "Loading...";
  document.getElementById("email-headers-content").textContent = "";
  document.getElementById("score-details-list").innerHTML = '<li class="list-group-item text-muted">Loading...</li>';
  aiResultPanel.classList.add("d-none");
  
  showAlert(emailDetailStatus, "Fetching full body and details from the server...", "info");
  sendCommand("get_email_detail", { uid: state.selectedEmailUid });
}

function renderEmailDetail(email) {
  emailDetailPanel.classList.remove("d-none");
  
  const scoreData = email.header_score || { score: 0, details: [] };
  
  // Update Hero Section
  document.getElementById("hero-subject").textContent = email.subject || "(No subject)";
  document.getElementById("hero-score-badge").textContent = `${scoreData.score}/10`;
  
  // Update table badge for Tech Score
  const tableBadge = document.getElementById(`table-score-tech-${email.uid}`);
  if (tableBadge) {
    tableBadge.textContent = scoreData.score;
    tableBadge.className = `badge badge-score-tech ${scoreData.score >= 7 ? 'bg-success' : scoreData.score >= 4 ? 'bg-warning text-dark' : 'bg-danger'}`;
  }

  // Update Score Details Panel
  const detailsHtml = scoreData.details.map(d => `
    <li class="list-group-item d-flex justify-content-between align-items-start py-3">
      <div class="ms-2 me-auto">
        <div class="fw-bold">${d.rule}</div>
        <div class="small text-muted">${d.desc}</div>
      </div>
      <span class="badge ${d.points > 0 ? 'bg-success' : 'bg-danger'} rounded-pill">${d.points > 0 ? '+' : ''}${d.points}</span>
    </li>
  `).join("");
  document.getElementById("score-details-list").innerHTML = detailsHtml || '<li class="list-group-item">No security headers analyzed.</li>';

  // Update Body Panel
  document.getElementById("email-body-content").textContent = email.body?.preferred || "No body content available.";
  document.getElementById("detail-from").textContent = (email.from || []).join(", ") || "—";
  document.getElementById("detail-to").textContent = (email.to || []).join(", ") || "—";
  document.getElementById("detail-date").textContent = email.date || "—";
  document.getElementById("detail-content-type").textContent = email.content_type || "—";
  
  // Update Headers Panel
  document.getElementById("email-headers-content").textContent = (email.headers || [])
    .map((header) => `${header.name}: ${header.value}`)
    .join("\n");
    
  // Reset AI panel
  aiResultPanel.classList.add("d-none");
}

function renderAiResult(data) {
  aiResultPanel.classList.remove("d-none");
  const prob = data.spam_probability;
  aiProbabilityRing.textContent = `${prob}%`;
  
  if (prob > 75) {
    aiProbabilityRing.className = "ai-probability-ring bg-danger";
  } else if (prob > 35) {
    aiProbabilityRing.className = "ai-probability-ring bg-warning text-dark";
  } else {
    aiProbabilityRing.className = "ai-probability-ring bg-success";
  }
  
  document.getElementById("ai-reasoning").textContent = data.reason || "No reasoning provided by AI.";
}

function clearDatabaseWithConfirmation() {
  const typedConfirmation = document.getElementById("clear-database-confirmation").value.trim();
  if (!typedConfirmation) {
    showAlert(debugStatus, 'Type "yes" or "YES" first.', "warning");
    return;
  }
  showAlert(debugStatus, "Clearing database...", "info");
  sendCommand("clear_database", { confirmation: typedConfirmation });
}

function setActiveSection(sectionId) {
  document.querySelectorAll(".content-section").forEach((section) => {
    section.classList.toggle("d-none", section.id !== sectionId);
  });
  document.querySelectorAll("[data-section-target]").forEach((button) => {
    button.classList.toggle("active", button.dataset.sectionTarget === sectionId);
  });
}

function showAlert(target, message, style) {
  target.textContent = message;
  target.className = `alert alert-${style} shadow-sm`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
