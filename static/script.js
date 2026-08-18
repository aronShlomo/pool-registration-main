// ============================================================
// MILLROD SWIM ACADEMY
// BOOKING SYSTEM — UPDATED SCRIPT
// ============================================================

// ============================================================
// LESSON PRICES
// ============================================================

const lessonPrices = {
  "Private Lesson": {
    "Single Lesson": "$80",
    "4 Lessons Package": "$300",
    "8 Lessons Package": "$560",
    "Monthly Program": "$650",
  },

  "Semi-Private Lesson": {
    "Single Lesson": "$50",
    "4 Lessons Package": "$180",
    "8 Lessons Package": "$340",
    "Monthly Program": "$400",
  },

  "Group Lesson": {
    "Single Lesson": "$35",
    "4 Lessons Package": "$120",
    "8 Lessons Package": "$220",
    "Monthly Program": "$260",
  },
};

// ============================================================
// AVAILABLE LESSON TIMES
// ============================================================

const LESSON_TIMES = [
  "9:00 AM",
  "10:00 AM",
  "11:00 AM",
  "12:00 PM",
  "1:00 PM",
  "2:00 PM",
  "3:00 PM",
  "4:00 PM",
];

// ============================================================
// GLOBAL BOOKED SLOTS
// ============================================================

let bookedSlotsCache = [];

// ============================================================
// ELEMENTS
// ============================================================

const lessonType = document.getElementById("lesson_type");

const packageType = document.getElementById("package");

const priceDisplay = document.getElementById("priceDisplay");

// ============================================================
// PRICE
// ============================================================

function getSelectedPrice() {
  const lesson = lessonType?.value || "";
  const pack = packageType?.value || "";

  return lessonPrices[lesson]?.[pack] || "";
}

function updatePrice() {
  if (!priceDisplay) return;

  const price = getSelectedPrice();

  priceDisplay.textContent = price ? `Price: ${price}` : "Price: Select Lesson";
}

lessonType?.addEventListener("change", updatePrice);

packageType?.addEventListener("change", updatePrice);

// ============================================================
// GET FORM DATA
// ============================================================

function getBookingData() {
  const form = document.getElementById("bookingForm");

  if (!form) {
    return {};
  }

  const lessonTypeValue =
    form.lesson_type?.value ||
    document.getElementById("lesson_type")?.value ||
    form.querySelector("[name='lesson_type']")?.value ||
    "";

  const packageValue =
    form.package?.value ||
    document.getElementById("package")?.value ||
    form.querySelector("[name='package']")?.value ||
    "";

  return {
    name: form.name?.value.trim() || "",

    age: form.age?.value || "",

    phone: form.phone?.value.trim() || "",

    email: form.email?.value.trim() || "",

    lesson_type: lessonTypeValue,

    package: packageValue,

    lesson_date: form.lesson_date?.value || form.date?.value || "",

    lesson_time: form.lesson_time?.value || form.time?.value || "",

    price: getSelectedPrice(),

    medical: form.medical?.value || "",

    notes: form.notes?.value || "",
  };
}

// ============================================================
// MESSAGE
// ============================================================

function showMessage(message, success = true) {
  const box = document.getElementById("bookingMessage");

  if (!box) return;

  box.className = success ? "success-message" : "error-message";

  box.innerHTML = message;

  box.scrollIntoView({
    behavior: "smooth",
    block: "center",
  });
}

// ============================================================
// LOAD BOOKED SLOTS
// ============================================================

async function fetchBookedSlots() {
  try {
    const response = await fetch("/api/booked-slots", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error("Unable to load booked slots.");
    }

    const data = await response.json();

    bookedSlotsCache = Array.isArray(data) ? data : [];

    return bookedSlotsCache;
  } catch (error) {
    console.error("Booked slots error:", error);

    bookedSlotsCache = [];

    return [];
  }
}

// ============================================================
// GET BOOKED TIMES FOR DATE
// ============================================================

function getBookedTimes(date) {
  return bookedSlotsCache
    .filter((slot) => slot.date === date)
    .map((slot) => slot.time);
}

// ============================================================
// DATE AVAILABILITY
// ============================================================

function getDateAvailability(date) {
  const dateObj = new Date(`${date}T00:00:00`);

  // Sunday = closed
  if (dateObj.getDay() === 0) {
    return {
      status: "closed",
      available: 0,
      total: LESSON_TIMES.length,
    };
  }

  const bookedTimes = getBookedTimes(date);

  const available = LESSON_TIMES.filter((time) => !bookedTimes.includes(time));

  if (available.length === 0) {
    return {
      status: "full",
      available: 0,
      total: LESSON_TIMES.length,
    };
  }

  return {
    status: "available",
    available: available.length,
    total: LESSON_TIMES.length,
  };
}

// ============================================================
// UPDATE TIME SELECT
// ============================================================

function updateAvailableTimes(selectedDate) {
  const timeSelect = document.getElementById("lesson_time");

  if (!timeSelect) {
    return;
  }

  const bookedTimes = getBookedTimes(selectedDate);

  timeSelect.innerHTML = "";

  const availableTimes = LESSON_TIMES.filter(
    (time) => !bookedTimes.includes(time),
  );

  // ----------------------------------------------------------
  // NO AVAILABLE TIMES
  // ----------------------------------------------------------

  if (availableTimes.length === 0) {
    const option = document.createElement("option");

    option.value = "";

    option.textContent = "No times available";

    option.disabled = true;

    option.selected = true;

    timeSelect.appendChild(option);

    return;
  }

  // ----------------------------------------------------------
  // PLACEHOLDER
  // ----------------------------------------------------------

  const placeholder = document.createElement("option");

  placeholder.value = "";

  placeholder.textContent = "Select an available time";

  placeholder.disabled = true;

  placeholder.selected = true;

  timeSelect.appendChild(placeholder);

  // ----------------------------------------------------------
  // AVAILABLE TIMES
  // ----------------------------------------------------------

  availableTimes.forEach((time) => {
    const option = document.createElement("option");

    option.value = time;

    option.textContent = `${time} — Available`;

    timeSelect.appendChild(option);
  });
}

// ============================================================
// SELECT DATE
// ============================================================

function selectDate(date) {
  const availability = getDateAvailability(date);

  if (availability.status === "closed") {
    showMessage("Sunday is closed. Please choose another date.", false);

    return;
  }

  if (availability.status === "full") {
    showMessage(
      "This date is fully booked. Please choose another date.",
      false,
    );

    return;
  }

  const dateInput = document.getElementById("lesson_date");

  if (dateInput) {
    dateInput.value = date;
  }

  updateAvailableTimes(date);

  // Remove previous selection
  document.querySelectorAll(".selected-date").forEach((element) => {
    element.classList.remove("selected-date");
  });

  // Highlight selected calendar date
  const selectedCell = document.querySelector(`[data-date="${date}"]`);

  if (selectedCell) {
    selectedCell.classList.add("selected-date");
  }
}

// ============================================================
// FULLCALENDAR
// ============================================================

async function initializeCalendar() {
  const calendarElement = document.getElementById("calendar");

  if (!calendarElement) {
    console.warn("Calendar #calendar not found.");

    return;
  }

  // Make sure FullCalendar exists
  if (typeof FullCalendar === "undefined") {
    console.error("FullCalendar is not loaded.");

    return;
  }

  await fetchBookedSlots();

  calendarElement.innerHTML = "";

  const calendar = new FullCalendar.Calendar(calendarElement, {
    // ----------------------------------------------------
    // VIEW
    // ----------------------------------------------------

    initialView: "dayGridMonth",

    height: "auto",

    contentHeight: "auto",

    expandRows: true,

    fixedWeekCount: false,

    firstDay: 0,

    // ----------------------------------------------------
    // HEADER
    // ----------------------------------------------------

    headerToolbar: {
      left: "prev,next",

      center: "title",

      right: "today",
    },

    buttonText: {
      today: "Today",
    },

    // ----------------------------------------------------
    // VALID DATE RANGE
    // ----------------------------------------------------

    validRange: function () {
      const today = new Date();

      today.setHours(0, 0, 0, 0);

      const end = new Date(today);

      end.setDate(end.getDate() + 30);

      return {
        start: today,

        end: end,
      };
    },

    // ----------------------------------------------------
    // DATE CELL
    // ----------------------------------------------------

    dayCellDidMount: function (info) {
      const date = info.date;

      const dateString = date.toISOString().split("T")[0];

      const availability = getDateAvailability(dateString);

      const frame = info.el.querySelector(".fc-daygrid-day-frame");

      if (!frame) {
        return;
      }

      // Remove old badge
      const oldBadge = frame.querySelector(".calendar-availability");

      oldBadge?.remove();

      // Remove old classes
      info.el.classList.remove(
        "calendar-available",
        "calendar-full",
        "calendar-unavailable",
      );

      // ------------------------------------------------
      // CLOSED
      // ------------------------------------------------

      if (availability.status === "closed") {
        info.el.classList.add("calendar-unavailable");

        const badge = document.createElement("div");

        badge.className = "calendar-availability closed";

        badge.innerHTML = `
                <span class="availability-dot"></span>
                <span class="availability-text">
                  Closed
                </span>
              `;

        frame.appendChild(badge);

        return;
      }

      // ------------------------------------------------
      // FULLY BOOKED
      // ------------------------------------------------

      if (availability.status === "full") {
        info.el.classList.add("calendar-full");

        const badge = document.createElement("div");

        badge.className = "calendar-availability full";

        badge.innerHTML = `
                <span class="availability-dot"></span>
                <span class="availability-text">
                  Fully Booked
                </span>
              `;

        frame.appendChild(badge);

        return;
      }

      // ------------------------------------------------
      // AVAILABLE
      // ------------------------------------------------

      info.el.classList.add("calendar-available");

      const badge = document.createElement("div");

      badge.className = "calendar-availability available";

      badge.innerHTML = `
              <span class="availability-dot"></span>
              <span class="availability-text">
                Available
              </span>
            `;

      frame.appendChild(badge);
    },

    // ----------------------------------------------------
    // DATE CLICK
    // ----------------------------------------------------

    dateClick: function (info) {
      selectDate(info.dateStr);
    },

    // ----------------------------------------------------
    // MONTH CHANGE
    // ----------------------------------------------------

    datesSet: function () {
      setTimeout(refreshCalendarBadges, 50);
    },
  });

  calendar.render();

  window.millrodCalendar = calendar;
}

// ============================================================
// REFRESH CALENDAR BADGES
// ============================================================

function refreshCalendarBadges() {
  document.querySelectorAll(".fc-daygrid-day").forEach((cell) => {
    const date = cell.getAttribute("data-date");

    if (!date) {
      return;
    }

    const dateObj = new Date(`${date}T00:00:00`);

    const availability = getDateAvailability(date);

    const frame = cell.querySelector(".fc-daygrid-day-frame");

    if (!frame) {
      return;
    }

    const oldBadge = frame.querySelector(".calendar-availability");

    oldBadge?.remove();

    cell.classList.remove(
      "calendar-available",
      "calendar-full",
      "calendar-unavailable",
    );

    // Sunday
    if (dateObj.getDay() === 0) {
      cell.classList.add("calendar-unavailable");

      addCalendarBadge(frame, "closed", "Closed");

      return;
    }

    // Fully booked
    if (availability.status === "full") {
      cell.classList.add("calendar-full");

      addCalendarBadge(frame, "full", "Fully Booked");

      return;
    }

    // Available
    cell.classList.add("calendar-available");

    addCalendarBadge(frame, "available", "Available");
  });
}

// ============================================================
// ADD CALENDAR BADGE
// ============================================================

function addCalendarBadge(frame, type, text) {
  const badge = document.createElement("div");

  badge.className = `calendar-availability ${type}`;

  badge.innerHTML = `
    <span class="availability-dot"></span>
    <span class="availability-text">
      ${text}
    </span>
  `;

  frame.appendChild(badge);
}

// ============================================================
// SEND FOR APPROVAL
// ============================================================

const sendBtn = document.getElementById("sendApprovalBtn");

sendBtn?.addEventListener("click", async function () {
  try {
    const form = document.getElementById("bookingForm");

    if (!form) {
      return;
    }

    // HTML5 validation
    if (!form.checkValidity()) {
      form.reportValidity();

      return;
    }

    const bookingData = getBookingData();

    if (!bookingData.lesson_date) {
      showMessage("Please choose an available date.", false);

      return;
    }

    if (!bookingData.lesson_time) {
      showMessage("Please choose an available lesson time.", false);

      return;
    }

    sendBtn.disabled = true;

    sendBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Sending...`;

    const response = await fetch("/api/create-booking", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(bookingData),
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      showMessage(result.error || "Unable to send booking request.", false);

      return;
    }

    showMessage(
      `
          <div>
            <h3>✅ Request Sent Successfully!</h3>
            <p>
              Your swimming lesson request
              has been sent for approval.
            </p>

            <p>
              The owner will review your request
              and contact you by email.
            </p>
          </div>
        `,
      true,
    );

    form.reset();

    updatePrice();

    const timeSelect = document.getElementById("lesson_time");

    if (timeSelect) {
      timeSelect.innerHTML = `
          <option value="">
            Select an available time
          </option>
        `;
    }

    await fetchBookedSlots();

    if (window.millrodCalendar) {
      window.millrodCalendar.render();
    }
  } catch (error) {
    console.error("Approval error:", error);

    showMessage("Server error. Please try again.", false);
  } finally {
    sendBtn.disabled = false;

    sendBtn.innerHTML = `<i class="fas fa-paper-plane"></i> Send for Approval`;
  }
});

// ============================================================
// PAY WITH STRIPE
// ============================================================

const payBtn = document.getElementById("pay_button");

payBtn?.addEventListener("click", async function () {
  try {
    const form = document.getElementById("bookingForm");

    if (form && !form.checkValidity()) {
      form.reportValidity();

      return;
    }

    const bookingData = getBookingData();

    if (!bookingData.lesson_date || !bookingData.lesson_time) {
      showMessage("Please select an available date and time.", false);

      return;
    }

    payBtn.disabled = true;

    payBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Processing...`;

    const response = await fetch("/api/create-booking", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(bookingData),
    });

    const booking = await response.json();

    if (!response.ok || !booking.success) {
      showMessage(booking.error || "Unable to create booking.", false);

      return;
    }

    const stripeResponse = await fetch("/api/create-checkout-session", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        booking_id: booking.booking_id,
      }),
    });

    const stripe = await stripeResponse.json();

    if (stripe.checkout_url) {
      window.location.href = stripe.checkout_url;
    } else {
      showMessage(stripe.error || "Unable to start payment.", false);
    }
  } catch (error) {
    console.error("Stripe error:", error);

    showMessage("Payment server error. Please try again.", false);
  } finally {
    payBtn.disabled = false;

    payBtn.innerHTML = `<i class="fas fa-credit-card"></i> Pay Now`;
  }
});

// ============================================================
// PAY LATER
// ============================================================

const skipButton = document.getElementById("skip_payment_button");

skipButton?.addEventListener("click", async function () {
  try {
    const form = document.getElementById("bookingForm");

    if (form && !form.checkValidity()) {
      form.reportValidity();

      return;
    }

    const bookingData = getBookingData();

    if (!bookingData.lesson_date || !bookingData.lesson_time) {
      showMessage("Please select an available date and time.", false);

      return;
    }

    skipButton.disabled = true;

    skipButton.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Reserving...`;

    const response = await fetch("/api/create-booking", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(bookingData),
    });

    const result = await response.json();

    if (!response.ok || !result.success) {
      showMessage(result.error || "Unable to reserve lesson.", false);

      return;
    }

    showMessage(
      `
          <div>
            <h3>✅ Reservation Successful!</h3>

            <p>
              Your swimming lesson has been reserved.
            </p>

            <p>
              <strong>Payment:</strong>
              Pay when you arrive
            </p>

            <p>
              <strong>Amount Due:</strong>
              ${bookingData.price}
            </p>

            <p>
              We accept:
              💵 Cash or 📱 Zelle
            </p>

            <p>
              Thank you for choosing
              Millrod Swim Academy!
            </p>
          </div>
        `,
      true,
    );

    if (form) {
      form.reset();
    }

    updatePrice();

    const timeSelect = document.getElementById("lesson_time");

    if (timeSelect) {
      timeSelect.innerHTML = `
          <option value="">
            Select an available time
          </option>
        `;
    }

    await fetchBookedSlots();

    if (window.millrodCalendar) {
      window.millrodCalendar.render();
    }
  } catch (error) {
    console.error("Pay later error:", error);

    showMessage("Server error. Please try again.", false);
  } finally {
    skipButton.disabled = false;

    skipButton.innerHTML = `<i class="fas fa-clock"></i> Pay Later`;
  }
});

// ============================================================
// DATE INPUT CHANGE
// ============================================================

const dateInput = document.getElementById("lesson_date");

dateInput?.addEventListener("change", async function () {
  const date = this.value;

  if (!date) {
    return;
  }

  await fetchBookedSlots();

  const availability = getDateAvailability(date);

  if (availability.status === "closed") {
    showMessage("Sunday is closed. Please choose another date.", false);

    this.value = "";

    return;
  }

  if (availability.status === "full") {
    showMessage(
      "This date is fully booked. Please choose another date.",
      false,
    );

    this.value = "";

    return;
  }

  updateAvailableTimes(date);
});

// ============================================================
// TIME INPUT VALIDATION
// ============================================================

const timeSelect = document.getElementById("lesson_time");

timeSelect?.addEventListener("change", function () {
  const date = dateInput?.value;

  const selectedTime = this.value;

  if (!date || !selectedTime) {
    return;
  }

  const bookedTimes = getBookedTimes(date);

  if (bookedTimes.includes(selectedTime)) {
    showMessage(
      "That time has just been booked. Please choose another available time.",
      false,
    );

    updateAvailableTimes(date);
  }
});

// ============================================================
// REFRESH AVAILABILITY
// ============================================================

async function refreshAvailability() {
  await fetchBookedSlots();

  if (window.millrodCalendar) {
    window.millrodCalendar.render();
  }

  if (dateInput?.value) {
    updateAvailableTimes(dateInput.value);
  }
}

// ============================================================
// INITIALIZE
// ============================================================

document.addEventListener("DOMContentLoaded", async function () {
  console.log("Millrod Swim Academy booking system loaded.");

  updatePrice();

  await fetchBookedSlots();

  await initializeCalendar();
});
