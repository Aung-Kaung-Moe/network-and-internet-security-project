const app = document.querySelector("#app");
const authButton = document.querySelector("#authButton");

function cookieToken() {
  return document.cookie
    .split(";")
    .map(part => part.trim())
    .find(part => part.startsWith("library_jwt="))
    ?.slice("library_jwt=".length) || "";
}

const state = {
  books: [],
  category: "All",
  search: "",
  token: cookieToken() || localStorage.getItem("libraryToken") || "",
  user: JSON.parse(localStorage.getItem("libraryUser") || "null")
};

function setToken(token, user) {
  state.token = token || "";
  state.user = user || null;
  if (token) {
    localStorage.setItem("libraryToken", token);
    localStorage.setItem("libraryUser", JSON.stringify(user));
    document.cookie = `library_jwt=${token}; Path=/; SameSite=Lax; Max-Age=3600`;
  } else {
    localStorage.removeItem("libraryToken");
    localStorage.removeItem("libraryUser");
    document.cookie = "library_jwt=; Path=/; SameSite=Lax; Max-Age=0";
  }
  syncNav();
}

function clearAuthCookies() {
  const expired = "Path=/; SameSite=Lax; Max-Age=0";
  document.cookie = `library_jwt=; ${expired}`;
  document.cookie = `honeypot_ticket=; ${expired}`;
  document.cookie = `library_jwt=; Domain=localhost; ${expired}`;
  document.cookie = `honeypot_ticket=; Domain=localhost; ${expired}`;
}

function logoutToRealSite() {
  setToken("", null);
  clearAuthCookies();
  location.href = "http://localhost:3000";
}

function syncNav() {
  const route = location.hash || "#/";
  document.querySelectorAll("[data-link]").forEach(link => {
    const isHome = link.dataset.link === "home" && (route === "#/" || route === "#catalog");
    link.classList.toggle("active", isHome || route.startsWith(`#/${link.dataset.link}`));
  });
  authButton.textContent = (state.token || isHoneypotPort()) ? "Logout" : "Login";
}

function wantsAdminRoute() {
  const path = location.pathname.toLowerCase();
  const hash = (location.hash || "").toLowerCase();
  return path === "/admin" || path === "/dashboard" || hash.startsWith("#/admin") || hash.startsWith("#/dashboard");
}

function wantsWebAdminPath() {
  return location.pathname.toLowerCase() === "/webadmin";
}

function isHoneypotPort() {
  const port = location.port || (location.protocol === "https:" ? "443" : "80");
  return port !== "3000" && location.pathname.toLowerCase() !== "/";
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }

  const response = await fetch(path, { ...options, headers });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }

  return data;
}

async function getSession() {
  if (!state.token) {
    return null;
  }

  const data = await api("/api/me");
  state.user = data.user;
  localStorage.setItem("libraryUser", JSON.stringify(data.user));
  return data;
}

async function redirectToHoneypot() {
  if (state.token) {
    document.cookie = `library_jwt=${state.token}; Path=/; SameSite=Lax; Max-Age=3600`;
  }
  const data = await api("/api/honeypot/redirect", { method: "POST", body: "{}" });
  location.href = data.url;
}

function money(value) {
  return `${Number(value || 0).toLocaleString()} MMK`;
}

function shortDate(value) {
  return new Date(value).toLocaleDateString();
}

function coverClass(book) {
  return book.category.toLowerCase();
}

function coverText(book) {
  return book.title.split(" ").slice(0, 3).join(" ");
}

function cover(book, size = "") {
  return `<div class="book-cover ${size} ${coverClass(book)}">${coverText(book)}</div>`;
}

function availability(book) {
  if (book.copiesAvailable > 0) {
    return `<span class="badge">${book.copiesAvailable} available</span>`;
  }
  return `<span class="badge warning">Checked out</span>`;
}

function bookCard(book) {
  return `
    <a class="book-card" href="#/book/${book.id}">
      ${cover(book)}
      <article class="book-meta">
        <h3>${book.title}</h3>
        <div class="meta-line">
          <span>${book.author}</span>
          <span>${book.year}</span>
        </div>
        <p>${book.summary}</p>
        <div class="status-line">
          <span class="badge">${book.category}</span>
          ${availability(book)}
        </div>
      </article>
    </a>
  `;
}

function filteredBooks() {
  return state.books.filter(book => {
    const text = `${book.title} ${book.author} ${book.category} ${book.summary}`.toLowerCase();
    const categoryMatch = state.category === "All" || book.category === state.category;
    const searchMatch = !state.search || text.includes(state.search.toLowerCase());
    return categoryMatch && searchMatch;
  });
}

function renderCatalogResults() {
  const target = document.querySelector("#bookGrid");
  if (!target) {
    return;
  }
  const books = filteredBooks();
  target.innerHTML = books.length
    ? books.map(bookCard).join("")
    : `<div class="empty-state"><p>No books match your search.</p></div>`;
}

function renderHome() {
  const categories = ["All", ...new Set(state.books.map(book => book.category))];

  app.innerHTML = `
    <section class="hero">
      <div class="hero-content">
        <p class="eyebrow">Borrowing portal</p>
        <h1>Northstar Library</h1>
        <p>Browse the public catalog, open a book record, and sign in when you are ready to borrow a copy.</p>
        <div class="hero-actions">
          <a class="primary-button" href="#catalog">Browse Books</a>
          <a class="secondary-button" href="${state.token ? "#/account" : "#/login"}">${state.token ? "View My Books" : "Member Login"}</a>
        </div>
      </div>
    </section>

    <section id="catalog" class="catalog-tools">
      <input class="search-field" id="searchInput" value="${state.search}" placeholder="Search title, author, genre..." aria-label="Search books">
      <div class="filter-row">
        ${categories.map(category => `
          <button class="chip ${category === state.category ? "active" : ""}" data-category="${category}" type="button">${category}</button>
        `).join("")}
      </div>
    </section>

    <section class="book-grid" id="bookGrid"></section>
  `;

  const searchInput = document.querySelector("#searchInput");
  searchInput.addEventListener("input", event => {
    state.search = event.target.value;
    renderCatalogResults();
  });

  document.querySelectorAll("[data-category]").forEach(button => {
    button.addEventListener("click", () => {
      state.category = button.dataset.category;
      document.querySelectorAll("[data-category]").forEach(item => {
        item.classList.toggle("active", item.dataset.category === state.category);
      });
      renderCatalogResults();
      searchInput.focus();
    });
  });

  renderCatalogResults();
}

function renderWebAdminWarning() {
  app.innerHTML = `
    <section class="restricted-panel">
      <p class="eyebrow">Administrative path</p>
      <h1>Restricted Area</h1>
      <p>This is an admin path and not for normal library users.</p>
      <a class="secondary-button" href="/">Back to Library</a>
    </section>
  `;
}

function renderBook(id) {
  const book = state.books.find(item => item.id === id);
  if (!book) {
    app.innerHTML = `<section class="empty-state"><p>Book not found.</p></section>`;
    return;
  }

  app.innerHTML = `
    <section class="detail-layout">
      ${cover(book, "large-cover")}
      <article class="detail-panel">
        <div class="meta-line">
          <a href="#/">Catalog</a>
          <span>/</span>
          <span>${book.category}</span>
        </div>
        <h2>${book.title}</h2>
        <p>${book.summary}</p>
        <div class="facts">
          <div class="fact"><small>Author</small><strong>${book.author}</strong></div>
          <div class="fact"><small>Year</small><strong>${book.year}</strong></div>
          <div class="fact"><small>Shelf</small><strong>${book.shelf}</strong></div>
          <div class="fact"><small>ISBN</small><strong>${book.isbn}</strong></div>
          <div class="fact"><small>Copies</small><strong>${book.copiesAvailable} of ${book.copiesTotal} available</strong></div>
          <div class="fact"><small>Genre</small><strong>${book.category}</strong></div>
        </div>
        <div class="detail-actions">
          <button class="primary-button" id="borrowButton" type="button">Borrow Book</button>
          <a class="secondary-button" href="#/">Back to Catalog</a>
        </div>
        <p class="message" id="detailMessage"></p>
      </article>
    </section>
  `;

  document.querySelector("#borrowButton").addEventListener("click", async () => {
    if (!state.token) {
      location.hash = "#/login";
      return;
    }

    const message = document.querySelector("#detailMessage");
    message.textContent = "";
    message.className = "message";

    try {
      const result = await api("/api/borrow", {
        method: "POST",
        body: JSON.stringify({ bookId: book.id })
      });
      Object.assign(book, result.book);
      message.textContent = result.message;
      message.classList.add("success");
      setTimeout(() => renderBook(book.id), 500);
    } catch (error) {
      message.textContent = error.message;
    }
  });
}

function renderAuth(mode) {
  const isRegister = mode === "register";
  app.innerHTML = `
    <section class="auth-wrap">
      <article class="auth-panel">
        <h2>${isRegister ? "Create Member Account" : "Member Login"}</h2>
        <p class="meta-line">${isRegister ? "Register first, then login to borrow books." : "Login to borrow and return books."}</p>
        <form class="auth-form" id="authForm">
          ${isRegister ? `
            <label>
              Full name
              <input name="fullName" autocomplete="name" placeholder="Library member name">
            </label>
          ` : ""}
          <label>
            Username
            <input name="username" autocomplete="username" required placeholder="student01">
          </label>
          <label>
            Password
            <input name="password" type="password" autocomplete="${isRegister ? "new-password" : "current-password"}" required placeholder="At least 6 characters">
          </label>
          <div class="form-actions">
            <button class="primary-button" type="submit">${isRegister ? "Register" : "Login"}</button>
            <a class="secondary-button" href="${isRegister ? "#/login" : "#/register"}">${isRegister ? "I already have an account" : "Create account"}</a>
          </div>
          <p class="message" id="authMessage"></p>
        </form>
      </article>
    </section>
  `;

  document.querySelector("#authForm").addEventListener("submit", async event => {
    event.preventDefault();
    const form = new FormData(event.target);
    const message = document.querySelector("#authMessage");
    message.textContent = "";
    message.className = "message";

    try {
      const result = await api(isRegister ? "/api/register" : "/api/login", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(form.entries()))
      });
      setToken(result.token, result.user);
      location.hash = "#/account";
    } catch (error) {
      message.textContent = error.message;
    }
  });
}

function loanItem(loan) {
  const overdue = loan.fineMmk > 0;
  return `
    <div class="loan-item ${overdue ? "overdue" : ""}">
      ${cover(loan.book, "mini-cover")}
      <div class="loan-body">
        <div>
          <h3>${loan.book.title}</h3>
          <div class="meta-line">
            <span>Borrowed ${shortDate(loan.borrowedAt)}</span>
            <span>Due ${shortDate(loan.dueAt)}</span>
          </div>
        </div>
        <div class="loan-footer">
          <div class="fine-line">
            ${overdue
              ? `<span class="badge warning">${loan.overdueDays} day overdue</span><strong>${money(loan.fineMmk)} fine</strong>`
              : `<span class="badge">Return allowed</span><strong>${money(0)} fine</strong>`}
          </div>
          <button class="secondary-button return-button" data-loan-id="${loan.id}" ${overdue ? "disabled" : ""} type="button">
            Return Book
          </button>
        </div>
      </div>
    </div>
  `;
}

async function renderAccount() {
  if (!state.token) {
    location.hash = "#/login";
    return;
  }

  app.innerHTML = document.querySelector("#loadingTemplate").innerHTML;

  try {
    const data = await api("/api/me");
    state.user = data.user;
    localStorage.setItem("libraryUser", JSON.stringify(data.user));

    app.innerHTML = `
      <section class="account-panel">
        <div class="account-header">
          <div>
            <p class="eyebrow">Member account</p>
            <h2>${data.user.fullName}</h2>
            <div class="meta-line">
              <span>Username: ${data.user.username}</span>
              <span>Role: ${data.user.role}</span>
            </div>
          </div>
          <div class="fine-summary">
            <small>Total overdue fine</small>
            <strong>${money(data.totalFineMmk)}</strong>
          </div>
        </div>

        <h3>Borrowed Books</h3>
        <div class="loan-list">
          ${data.loans.length ? data.loans.map(loanItem).join("") : `<div class="empty-state"><p>No borrowed books yet.</p></div>`}
        </div>
        <p class="message" id="accountMessage"></p>
      </section>
    `;

    document.querySelectorAll("[data-loan-id]").forEach(button => {
      button.addEventListener("click", async () => {
        const message = document.querySelector("#accountMessage");
        message.textContent = "";
        message.className = "message";

        try {
          const result = await api("/api/return", {
            method: "POST",
            body: JSON.stringify({ loanId: button.dataset.loanId })
          });
          state.books = state.books.map(book => book.id === result.book.id ? result.book : book);
          message.textContent = result.message;
          message.classList.add("success");
          await renderAccount();
        } catch (error) {
          message.textContent = error.message;
        }
      });
    });
  } catch (error) {
    setToken("", null);
    app.innerHTML = `<section class="empty-state"><p>${error.message}</p></section>`;
  }
}

async function downloadAdminFile(file) {
  const response = await fetch(`/api/admin/download/${file.id}`, {
    headers: {
      Authorization: `Bearer ${state.token}`
    }
  });

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || "Download failed.");
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = file.name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function renderAdmin() {
  app.innerHTML = document.querySelector("#loadingTemplate").innerHTML;

  try {
    const data = await api("/api/admin/files", {
      headers: { Authorization: "" }
    });
    state.user = data.user;
    localStorage.setItem("libraryUser", JSON.stringify(data.user));

    app.innerHTML = `
      <section class="admin-shell">
        <div class="admin-hero">
          <div>
            <p class="eyebrow">Administrative records</p>
            <h1>Library Dashboard</h1>
            <p>Internal borrower exports are available below.</p>
          </div>
          <div class="admin-user">
            <small>Signed in as</small>
            <strong>${data.user.username}</strong>
            <span class="badge warning">admin</span>
          </div>
        </div>

        <section class="admin-files">
          ${data.files.map(file => `
            <article class="admin-file-card">
              <div class="file-icon">CSV</div>
              <div>
                <h3>${file.title}</h3>
                <p>${file.name}</p>
                <span class="badge">${file.rows} records</span>
              </div>
              <button class="primary-button" data-admin-file="${file.id}" type="button">Download</button>
            </article>
          `).join("")}
        </section>
        <p class="message" id="adminMessage"></p>
      </section>
    `;

    document.querySelectorAll("[data-admin-file]").forEach(button => {
      button.addEventListener("click", async () => {
        const message = document.querySelector("#adminMessage");
        const file = data.files.find(item => item.id === button.dataset.adminFile);
        message.textContent = "";
        message.className = "message";

        try {
          await downloadAdminFile(file);
          message.textContent = `${file.name} downloaded.`;
          message.classList.add("success");
        } catch (error) {
          message.textContent = error.message;
        }
      });
    });
  } catch (error) {
    app.innerHTML = `<section class="empty-state"><p>${error.message}</p></section>`;
  }
}

async function loadBooks(force = false) {
  if (!state.books.length || force) {
    const data = await api("/api/books");
    state.books = data.books;
  }
}

async function render() {
  syncNav();
  app.innerHTML = document.querySelector("#loadingTemplate").innerHTML;

  try {
    if (isHoneypotPort()) {
      await renderAdmin();
      syncNav();
      return;
    }

    const hash = location.hash || "#/";
    const [, route, id] = hash.split("/");
    const session = await getSession().catch(() => null);

    if (session?.user?.role === "admin") {
      await redirectToHoneypot();
      return;
    }

    if (wantsWebAdminPath()) {
      renderWebAdminWarning();
      return;
    }

    if (wantsAdminRoute()) {
      location.hash = "#/login";
      syncNav();
      return;
    }

    await loadBooks();

    if (!route || route === "#" || hash === "#catalog") {
      renderHome();
    } else if (route === "book") {
      renderBook(id);
    } else if (route === "login") {
      renderAuth("login");
    } else if (route === "register") {
      renderAuth("register");
    } else if (route === "account") {
      await renderAccount();
    } else {
      renderHome();
    }
  } catch (error) {
    app.innerHTML = `<section class="empty-state"><p>${error.message}</p></section>`;
  }

  syncNav();
}

authButton.addEventListener("click", () => {
  if (isHoneypotPort()) {
    logoutToRealSite();
  } else if (state.token) {
    logoutToRealSite();
  } else {
    location.hash = "#/login";
  }
});

window.addEventListener("hashchange", render);
render();
