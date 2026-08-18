/* ============================================================
   MILLROD SWIM ACADEMY
   ADMIN DASHBOARD
   ============================================================

   FEATURES
   ------------------------------------------------------------
   • Visible 5-minute security countdown
   • Automatic logout at 00:00
   • Activity detection
   • Timer resets after admin activity
   • Server-side session compatibility
   • Booking view modal
   • Approve booking
   • Reject booking
   • Mark payment paid
   • Return payment to pending
   • Resend emails
   • Search bookings
   • Status filtering
   • Date filtering
   • Dashboard statistics
   • Toast notifications
   • Mobile friendly
   ============================================================ */

(function () {
  "use strict";

  // ========================================================
  // CONFIGURATION
  // ========================================================

  const SESSION_LENGTH_SECONDS = 5 * 60;

  const ACTIVITY_DEBOUNCE_MS = 1000;

  const STATS_REFRESH_MS = 60 * 1000;

  // ========================================================
  // STATE
  // ========================================================

  let secondsRemaining = SESSION_LENGTH_SECONDS;

  let countdownInterval = null;

  let activityTimeout = null;

  let logoutStarted = false;

  // ========================================================
  // DOM HELPERS
  // ========================================================

  function getElement(id) {
    return document.getElementById(id);
  }

  // ========================================================
  // TOAST
  // ========================================================

  function showToast(message, type = "success") {
    let container = getElement("adminToastContainer");

    if (!container) {
      container = document.createElement("div");

      container.id = "adminToastContainer";

      container.style.cssText = `
                position: fixed;
                right: 20px;
                bottom: 20px;
                z-index: 999999;

                display: flex;
                flex-direction: column;
                gap: 10px;

                width: min(
                    420px,
                    calc(100vw - 40px)
                );

                pointer-events: none;
            `;

      document.body.appendChild(container);
    }

    const toast = document.createElement("div");

    let borderColor = "#14834b";

    if (type === "error") {
      borderColor = "#b42323";
    }

    if (type === "warning") {
      borderColor = "#b45309";
    }

    toast.style.cssText = `
            padding: 15px 18px;

            border-left:
                4px solid ${borderColor};

            border-radius: 14px;

            background:
                rgba(255,255,255,.98);

            color: #17324d;

            font-weight: 700;

            line-height: 1.4;

            box-shadow:
                0 18px 45px
                rgba(6,59,115,.18);

            opacity: 0;

            transform:
                translateY(12px);

            transition:
                opacity .25s ease,
                transform .25s ease;
        `;

    toast.textContent = message;

    container.appendChild(toast);

    requestAnimationFrame(function () {
      toast.style.opacity = "1";

      toast.style.transform = "translateY(0)";
    });

    setTimeout(function () {
      toast.style.opacity = "0";

      toast.style.transform = "translateY(12px)";

      setTimeout(function () {
        toast.remove();
      }, 250);
    }, 4000);
  }

  // ========================================================
  // FORMAT TIMER
  // ========================================================

  function formatTime(totalSeconds) {
    totalSeconds = Math.max(0, Math.floor(totalSeconds));

    const minutes = Math.floor(totalSeconds / 60);

    const seconds = totalSeconds % 60;

    return (
      String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0")
    );
  }

  // ========================================================
  // GET TIMER ELEMENTS
  // ========================================================

  function getTimer() {
    return {
      container: getElement("adminSessionTimer"),

      countdown: getElement("sessionCountdown"),
    };
  }

  // ========================================================
  // UPDATE TIMER ON SCREEN
  // ========================================================

  function updateTimerDisplay() {
    const timer = getTimer();

    if (!timer.countdown) {
      console.warn("Admin timer element #sessionCountdown was not found.");

      return;
    }

    timer.countdown.textContent = formatTime(secondsRemaining);

    // ----------------------------------------------------
    // NORMAL
    // ----------------------------------------------------

    if (secondsRemaining > 60) {
      timer.countdown.style.color = "";

      if (timer.container) {
        timer.container.classList.remove("warning", "danger");
      }

      return;
    }

    // ----------------------------------------------------
    // WARNING
    // ----------------------------------------------------

    if (secondsRemaining > 20) {
      timer.countdown.style.color = "#b45309";

      if (timer.container) {
        timer.container.classList.add("warning");

        timer.container.classList.remove("danger");
      }

      return;
    }

    // ----------------------------------------------------
    // DANGER
    // ----------------------------------------------------

    timer.countdown.style.color = "#b42323";

    if (timer.container) {
      timer.container.classList.add("danger");

      timer.container.classList.remove("warning");
    }
  }

  // ========================================================
  // RESET TIMER
  // ========================================================

  function resetTimer() {
    if (logoutStarted) {
      return;
    }

    secondsRemaining = SESSION_LENGTH_SECONDS;

    updateTimerDisplay();
  }

  // ========================================================
  // START TIMER
  // ========================================================

  function startTimer() {
    console.log("Starting admin security timer: 05:00");

    secondsRemaining = SESSION_LENGTH_SECONDS;

    updateTimerDisplay();

    if (countdownInterval) {
      clearInterval(countdownInterval);
    }

    countdownInterval = setInterval(function () {
      if (logoutStarted) {
        return;
      }

      secondsRemaining--;

      updateTimerDisplay();

      // ----------------------------------------
      // EXPIRED
      // ----------------------------------------

      if (secondsRemaining <= 0) {
        expireSession();
      }
    }, 1000);
  }

  // ========================================================
  // EXPIRE SESSION
  // ========================================================

  function expireSession() {
    if (logoutStarted) {
      return;
    }

    logoutStarted = true;

    if (countdownInterval) {
      clearInterval(countdownInterval);

      countdownInterval = null;
    }

    const timer = getTimer();

    if (timer.countdown) {
      timer.countdown.textContent = "00:00";
    }

    showToast(
      "Your secure admin session has expired. Signing you out...",
      "warning",
    );

    /*
     * Give the user a short moment to see
     * the message before redirecting.
     */

    setTimeout(function () {
      window.location.href = "/admin/logout";
    }, 800);
  }

  // ========================================================
  // REGISTER ACTIVITY
  // ========================================================

  function registerActivity() {
    if (logoutStarted) {
      return;
    }

    /*
     * Mouse movement and scrolling can fire
     * hundreds of events.
     *
     * Debounce them so we don't reset the timer
     * continuously.
     */

    if (activityTimeout) {
      return;
    }

    activityTimeout = setTimeout(function () {
      resetTimer();

      activityTimeout = null;
    }, ACTIVITY_DEBOUNCE_MS);
  }

  // ========================================================
  // ACTIVITY EVENTS
  // ========================================================

  function initializeActivityTracking() {
    const events = [
      "click",

      "keydown",

      "mousedown",

      "pointerdown",

      "touchstart",

      "scroll",

      "wheel",

      "input",

      "change",
    ];

    events.forEach(function (eventName) {
      document.addEventListener(eventName, registerActivity, {
        passive: true,
      });
    });

    console.log("Admin activity tracking enabled.");
  }

  // ========================================================
  // API HELPER
  // ========================================================

  async function api(url, options = {}) {
    const requestOptions = {
      credentials: "same-origin",

      ...options,
    };

    requestOptions.headers = {
      "Content-Type": "application/json",

      ...(options.headers || {}),
    };

    const response = await fetch(url, requestOptions);

    // ----------------------------------------------------
    // SESSION EXPIRED
    // ----------------------------------------------------

    if (response.status === 401 || response.status === 403) {
      showToast("Your admin session has expired.", "warning");

      setTimeout(function () {
        window.location.href = "/admin/login?timeout=1";
      }, 500);

      throw new Error("Admin session expired.");
    }

    let data;

    try {
      data = await response.json();
    } catch (error) {
      throw new Error("The server returned an invalid response.");
    }

    if (!response.ok || data.success === false) {
      throw new Error(data.error || data.message || "The request failed.");
    }

    return data;
  }

  // ========================================================
  // BUTTON LOADING
  // ========================================================

  function setButtonLoading(button, loading, text = "Working...") {
    if (!button) {
      return;
    }

    if (loading) {
      if (!button.dataset.originalHtml) {
        button.dataset.originalHtml = button.innerHTML;
      }

      button.disabled = true;

      button.style.opacity = "0.65";

      button.style.cursor = "wait";

      button.innerHTML = `

                <i class="fas fa-spinner fa-spin"></i>

                ${text}

            `;
    } else {
      button.disabled = false;

      button.style.opacity = "";

      button.style.cursor = "";

      if (button.dataset.originalHtml) {
        button.innerHTML = button.dataset.originalHtml;
      }
    }
  }

  // ========================================================
  // ESCAPE HTML
  // ========================================================

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  // ========================================================
  // BOOKING DETAILS
  // ========================================================

  async function viewBooking(id) {
    try {
      const data = await api(`/admin/booking/${id}`);

      const booking = data.booking || data;

      let modal = getElement("bookingDetailsModal");

      if (!modal) {
        modal = document.createElement("div");

        modal.id = "bookingDetailsModal";

        modal.style.cssText = `
                    position: fixed;
                    inset: 0;
                    z-index: 99990;

                    display: flex;
                    align-items: center;
                    justify-content: center;

                    padding: 20px;

                    background:
                        rgba(3,30,52,.60);

                    backdrop-filter:
                        blur(7px);
                `;

        document.body.appendChild(modal);
      }

      const fields = [
        ["Student", booking.name],

        ["Email", booking.email],

        ["Phone", booking.phone],

        ["Lesson", booking.lesson_type],

        ["Package", booking.package],

        ["Date", booking.lesson_date],

        ["Time", booking.lesson_time],

        ["Price", booking.price],

        ["Status", booking.status],

        ["Payment", booking.payment_status],

        ["Payment Method", booking.payment_method],

        ["Created", booking.created_at],
      ];

      modal.innerHTML = `

                <div
                    style="
                        width:min(760px,100%);
                        max-height:90vh;
                        overflow:auto;

                        background:#ffffff;

                        border-radius:24px;

                        padding:28px;

                        box-shadow:
                            0 30px 90px
                            rgba(0,0,0,.30);
                    "
                >

                    <div
                        style="
                            display:flex;
                            align-items:center;
                            justify-content:space-between;

                            gap:20px;

                            margin-bottom:24px;
                        "
                    >

                        <div>

                            <div
                                style="
                                    color:#087fc1;
                                    font-size:11px;
                                    font-weight:800;

                                    text-transform:
                                        uppercase;

                                    letter-spacing:.12em;
                                "
                            >
                                Booking Details
                            </div>


                            <h2
                                style="
                                    margin:5px 0 0;
                                    color:#063b73;
                                "
                            >
                                ${escapeHtml(booking.name || "Student")}
                            </h2>

                        </div>


                        <button
                            type="button"
                            id="closeBookingModal"

                            style="
                                width:42px;
                                height:42px;

                                border:0;
                                border-radius:12px;

                                background:#eef6fa;

                                color:#17324d;

                                cursor:pointer;

                                font-size:22px;
                                font-weight:800;
                            "
                        >
                            ×
                        </button>

                    </div>


                    <div
                        style="
                            display:grid;

                            grid-template-columns:
                                repeat(
                                    auto-fit,
                                    minmax(
                                        200px,
                                        1fr
                                    )
                                );

                            gap:12px;
                        "
                    >

                        ${fields
                          .map(function ([label, value]) {
                            return `

                                    <div
                                        style="
                                            padding:15px;

                                            border:
                                                1px solid
                                                #e3edf3;

                                            border-radius:
                                                14px;

                                            background:
                                                #fbfdfe;
                                        "
                                    >

                                        <div
                                            style="
                                                color:#71869a;

                                                font-size:10px;

                                                font-weight:800;

                                                text-transform:
                                                    uppercase;

                                                letter-spacing:.07em;
                                            "
                                        >
                                            ${escapeHtml(label)}
                                        </div>


                                        <div
                                            style="
                                                margin-top:7px;

                                                color:#17324d;

                                                font-weight:700;

                                                word-break:
                                                    break-word;
                                            "
                                        >
                                            ${escapeHtml(value || "—")}
                                        </div>

                                    </div>

                                `;
                          })
                          .join("")}

                    </div>


                    <div
                        style="
                            display:flex;
                            gap:10px;
                            flex-wrap:wrap;

                            margin-top:24px;
                        "
                    >

                        ${
                          booking.status !== "confirmed"
                            ? `

                                    <button
                                        type="button"

                                        class="modal-confirm"

                                        data-id="${escapeHtml(booking.id)}"

                                        style="
                                            border:0;

                                            border-radius:11px;

                                            padding:12px 17px;

                                            background:#14834b;

                                            color:#fff;

                                            font-weight:800;

                                            cursor:pointer;
                                        "
                                    >
                                        ✓ Approve
                                    </button>

                                `
                            : ""
                        }


                        ${
                          booking.status !== "rejected"
                            ? `

                                    <button
                                        type="button"

                                        class="modal-reject"

                                        data-id="${escapeHtml(booking.id)}"

                                        style="
                                            border:0;

                                            border-radius:11px;

                                            padding:12px 17px;

                                            background:#b42323;

                                            color:#fff;

                                            font-weight:800;

                                            cursor:pointer;
                                        "
                                    >
                                        × Reject
                                    </button>

                                `
                            : ""
                        }


                        ${
                          booking.status === "confirmed"
                            ? `

                                    <button
                                        type="button"

                                        class="modal-paid"

                                        data-id="${escapeHtml(booking.id)}"

                                        style="
                                            border:0;

                                            border-radius:11px;

                                            padding:12px 17px;

                                            background:#087fc1;

                                            color:#fff;

                                            font-weight:800;

                                            cursor:pointer;
                                        "
                                    >
                                        $ Mark Paid
                                    </button>

                                `
                            : ""
                        }

                    </div>

                </div>
            `;

      // ------------------------------------------------
      // CLOSE
      // ------------------------------------------------

      getElement("closeBookingModal")?.addEventListener("click", function () {
        modal.remove();
      });

      // ------------------------------------------------
      // CLICK OUTSIDE
      // ------------------------------------------------

      modal.addEventListener("click", function (event) {
        if (event.target === modal) {
          modal.remove();
        }
      });

      // ------------------------------------------------
      // APPROVE
      // ------------------------------------------------

      modal
        .querySelector(".modal-confirm")
        ?.addEventListener("click", async function () {
          await changeStatus(this.dataset.id, "confirmed", this);

          modal.remove();
        });

      // ------------------------------------------------
      // REJECT
      // ------------------------------------------------

      modal
        .querySelector(".modal-reject")
        ?.addEventListener("click", async function () {
          await changeStatus(this.dataset.id, "rejected", this);

          modal.remove();
        });

      // ------------------------------------------------
      // PAID
      // ------------------------------------------------

      modal
        .querySelector(".modal-paid")
        ?.addEventListener("click", async function () {
          await updatePayment(this.dataset.id, "paid", this);

          modal.remove();
        });
    } catch (error) {
      console.error("Booking details error:", error);

      showToast(error.message, "error");
    }
  }

  // ========================================================
  // CHANGE BOOKING STATUS
  // ========================================================

  async function changeStatus(id, status, button) {
    const action = status === "confirmed" ? "approve" : "reject";

    if (!window.confirm(`Are you sure you want to ${action} this booking?`)) {
      return;
    }

    try {
      setButtonLoading(
        button,
        true,

        status === "confirmed" ? "Approving..." : "Rejecting...",
      );

      const data = await api(
        `/admin/update-status/${id}`,

        {
          method: "POST",

          body: JSON.stringify({
            status: status,
          }),
        },
      );

      showToast(data.message || "Booking updated successfully.");

      setTimeout(function () {
        window.location.reload();
      }, 600);
    } catch (error) {
      setButtonLoading(button, false);

      showToast(error.message, "error");
    }
  }

  // ========================================================
  // PAYMENT STATUS
  // ========================================================

  async function updatePayment(id, paymentStatus, button) {
    const message =
      paymentStatus === "paid"
        ? "Mark this booking as PAID?"
        : "Return this payment to PENDING?";

    if (!window.confirm(message)) {
      return;
    }

    try {
      setButtonLoading(button, true, "Saving...");

      const data = await api(
        `/admin/update-payment/${id}`,

        {
          method: "POST",

          body: JSON.stringify({
            payment_status: paymentStatus,
          }),
        },
      );

      showToast(data.message || "Payment updated successfully.");

      setTimeout(function () {
        window.location.reload();
      }, 600);
    } catch (error) {
      setButtonLoading(button, false);

      showToast(error.message, "error");
    }
  }

  // ========================================================
  // RESEND EMAIL
  // ========================================================

  async function resendEmail(id, type, button) {
    const endpoint =
      type === "approval"
        ? `/admin/resend-approval/${id}`
        : `/admin/resend-rejection/${id}`;

    try {
      setButtonLoading(button, true, "Sending...");

      const data = await api(
        endpoint,

        {
          method: "POST",

          body: "{}",
        },
      );

      showToast(data.message || "Email sent successfully.");

      setButtonLoading(button, false);
    } catch (error) {
      setButtonLoading(button, false);

      showToast(error.message, "error");
    }
  }

  // ========================================================
  // BIND BUTTONS
  // ========================================================

  function bindBookingButtons() {
    // ----------------------------------------------------
    // VIEW
    // ----------------------------------------------------

    document.querySelectorAll(".view-btn").forEach(function (button) {
      if (button.dataset.bound) {
        return;
      }

      button.dataset.bound = "true";

      button.addEventListener("click", function () {
        viewBooking(this.dataset.id);
      });
    });

    // ----------------------------------------------------
    // APPROVE
    // ----------------------------------------------------

    document.querySelectorAll(".confirm-btn").forEach(function (button) {
      if (button.dataset.bound) {
        return;
      }

      button.dataset.bound = "true";

      button.addEventListener("click", function () {
        changeStatus(this.dataset.id, "confirmed", this);
      });
    });

    // ----------------------------------------------------
    // REJECT
    // ----------------------------------------------------

    document.querySelectorAll(".cancel-btn").forEach(function (button) {
      if (button.dataset.bound) {
        return;
      }

      button.dataset.bound = "true";

      button.addEventListener("click", function () {
        changeStatus(this.dataset.id, "rejected", this);
      });
    });

    // ----------------------------------------------------
    // PAID
    // ----------------------------------------------------

    document.querySelectorAll(".paid-btn").forEach(function (button) {
      if (button.dataset.bound) {
        return;
      }

      button.dataset.bound = "true";

      button.addEventListener("click", function () {
        updatePayment(this.dataset.id, "paid", this);
      });
    });

    // ----------------------------------------------------
    // PENDING PAYMENT
    // ----------------------------------------------------

    document
      .querySelectorAll(".pending-payment-btn")
      .forEach(function (button) {
        if (button.dataset.bound) {
          return;
        }

        button.dataset.bound = "true";

        button.addEventListener("click", function () {
          updatePayment(this.dataset.id, "pending", this);
        });
      });

    // ----------------------------------------------------
    // RESEND APPROVAL
    // ----------------------------------------------------

    document
      .querySelectorAll(".resend-approval-btn")
      .forEach(function (button) {
        if (button.dataset.bound) {
          return;
        }

        button.dataset.bound = "true";

        button.addEventListener("click", function () {
          resendEmail(this.dataset.id, "approval", this);
        });
      });

    // ----------------------------------------------------
    // RESEND REJECTION
    // ----------------------------------------------------

    document
      .querySelectorAll(".resend-rejection-btn")
      .forEach(function (button) {
        if (button.dataset.bound) {
          return;
        }

        button.dataset.bound = "true";

        button.addEventListener("click", function () {
          resendEmail(this.dataset.id, "rejection", this);
        });
      });
  }

  // ========================================================
  // SEARCH
  // ========================================================

  function initializeSearch() {
    const input = getElement("searchInput");

    const table = getElement("bookingTable");

    if (!input || !table) {
      return;
    }

    input.addEventListener("input", function () {
      const search = input.value.trim().toLowerCase();

      table.querySelectorAll("tbody tr").forEach(function (row) {
        const text = row.textContent.toLowerCase();

        row.style.display = !search || text.includes(search) ? "" : "none";
      });
    });
  }

  // ========================================================
  // STATUS FILTER
  // ========================================================

  function initializeStatusFilter() {
    const filter = getElement("statusFilter");

    const table = getElement("bookingTable");

    if (!filter || !table) {
      return;
    }

    filter.addEventListener("change", function () {
      const selected = filter.value.trim().toLowerCase();

      table.querySelectorAll("tbody tr").forEach(function (row) {
        if (!selected) {
          row.style.display = "";

          return;
        }

        const rowStatus = (row.dataset.status || row.textContent).toLowerCase();

        row.style.display = rowStatus.includes(selected) ? "" : "none";
      });
    });
  }

  // ========================================================
  // DATE FILTER
  // ========================================================

  function initializeDateFilter() {
    const input = getElement("dateFilter");

    const table = getElement("bookingTable");

    if (!input || !table) {
      return;
    }

    input.addEventListener("change", function () {
      const selected = input.value;

      table.querySelectorAll("tbody tr").forEach(function (row) {
        if (!selected) {
          row.style.display = "";

          return;
        }

        const rowDate = row.dataset.date || "";

        row.style.display = rowDate === selected ? "" : "none";
      });
    });
  }

  // ========================================================
  // DASHBOARD STATS
  // ========================================================

  async function refreshStats() {
    try {
      const data = await api("/admin/api/stats");

      const stats = data.stats || {};

      const mapping = {
        today_lessons: ["todayLessons", "today-lessons"],

        pending_approvals: ["pendingApprovals", "pending-approvals"],

        pending_payments: ["pendingPayments", "pending-payments"],

        confirmed_lessons: ["confirmedLessons", "confirmed-lessons"],

        rejected_bookings: ["rejectedBookings", "rejected-bookings"],

        paid_bookings: ["paidBookings", "paid-bookings"],

        pay_later_bookings: ["payLaterBookings", "pay-later-bookings"],
      };

      Object.entries(mapping).forEach(function ([key, ids]) {
        if (stats[key] === undefined) {
          return;
        }

        ids.forEach(function (id) {
          const element = getElement(id);

          if (element) {
            element.textContent = stats[key];
          }
        });
      });

      const revenue = getElement("dashboardRevenue");

      if (revenue && stats.revenue !== undefined) {
        revenue.textContent = Number(stats.revenue).toLocaleString("en-US", {
          style: "currency",

          currency: "USD",
        });
      }
    } catch (error) {
      console.warn("Admin statistics refresh failed:", error.message);
    }
  }

  // ========================================================
  // AUTO REFRESH
  // ========================================================

  function initializeAutoRefresh() {
    setInterval(function () {
      refreshStats();
    }, STATS_REFRESH_MS);
  }

  // ========================================================
  // ESCAPE TO CLOSE MODAL
  // ========================================================

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") {
      return;
    }

    const modal = getElement("bookingDetailsModal");

    if (modal) {
      modal.remove();
    }
  });

  // ========================================================
  // INITIALIZE ADMIN
  // ========================================================

  function initializeAdmin() {
    console.log("====================================");

    console.log("Millrod Swim Academy Admin");

    console.log("Security timer: 5 minutes");

    console.log("====================================");

    // ----------------------------------------------------
    // START VISIBLE TIMER
    // ----------------------------------------------------

    startTimer();

    // ----------------------------------------------------
    // ACTIVITY TRACKING
    // ----------------------------------------------------

    initializeActivityTracking();

    // ----------------------------------------------------
    // BOOKING BUTTONS
    // ----------------------------------------------------

    bindBookingButtons();

    // ----------------------------------------------------
    // SEARCH / FILTERS
    // ----------------------------------------------------

    initializeSearch();

    initializeStatusFilter();

    initializeDateFilter();

    // ----------------------------------------------------
    // STATS
    // ----------------------------------------------------

    refreshStats();

    initializeAutoRefresh();

    // ----------------------------------------------------
    // VERIFY TIMER EXISTS
    // ----------------------------------------------------

    const timer = getTimer();

    if (timer.countdown) {
      console.log("✓ Admin countdown found.");
    } else {
      console.error("✗ #sessionCountdown was NOT found in admin.html.");
    }
  }

  // ========================================================
  // START WHEN PAGE IS READY
  // ========================================================

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeAdmin);
  } else {
    initializeAdmin();
  }
})();
