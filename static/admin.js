// ============================================================
// MILLROD SWIM ACADEMY
// ADMIN DASHBOARD SCRIPT
// ============================================================

"use strict";

// ============================================================
// PAGE INITIALIZATION
// ============================================================

document.addEventListener("DOMContentLoaded", function () {
  // ==========================================================
  // SEARCH BOOKINGS
  // ==========================================================

  const searchInput = document.getElementById("searchInput");

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      const value = searchInput.value.toLowerCase().trim();

      document
        .querySelectorAll("#bookingTable tbody tr")
        .forEach(function (row) {
          const text = row.textContent.toLowerCase();

          row.style.display = text.includes(value) ? "" : "none";
        });
    });
  }

  // ==========================================================
  // VIEW BOOKING
  // ==========================================================

  document.querySelectorAll(".view-btn").forEach((button) => {
    button.addEventListener("click", async function () {
      const id = this.dataset.id;

      if (!id) {
        alert("Booking ID is missing.");

        return;
      }

      const originalText = this.innerHTML;

      try {
        this.disabled = true;

        this.innerHTML = "⏳ Loading...";

        const response = await fetch(
          `/api/admin/booking/${encodeURIComponent(id)}`,
          {
            headers: {
              Accept: "application/json",
            },
          },
        );

        let booking;

        try {
          booking = await response.json();
        } catch {
          booking = {};
        }

        if (!response.ok) {
          throw new Error(booking.error || "Unable to load booking.");
        }

        if (booking.success === false) {
          throw new Error(booking.error || "Unable to load booking.");
        }

        // ==================================================
        // BOOKING DETAILS
        // ==================================================

        const student = booking.name || booking.student_name || "N/A";

        const email = booking.email || "N/A";

        const phone = booking.phone || "N/A";

        const lesson = booking.lesson_type || "N/A";

        const packageName = booking.package || "N/A";

        const date = booking.lesson_date || booking.date || "N/A";

        const time = booking.lesson_time || booking.time || "N/A";

        const payment = booking.payment_status || "Pending";

        const status = booking.status || "Pending";

        const age = booking.age || "N/A";

        const parent = booking.parent_name || "N/A";

        const emergency = booking.emergency_contact || "N/A";

        const experience = booking.swimming_experience || "N/A";

        const medical = booking.medical || "N/A";

        const notes = booking.notes || "None";

        // ==================================================
        // DISPLAY BOOKING
        // ==================================================

        alert(
          `🏊 MILLROD SWIM ACADEMY
==============================

STUDENT
${student}

AGE
${age}

PARENT / GUARDIAN
${parent}

EMAIL
${email}

PHONE
${phone}

EMERGENCY CONTACT
${emergency}

LESSON
${lesson}

PACKAGE
${packageName}

DATE
${date}

TIME
${time}

SWIMMING EXPERIENCE
${experience}

MEDICAL INFORMATION
${medical}

NOTES
${notes}

PAYMENT STATUS
${payment}

BOOKING STATUS
${status}

==============================`,
        );
      } catch (error) {
        console.error("View booking error:", error);

        alert(error.message || "Unable to load booking.");
      } finally {
        this.disabled = false;

        this.innerHTML = originalText;
      }
    });
  });

  // ==========================================================
  // CONFIRM BOOKING
  // ==========================================================

  document.querySelectorAll(".confirm-btn").forEach((button) => {
    button.addEventListener("click", async function () {
      const id = this.dataset.id;

      if (!id) {
        alert("Booking ID is missing.");

        return;
      }

      const confirmed = confirm("Confirm this swimming lesson booking?");

      if (!confirmed) {
        return;
      }

      await updateBookingStatus(id, "confirmed", this);
    });
  });

  // ==========================================================
  // CANCEL BOOKING
  // ==========================================================

  document.querySelectorAll(".cancel-btn").forEach((button) => {
    button.addEventListener("click", async function () {
      const id = this.dataset.id;

      if (!id) {
        alert("Booking ID is missing.");

        return;
      }

      const confirmed = confirm(
        "Are you sure you want to cancel this booking?",
      );

      if (!confirmed) {
        return;
      }

      await updateBookingStatus(id, "cancelled", this);
    });
  });
});

// ============================================================
// UPDATE BOOKING STATUS
// ============================================================

async function updateBookingStatus(id, status, button = null) {
  if (!id) {
    alert("Booking ID is missing.");

    return;
  }

  const originalText = button?.innerHTML || "";

  try {
    // --------------------------------------------------------
    // BUTTON LOADING STATE
    // --------------------------------------------------------

    if (button) {
      button.disabled = true;

      button.innerHTML =
        status === "confirmed" ? "⏳ Confirming..." : "⏳ Cancelling...";
    }

    // --------------------------------------------------------
    // SEND REQUEST
    // --------------------------------------------------------

    const response = await fetch(
      `/api/admin/update-status/${encodeURIComponent(id)}`,
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",

          Accept: "application/json",
        },

        body: JSON.stringify({
          status: status,
        }),
      },
    );

    // --------------------------------------------------------
    // READ RESPONSE
    // --------------------------------------------------------

    let result;

    try {
      result = await response.json();
    } catch {
      result = {};
    }

    // --------------------------------------------------------
    // CHECK SERVER RESPONSE
    // --------------------------------------------------------

    if (!response.ok) {
      throw new Error(
        result.error || result.message || `Server error (${response.status})`,
      );
    }

    if (!result.success) {
      throw new Error(
        result.error || result.message || "Booking status update failed.",
      );
    }

    // --------------------------------------------------------
    // SUCCESS MESSAGE
    // --------------------------------------------------------

    if (status === "confirmed") {
      alert("✅ Booking confirmed successfully.");
    } else if (status === "cancelled") {
      alert("❌ Booking cancelled successfully.");
    }

    // --------------------------------------------------------
    // REFRESH DASHBOARD
    // --------------------------------------------------------

    window.location.reload();
  } catch (error) {
    console.error("Update booking status error:", error);

    alert(error.message || "Server error. Please try again.");
  } finally {
    if (button) {
      button.disabled = false;

      button.innerHTML = originalText;
    }
  }
}

// ============================================================
// OPTIONAL: REFRESH BOOKINGS
// ============================================================

function refreshBookings() {
  window.location.reload();
}

// ============================================================
// OPTIONAL: SEARCH CLEAR BUTTON
// ============================================================

const clearSearchButton = document.getElementById("clearSearch");

if (clearSearchButton) {
  clearSearchButton.addEventListener("click", function () {
    const searchInput = document.getElementById("searchInput");

    if (searchInput) {
      searchInput.value = "";

      searchInput.dispatchEvent(new Event("input"));

      searchInput.focus();
    }
  });
}
