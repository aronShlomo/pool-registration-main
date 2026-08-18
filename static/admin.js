/* ============================================================
   MILLROD SWIM ACADEMY
   ADMIN DASHBOARD JAVASCRIPT
   ============================================================ */

"use strict";

/* ============================================================
   CONFIGURATION
   ============================================================ */

const ADMIN_CONFIG = {
  requestTimeout: 15000,

  sessionMinutes: 5,

  apiPrefix: "/admin/api",
};

/* ============================================================
   DOM READY
   ============================================================ */

document.addEventListener("DOMContentLoaded", function () {
  initializeAdminDashboard();
});

/* ============================================================
   INITIALIZE
   ============================================================ */

function initializeAdminDashboard() {
  setupNavigation();

  setupSearch();

  setupBookingActions();

  setupLogoutProtection();

  initializeSessionTimer();

  loadDashboardStats();
}

/* ============================================================
   NAVIGATION
   ============================================================ */

function setupNavigation() {
  const links = document.querySelectorAll(".sidebar nav a[href^='#']");

  links.forEach(function (link) {
    link.addEventListener("click", function (event) {
      const targetId = link.getAttribute("href");

      if (!targetId || targetId === "#") {
        return;
      }

      const target = document.querySelector(targetId);

      if (!target) {
        return;
      }

      event.preventDefault();

      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });

      links.forEach(function (item) {
        item.classList.remove("active");
      });

      link.classList.add("active");
    });
  });
}

/* ============================================================
   SEARCH BOOKINGS
   ============================================================ */

function setupSearch() {
  const input = document.getElementById("searchInput");

  if (!input) {
    return;
  }

  input.addEventListener("input", function () {
    const query = input.value.trim().toLowerCase();

    const rows = document.querySelectorAll("#bookingTable tbody tr");

    rows.forEach(function (row) {
      const text = row.textContent.toLowerCase();

      if (!query || text.includes(query)) {
        row.style.display = "";
      } else {
        row.style.display = "none";
      }
    });
  });
}

/* ============================================================
   BOOKING ACTIONS
   ============================================================ */

function setupBookingActions() {
  document.addEventListener("click", async function (event) {
    const button = event.target.closest("button");

    if (!button) {
      return;
    }

    const bookingId = button.dataset.id;

    if (!bookingId) {
      return;
    }

    /* -----------------------------------------------
               CONFIRM / APPROVE
            ------------------------------------------------ */

    if (button.classList.contains("confirm-btn")) {
      await approveBooking(bookingId, button);

      return;
    }

    /* -----------------------------------------------
               CANCEL
            ------------------------------------------------ */

    if (button.classList.contains("cancel-btn")) {
      await cancelBooking(bookingId, button);

      return;
    }

    /* -----------------------------------------------
               VIEW
            ------------------------------------------------ */

    if (button.classList.contains("view-btn")) {
      await viewBooking(bookingId);
    }
  });
}

/* ============================================================
   APPROVE BOOKING
   ============================================================ */

async function approveBooking(bookingId, button) {
  if (!bookingId) {
    return;
  }

  const confirmed = window.confirm(
    `Approve booking #${bookingId}?\n\n` +
      `The customer will be notified by email.`,
  );

  if (!confirmed) {
    return;
  }

  const originalHTML = button.innerHTML;

  setButtonLoading(button, "Approving...");

  try {
    const response = await fetchWithTimeout(
      `/admin/update-status/${bookingId}`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",

          Accept: "application/json",
        },

        body: JSON.stringify({
          status: "confirmed",
        }),
      },
    );

    const data = await parseResponse(response);

    if (!response.ok) {
      throw new Error(
        data.message || data.error || `Approval failed (${response.status})`,
      );
    }

    if (data.success === false) {
      throw new Error(data.message || data.error || "Booking approval failed.");
    }

    showToast("Booking approved successfully.", "success");

    /*
     * IMPORTANT:
     *
     * The backend should save the booking first
     * and send the customer email in the background.
     *
     * Therefore this request should return quickly
     * and never remain stuck waiting for Resend.
     */

    setButtonSuccess(button, "Approved");

    setTimeout(function () {
      window.location.reload();
    }, 900);
  } catch (error) {
    console.error("APPROVE BOOKING ERROR:", error);

    restoreButton(button, originalHTML);

    showToast(error.message || "Unable to approve the booking.", "error");
  }
}

/* ============================================================
   CANCEL BOOKING
   ============================================================ */

async function cancelBooking(bookingId, button) {
  if (!bookingId) {
    return;
  }

  const confirmed = window.confirm(`Cancel booking #${bookingId}?`);

  if (!confirmed) {
    return;
  }

  const originalHTML = button.innerHTML;

  setButtonLoading(button, "Cancelling...");

  try {
    const response = await fetchWithTimeout(
      `/admin/update-status/${bookingId}`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",

          Accept: "application/json",
        },

        body: JSON.stringify({
          status: "cancelled",
        }),
      },
    );

    const data = await parseResponse(response);

    if (!response.ok) {
      throw new Error(
        data.message ||
          data.error ||
          `Cancellation failed (${response.status})`,
      );
    }

    if (data.success === false) {
      throw new Error(
        data.message || data.error || "Booking cancellation failed.",
      );
    }

    showToast("Booking cancelled successfully.", "success");

    setButtonSuccess(button, "Cancelled");

    setTimeout(function () {
      window.location.reload();
    }, 900);
  } catch (error) {
    console.error("CANCEL BOOKING ERROR:", error);

    restoreButton(button, originalHTML);

    showToast(error.message || "Unable to cancel the booking.", "error");
  }
}

/* ============================================================
   VIEW BOOKING
   ============================================================ */

async function viewBooking(bookingId) {
  try {
    const response = await fetchWithTimeout(`/admin/api/booking/${bookingId}`, {
      method: "GET",

      headers: {
        Accept: "application/json",
      },
    });

    const data = await parseResponse(response);

    if (!response.ok) {
      throw new Error(data.message || data.error || "Unable to load booking.");
    }

    displayBookingModal(data.booking || data);
  } catch (error) {
    console.error("VIEW BOOKING ERROR:", error);

    showToast(error.message || "Unable to load booking.", "error");
  }
}

/* ============================================================
   BOOKING MODAL
   ============================================================ */

function displayBookingModal(booking) {
  const existing = document.getElementById("adminBookingModal");

  if (existing) {
    existing.remove();
  }

  const modal = document.createElement("div");

  modal.id = "adminBookingModal";

  modal.className = "admin-modal-overlay";

  modal.innerHTML = `

        <div class="admin-modal">

            <button
                type="button"
                class="admin-modal-close"
                aria-label="Close"
            >
                &times;
            </button>


            <div class="admin-modal-header">

                <div class="admin-modal-icon">

                    <i class="fas fa-calendar-check"></i>

                </div>


                <div>

                    <h2>
                        Booking #${escapeHTML(booking.id ?? "")}
                    </h2>

                    <p>
                        Booking details
                    </p>

                </div>

            </div>


            <div class="admin-modal-body">

                ${bookingDetail("Student", booking.name)}

                ${bookingDetail("Email", booking.email)}

                ${bookingDetail("Phone", booking.phone)}

                ${bookingDetail("Lesson", booking.lesson_type)}

                ${bookingDetail("Package", booking.package)}

                ${bookingDetail("Date", booking.lesson_date)}

                ${bookingDetail("Time", booking.lesson_time)}

                ${bookingDetail("Payment", booking.payment_status)}

                ${bookingDetail("Status", booking.status)}

            </div>

        </div>

    `;

  document.body.appendChild(modal);

  const closeButton = modal.querySelector(".admin-modal-close");

  closeButton.addEventListener("click", function () {
    modal.remove();
  });

  modal.addEventListener("click", function (event) {
    if (event.target === modal) {
      modal.remove();
    }
  });
}

/* ============================================================
   BOOKING DETAIL
   ============================================================ */

function bookingDetail(label, value) {
  return `

        <div class="admin-detail-row">

            <span>
                ${escapeHTML(label)}
            </span>

            <strong>
                ${escapeHTML(value ?? "—")}
            </strong>

        </div>

    `;
}

/* ============================================================
   DASHBOARD STATISTICS
   ============================================================ */

async function loadDashboardStats() {
  try {
    const response = await fetchWithTimeout("/admin/api/stats", {
      method: "GET",

      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`Stats request failed (${response.status})`);
    }

    const data = await parseResponse(response);

    if (!data) {
      return;
    }

    updateStat("todayLessons", data.today_lessons);

    updateStat("pendingPayments", data.pending_payments);

    updateStat("confirmedLessons", data.confirmed_lessons);

    updateStat("revenue", data.revenue);
  } catch (error) {
    console.warn("Unable to refresh dashboard statistics:", error);
  }
}

/* ============================================================
   UPDATE STAT
   ============================================================ */

function updateStat(id, value) {
  const element = document.getElementById(id);

  if (!element) {
    return;
  }

  if (value === undefined || value === null) {
    return;
  }

  element.textContent = value;
}

/* ============================================================
   BUTTON LOADING
   ============================================================ */

function setButtonLoading(button, text) {
  if (!button) {
    return;
  }

  button.disabled = true;

  button.dataset.originalHTML = button.innerHTML;

  button.innerHTML = `

        <i class="fas fa-spinner fa-spin"></i>

        <span>
            ${escapeHTML(text)}
        </span>

    `;

  button.classList.add("is-loading");
}

/* ============================================================
   BUTTON SUCCESS
   ============================================================ */

function setButtonSuccess(button, text) {
  if (!button) {
    return;
  }

  button.disabled = true;

  button.innerHTML = `

        <i class="fas fa-check"></i>

        <span>
            ${escapeHTML(text)}
        </span>

    `;

  button.classList.remove("is-loading");

  button.classList.add("is-success");
}

/* ============================================================
   RESTORE BUTTON
   ============================================================ */

function restoreButton(button, html) {
  if (!button) {
    return;
  }

  button.disabled = false;

  button.innerHTML = html || button.dataset.originalHTML || "Try Again";

  button.classList.remove("is-loading", "is-success");
}

/* ============================================================
   FETCH WITH TIMEOUT
   ============================================================ */

async function fetchWithTimeout(
  url,
  options = {},
  timeout = ADMIN_CONFIG.requestTimeout,
) {
  const controller = new AbortController();

  const timeoutId = window.setTimeout(function () {
    controller.abort();
  }, timeout);

  try {
    return await fetch(url, {
      ...options,

      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("The server took too long to respond. Please try again.");
    }

    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

/* ============================================================
   PARSE RESPONSE
   ============================================================ */

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return await response.json();
  }

  const text = await response.text();

  return {
    success: response.ok,

    message: text,
  };
}

/* ============================================================
   LOGOUT PROTECTION
   ============================================================ */

function setupLogoutProtection() {
  const logoutLinks = document.querySelectorAll('a[href*="/admin/logout"]');

  logoutLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      /*
       * Let the normal logout route handle logout.
       */
    });
  });
}

/* ============================================================
   5-MINUTE SESSION TIMER
   ============================================================ */

function initializeSessionTimer() {
  const countdown = document.getElementById("sessionCountdown");

  const timer = document.getElementById("adminSessionTimer");

  if (!countdown || !timer) {
    return;
  }

  const SESSION_SECONDS = ADMIN_CONFIG.sessionMinutes * 60;

  let remaining = SESSION_SECONDS;

  function update() {
    const minutes = Math.floor(remaining / 60);

    const seconds = remaining % 60;

    countdown.textContent =
      `${String(minutes).padStart(2, "0")}:` +
      `${String(seconds).padStart(2, "0")}`;

    timer.classList.remove("warning", "critical");

    if (remaining <= 30) {
      timer.classList.add("critical");
    } else if (remaining <= 60) {
      timer.classList.add("warning");
    }
  }

  update();

  window.setInterval(function () {
    remaining--;

    if (remaining <= 0) {
      countdown.textContent = "00:00";

      window.location.href = "/admin/logout";

      return;
    }

    update();
  }, 1000);
}

/* ============================================================
   TOAST
   ============================================================ */

function showToast(message, type = "info") {
  let container = document.getElementById("adminToastContainer");

  if (!container) {
    container = document.createElement("div");

    container.id = "adminToastContainer";

    container.className = "admin-toast-container";

    document.body.appendChild(container);
  }

  const toast = document.createElement("div");

  toast.className = `admin-toast ${type}`;

  let icon = "fa-circle-info";

  if (type === "success") {
    icon = "fa-circle-check";
  } else if (type === "error") {
    icon = "fa-circle-exclamation";
  } else if (type === "warning") {
    icon = "fa-triangle-exclamation";
  }

  toast.innerHTML = `

        <i class="fas ${icon}"></i>

        <span>
            ${escapeHTML(message)}
        </span>

        <button
            type="button"
            aria-label="Close"
        >
            &times;
        </button>

    `;

  const close = toast.querySelector("button");

  close.addEventListener("click", function () {
    toast.remove();
  });

  container.appendChild(toast);

  window.setTimeout(function () {
    if (toast.isConnected) {
      toast.classList.add("closing");

      window.setTimeout(function () {
        toast.remove();
      }, 250);
    }
  }, 5000);
}

/* ============================================================
   ESCAPE HTML
   ============================================================ */

function escapeHTML(value) {
  const div = document.createElement("div");

  div.textContent = String(value ?? "");

  return div.innerHTML;
}

/* ============================================================
   GLOBAL ERROR HANDLING
   ============================================================ */

window.addEventListener("unhandledrejection", function (event) {
  console.error("Unhandled admin error:", event.reason);
});

/* ============================================================
   GLOBAL API
   ============================================================ */

window.AdminDashboard = {
  approveBooking,

  cancelBooking,

  viewBooking,

  loadDashboardStats,

  showToast,
};
