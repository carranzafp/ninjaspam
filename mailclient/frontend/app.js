const state = {
  socket: null,
  connection: null,
  config: null,
  selectedEmailUid: null,
};

const LANGUAGE_OPTIONS = [
  { code: "EN", label: "English" },
  { code: "ES", label: "Spanish" },
  { code: "FR", label: "French" },
  { code: "DE", label: "German" },
  { code: "IT", label: "Italian" },
  { code: "PT", label: "Portuguese" },
  { code: "NL", label: "Dutch" },
  { code: "RU", label: "Russian" },
  { code: "JA", label: "Japanese" },
  { code: "ZH", label: "Chinese" },
  { code: "KO", label: "Korean" },
  { code: "AR", label: "Arabic" },
  { code: "HI", label: "Hindi" },
];

const COUNTRY_OPTIONS = [
  { code: "MX", label: "Mexico" },
  { code: "US", label: "United States" },
  { code: "CA", label: "Canada" },
  { code: "ES", label: "Spain" },
  { code: "FR", label: "France" },
  { code: "DE", label: "Germany" },
  { code: "IT", label: "Italy" },
  { code: "GB", label: "United Kingdom" },
  { code: "BR", label: "Brazil" },
  { code: "AR", label: "Argentina" },
  { code: "CO", label: "Colombia" },
  { code: "CL", label: "Chile" },
  { code: "PE", label: "Peru" },
  { code: "JP", label: "Japan" },
  { code: "CN", label: "China" },
  { code: "IN", label: "India" },
  { code: "AU", label: "Australia" },
  { code: "NL", label: "Netherlands" },
  { code: "BE", label: "Belgium" },
  { code: "CH", label: "Switzerland" },
];

const connectView = document.getElementById("connect-view");
const appView = document.getElementById("app-view");
const connectForm = document.getElementById("connect-form");
const configForm = document.getElementById("config-form");
const connectStatus = document.getElementById("connect-status");
const configStatus = document.getElementById("config-status");
const emailTableBody = document.getElementById("email-table-body");
const mailboxLabel = document.getElementById("mailbox-label");
const refreshButton = document.getElementById("refresh-button");
const emailDetailPanel = document.getElementById("email-detail-panel");
const emailDetailStatus = document.getElementById("email-detail-status");
const debugStatus = document.getElementById("debug-status");
const markSpamButton = document.getElementById("mark-spam-button");
const markHamButton = document.getElementById("mark-ham-button");
const testEmailButton = document.getElementById("test-email-button");
const clearDatabaseButton = document.getElementById("clear-database-button");

initialize();

function initialize() {
  populateSelectOptions("allowed-languages", LANGUAGE_OPTIONS);
  populateSelectOptions("allowed-countries", COUNTRY_OPTIONS);
  connectSocket();
  bindEvents();
}

function connectSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  state.socket = new WebSocket(`${protocol}://${window.location.host}/ws`);

  state.socket.addEventListener("open", () => {
    sendCommand("get_config", {});
  });

  state.socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    processResponse(message);
  });

  state.socket.addEventListener("close", () => {
    showAlert(connectStatus, "Connection to server lost. Refresh the page.", "danger");
  });
}

function bindEvents() {
  connectForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const connection = readConnectionForm();
    state.connection = connection;
    showAlert(connectStatus, "Connecting to mailbox...", "info");
    sendCommand("connect", { connection });
  });

  refreshButton.addEventListener("click", () => {
    if (state.connection) {
      sendCommand("connect", { connection: state.connection });
    }
  });

  configForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const preferences = readConfigForm();
    sendCommand("save_config", { preferences });
  });

  document.querySelectorAll("[data-section-target]").forEach((button) => {
    button.addEventListener("click", () => setActiveSection(button.dataset.sectionTarget));
  });

  markSpamButton.addEventListener("click", () => classifySelectedEmail("SPAM"));
  markHamButton.addEventListener("click", () => classifySelectedEmail("HAM"));
  testEmailButton.addEventListener("click", () => testSelectedEmail());
  clearDatabaseButton.addEventListener("click", () => clearDatabaseWithConfirmation());

  document.querySelectorAll("[data-detail-tab]").forEach((button) => {
    button.addEventListener("click", () => setDetailTab(button.dataset.detailTab));
  });
}

function sendCommand(command, payload) {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    showAlert(connectStatus, "WebSocket is not connected yet.", "danger");
    return;
  }

  state.socket.send(JSON.stringify({ command, payload }));
}

function processResponse(message) {
  if (message.event === "config_loaded") {
    state.config = message.config;
    populateForms(message.config);
    return;
  }

  if (message.event === "connect_result") {
    if (!message.success) {
      showAlert(connectStatus, message.error || "Connection failed.", "danger");
      return;
    }

    state.config = message.config;
    state.connection = message.config.connection;
    populateForms(message.config);
    renderEmails(message.emails || []);
    resetEmailDetailPanel();
    mailboxLabel.textContent = message.config.connection.username;
    connectView.classList.add("d-none");
    appView.classList.remove("d-none");
    showAlert(connectStatus, "Connected successfully.", "success");
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
    showAlert(emailDetailStatus, "Email details loaded.", "success");
    return;
  }

  if (message.event === "email_classified") {
    if (!message.success) {
      showAlert(emailDetailStatus, message.error || "Could not label email.", "danger");
      return;
    }

    let actionText = `Email stored with label ${message.record?.label || "unknown"}.`;
    let alertStyle = "success";

    if (message.updated) {
      actionText = `Existing email label updated to ${message.record?.label || "unknown"}.`;
      alertStyle = "info";
    } else if (message.duplicate) {
      actionText = `Email already stored as ${message.record?.label || "label"}.`;
      alertStyle = "warning";
    }

    showAlert(emailDetailStatus, `${actionText} Database records: ${message.database_count}.`, alertStyle);
    return;
  }

  if (message.event === "email_tested") {
    if (!message.success) {
      showAlert(emailDetailStatus, message.error || "Could not test email.", "danger");
      return;
    }

    showAlert(emailDetailStatus, `Stub model result: ${message.predicted_label} (${Math.round((message.confidence || 0) * 100)}% confidence).`, "info");
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

  if (!message.success) {
    showAlert(connectStatus, message.error || "An unexpected error happened.", "danger");
  }
}

function populateForms(config) {
  const { connection, preferences } = config;

  document.getElementById("host").value = connection.host || "";
  document.getElementById("port").value = connection.port || 993;
  document.getElementById("username").value = connection.username || "";
  document.getElementById("password").value = connection.password || "";
  document.getElementById("ssl").checked = Boolean(connection.ssl);

  setMultiSelectValues("allowed-languages", preferences.allowed_languages || []);
  setMultiSelectValues("allowed-countries", preferences.allowed_countries || []);
  document.getElementById("allow-links").checked = Boolean(preferences.allow_links);
  document.getElementById("allow-undisclosed").checked = Boolean(preferences.allow_undisclosed);
  document.getElementById("duplicate-threshold").value = preferences.duplicate_subject_threshold || 3;
}

function readConnectionForm() {
  return {
    host: document.getElementById("host").value.trim(),
    port: Number(document.getElementById("port").value),
    username: document.getElementById("username").value.trim(),
    password: document.getElementById("password").value,
    ssl: document.getElementById("ssl").checked,
  };
}

function readConfigForm() {
  return {
    allowed_languages: getMultiSelectValues("allowed-languages"),
    allowed_countries: getMultiSelectValues("allowed-countries"),
    allow_links: document.getElementById("allow-links").checked,
    allow_undisclosed: document.getElementById("allow-undisclosed").checked,
    duplicate_subject_threshold: Number(document.getElementById("duplicate-threshold").value) || 1,
  };
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
    emailTableBody.innerHTML = `
      <tr>
        <td colspan="3" class="text-center text-muted py-4">No emails found in the inbox.</td>
      </tr>
    `;
    return;
  }

  emailTableBody.innerHTML = emails
    .map(
      (email) => `
        <tr class="email-row" data-email-uid="${email.uid}">
          <td>${escapeHtml(email.subject)}</td>
          <td>${escapeHtml(email.from)}</td>
          <td>${escapeHtml(email.date)}</td>
        </tr>
      `
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
  setDetailTab("body");
  document.getElementById("detail-subject").textContent = "Loading email...";
  document.getElementById("detail-summary").textContent = "Fetching full body and details from the server.";
  document.getElementById("email-body-content").textContent = "Loading...";
  document.getElementById("email-headers-content").textContent = "";
  showAlert(emailDetailStatus, "Loading email details...", "info");
  sendCommand("get_email_detail", { uid: state.selectedEmailUid });
}

function renderEmailDetail(email) {
  emailDetailPanel.classList.remove("d-none");
  document.getElementById("detail-subject").textContent = email.subject || "(No subject)";
  document.getElementById("detail-summary").textContent = `${(email.from || []).join(", ") || "Unknown sender"} • ${email.date || "Unknown date"}`;
  document.getElementById("email-body-content").textContent = email.body?.preferred || "No body content available.";
  document.getElementById("detail-from").textContent = (email.from || []).join(", ") || "—";
  document.getElementById("detail-to").textContent = (email.to || []).join(", ") || "—";
  document.getElementById("detail-cc").textContent = (email.cc || []).join(", ") || "—";
  document.getElementById("detail-date").textContent = email.date || "—";
  document.getElementById("detail-message-id").textContent = email.message_id || "—";
  document.getElementById("detail-content-type").textContent = email.content_type || "—";
  document.getElementById("email-headers-content").textContent = (email.headers || [])
    .map((header) => `${header.name}: ${header.value}`)
    .join("\n");
}

function classifySelectedEmail(label) {
  if (!state.selectedEmailUid) {
    showAlert(emailDetailStatus, "Select an email first.", "warning");
    return;
  }

  showAlert(emailDetailStatus, `Saving email as ${label}...`, "info");
  sendCommand("classify_email", { uid: state.selectedEmailUid, label });
}

function testSelectedEmail() {
  if (!state.selectedEmailUid) {
    showAlert(emailDetailStatus, "Select an email first.", "warning");
    return;
  }

  showAlert(emailDetailStatus, "Testing email with stubbed model...", "info");
  sendCommand("test_email", { uid: state.selectedEmailUid });
}

function clearDatabaseWithConfirmation() {
  const typedConfirmation = document.getElementById("clear-database-confirmation").value.trim();
  if (!typedConfirmation) {
    showAlert(debugStatus, 'Type "yes" or "YES" first.', "warning");
    return;
  }

  const firstConfirmation = window.confirm("Are you sure you want to clear the local mail database?");
  if (!firstConfirmation) {
    showAlert(debugStatus, "Database clear cancelled.", "secondary");
    return;
  }

  const secondConfirmation = window.confirm("This action is permanent for the JSON database. Continue?");
  if (!secondConfirmation) {
    showAlert(debugStatus, "Database clear cancelled on second confirmation.", "secondary");
    return;
  }

  showAlert(debugStatus, "Clearing database...", "info");
  sendCommand("clear_database", { confirmation: typedConfirmation });
}

function resetEmailDetailPanel() {
  emailDetailPanel.classList.add("d-none");
  emailDetailStatus.className = "alert d-none mb-3";
  emailDetailStatus.textContent = "";
  document.getElementById("detail-subject").textContent = "Email details";
  document.getElementById("detail-summary").textContent = "Select an email to view its content.";
  document.getElementById("email-body-content").textContent = "Select an email to view the body.";
  document.getElementById("email-headers-content").textContent = "";
  setDetailTab("body");
}

function setDetailTab(tabName) {
  document.querySelectorAll("[data-detail-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.detailTab === tabName);
  });

  document.querySelectorAll(".detail-tab-content").forEach((panel) => {
    panel.classList.toggle("d-none", panel.id !== `detail-tab-${tabName}`);
  });
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
  target.className = `alert alert-${style}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
