/* AUREUS AI — authentication and role-based UI */
(() => {
  "use strict";

  const state = { user: null };
  const $ = (id) => document.getElementById(id);

  async function api(path, options = {}) {
    const response = await fetch(path, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    let data = {};
    try { data = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(data.message || `Request failed (${response.status})`);
    return data;
  }

  function setLoggedIn(user) {
    state.user = user;
    document.body.classList.add("authenticated");
    document.body.classList.toggle("is-president", user.role === "PRESIDENT");
    $("accountName").textContent = user.name || user.email;
    $("accountRole").textContent = user.role;
    $("accountAvatar").textContent = (user.name || user.email || "P").trim().charAt(0).toUpperCase();
    document.dispatchEvent(new CustomEvent("aureus:authenticated", { detail: user }));
  }

  function setLoggedOut() {
    state.user = null;
    document.body.classList.remove("authenticated", "is-president");
    document.dispatchEvent(new CustomEvent("aureus:loggedout"));
  }

  async function refreshSession() {
    try {
      const data = await api("/api/auth/me");
      if (data.user) setLoggedIn(data.user);
      else setLoggedOut();
    } catch (_) {
      setLoggedOut();
    }
  }

  function setAuthTab(tab) {
    document.querySelectorAll("[data-auth-tab]").forEach((b) => b.classList.toggle("active", b.dataset.authTab === tab));
    $("loginForm").style.display = tab === "login" ? "grid" : "none";
    $("registerForm").style.display = tab === "register" ? "grid" : "none";
  }

  async function loadAdmin() {
    if (!state.user || state.user.role !== "PRESIDENT") return;
    const [users, audit] = await Promise.all([
      api("/api/admin/users"),
      api("/api/admin/audit"),
    ]);
    $("adminUsersTable").innerHTML = `<table class="user-table"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Action</th></tr></thead><tbody>${users.users.map(u => `
      <tr>
        <td>${escapeHtml(u.name)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${escapeHtml(u.role)}</td>
        <td><span class="user-status ${u.active ? "active" : "disabled"}">${u.active ? "ACTIVE" : "DISABLED"}</span></td>
        <td>${u.role !== "PRESIDENT" ? `<button class="mini-btn" data-toggle-user="${u.id}">${u.active ? "Disable" : "Enable"}</button>` : ""}</td>
      </tr>`).join("")}</tbody></table>`;
    $("adminAudit").innerHTML = audit.audit.map(a => `<div class="audit-line"><strong>${escapeHtml(a.action)}</strong> · ${escapeHtml(a.actor)} · ${escapeHtml(a.time)}</div>`).join("") || `<div class="audit-line">No audit events yet.</div>`;
    document.querySelectorAll("[data-toggle-user]").forEach(btn => btn.addEventListener("click", async () => {
      try { await api(`/api/admin/users/${btn.dataset.toggleUser}/toggle`, { method: "POST" }); await loadAdmin(); }
      catch (err) { alert(err.message); }
    }));
  }

  function escapeHtml(v) {
    return String(v ?? "").replace(/[&<>'"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[ch]));
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-auth-tab]").forEach(b => b.addEventListener("click", () => setAuthTab(b.dataset.authTab)));

    $("loginForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      $("loginError").textContent = "";
      try {
        const data = await api("/api/auth/login", { method: "POST", body: JSON.stringify({ email: $("loginEmail").value.trim(), password: $("loginPassword").value }) });
        setLoggedIn(data.user);
      } catch (err) { $("loginError").textContent = err.message; }
    });

    $("registerForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      $("registerError").textContent = "";
      try {
        const data = await api("/api/auth/register", { method: "POST", body: JSON.stringify({ name: $("registerName").value.trim(), email: $("registerEmail").value.trim(), password: $("registerPassword").value }) });
        setAuthTab("login");
        $("loginEmail").value = data.email || $("registerEmail").value.trim();
        $("loginError").textContent = "Account created. Sign in to continue.";
      } catch (err) { $("registerError").textContent = err.message; }
    });

    $("logoutButton").addEventListener("click", async () => {
      try { await api("/api/auth/logout", { method: "POST" }); } finally { setLoggedOut(); }
    });

    $("createUserForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      $("adminFormError").textContent = "";
      try {
        await api("/api/admin/users", { method: "POST", body: JSON.stringify({
          name: $("newUserName").value.trim(), email: $("newUserEmail").value.trim(), password: $("newUserPassword").value, role: $("newUserRole").value
        }) });
        event.target.reset();
        await loadAdmin();
      } catch (err) { $("adminFormError").textContent = err.message; }
    });

    document.addEventListener("click", (event) => {
      const btn = event.target.closest('[data-page="admin"]');
      if (btn) loadAdmin().catch(err => alert(err.message));
    });

    refreshSession();
  });
})();
