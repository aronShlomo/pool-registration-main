// ============================================================
// MILLROD SWIM ACADEMY
// BOOKING SCRIPT — LIVE AVAILABILITY + APPROVAL SUBMISSION
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
// GLOBAL STATE
// ============================================================

let bookedSlotsCache = [];
let calendarInstance = null;

// ============================================================
// HELPER
// ============================================================

function $(id) {
  return document.getElementById(id);
}

// ============================================================
// MESSAGE
// ============================================================

function showMessage(message, success = true) {
  const box = $("bookingMessage");

  if (!box) {
    console.warn("bookingMessage element not found.");
    return;
  }

  box.className = success
    ? "booking-message success-message"
    : "booking-message error-message";

  box.innerHTML = message;

  box.style.display = "block";

  box.scrollIntoView({
    behavior: "smooth",
    block: "center",
  });
}

// ============================================================
// PRICE
// ============================================================

function getSelectedPrice() {
  const lesson = $("lesson_type")?.value || "";

  const pack = $("package")?.value || "";

  return lessonPrices[lesson]?.[pack] || "";
}

function updatePrice() {
  const display = $("priceDisplay");

  if (!display) {
    return;
  }

  const price = getSelectedPrice();

  display.textContent = price ? price : "Select a lesson and package";
}

// ============================================================
// GET BOOKED SLOTS
// ============================================================

async function fetchBookedSlots() {
  try {
    const response = await fetch("/api/booked-slots", {
      cache: "no-store",

      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`Booked slots request failed: ${response.status}`);
    }

    const data = await response.json();

    bookedSlotsCache = Array.isArray(data) ? data : [];

    return bookedSlotsCache;
  } catch (error) {
    console.error("BOOKED SLOTS ERROR:", error);

    bookedSlotsCache = [];

    return [];
  }
}

// ============================================================
// GET BOOKED TIMES FOR DATE
// ============================================================

function getBookedTimes(date) {
  return bookedSlotsCache

    .filter((slot) => String(slot.date) === String(date))

    .map((slot) => String(slot.time).trim());
}

// ============================================================
// DATE AVAILABILITY
// ============================================================

function getDateAvailability(date) {
  const dateObj = new Date(`${date}T00:00:00`);

  // Sunday closed
  if (dateObj.getDay() === 0) {
    return {
      status: "closed",
      available: 0,
      total: LESSON_TIMES.length,
    };
  }

  const booked = new Set(getBookedTimes(date));

  const available = LESSON_TIMES.filter((time) => !booked.has(time));

  return {
    status: available.length === 0 ? "full" : "available",

    available: available.length,

    total: LESSON_TIMES.length,
  };
}

// ============================================================
// UPDATE AVAILABLE TIMES
// ============================================================

function updateAvailableTimes(date) {
  const select = $("lesson_time");

  if (!select) {
    return;
  }

  const booked = new Set(getBookedTimes(date));

  const available = LESSON_TIMES.filter((time) => !booked.has(time));

  select.innerHTML = "";

  if (!available.length) {
    select.innerHTML = `
      <option value="">
        No times available
      </option>
    `;

    return;
  }

  const placeholder = document.createElement("option");

  placeholder.value = "";

  placeholder.textContent = "Select an available time";

  placeholder.disabled = true;

  placeholder.selected = true;

  select.appendChild(placeholder);

  available.forEach((time) => {
    const option = document.createElement("option");

    option.value = time;

    option.textContent = `${time} — Available`;

    select.appendChild(option);
  });
}

// ============================================================
// CALENDAR AVAILABILITY BADGE
// ============================================================

function addAvailabilityBadge(frame, type, text) {
  if (!frame) {
    return;
  }

  const old = frame.querySelector(".calendar-availability");

  old?.remove();

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
// REFRESH CALENDAR BADGES
// ============================================================

function refreshCalendarBadges() {
  document.querySelectorAll(".fc-daygrid-day").forEach((cell) => {
    const date = cell.getAttribute("data-date");

    if (!date) {
      return;
    }

    const frame = cell.querySelector(".fc-daygrid-day-frame");

    if (!frame) {
      return;
    }

    cell.classList.remove(
      "calendar-available",
      "calendar-full",
      "calendar-unavailable",
    );

    const availability = getDateAvailability(date);

    // CLOSED
    if (availability.status === "closed") {
      cell.classList.add("calendar-unavailable");

      addAvailabilityBadge(frame, "closed", "Closed");

      return;
    }

    // FULL
    if (availability.status === "full") {
      cell.classList.add("calendar-full");

      addAvailabilityBadge(frame, "full", "Fully Booked");

      return;
    }

    // AVAILABLE
    cell.classList.add("calendar-available");

    addAvailabilityBadge(frame, "available", "Available");
  });
}

// ============================================================
// SELECT DATE
// ============================================================

function selectDate(date) {
  const availability = getDateAvailability(date);

  // CLOSED
  if (availability.status === "closed") {
    showMessage("Sunday is closed. Please choose another date.", false);

    return;
  }

  // FULL
  if (availability.status === "full") {
    showMessage(
      "This date is fully booked. Please choose another date.",
      false,
    );

    return;
  }

  const dateInput = $("lesson_date");

  if (dateInput) {
    dateInput.value = date;
  }

  updateAvailableTimes(date);

  document
    .querySelectorAll(".selected-date")
    .forEach((el) => el.classList.remove("selected-date"));

  const cell = document.querySelector(`[data-date="${date}"]`);

  cell?.classList.add("selected-date");

  $("lesson_time")?.focus({
    preventScroll: true,
  });
}

// ============================================================
// INITIALIZE FULLCALENDAR
// ============================================================

async function initializeCalendar() {
  const calendarElement = $("calendar");

  if (!calendarElement) {
    console.warn("Calendar element #calendar was not found.");

    return;
  }

  if (typeof FullCalendar === "undefined") {
    console.error("FullCalendar is not loaded.");

    return;
  }

  await fetchBookedSlots();

  calendarElement.innerHTML = "";

  calendarInstance = new FullCalendar.Calendar(calendarElement, {
    initialView: "dayGridMonth",

    height: "auto",

    contentHeight: "auto",

    expandRows: true,

    fixedWeekCount: false,

    firstDay: 0,

    headerToolbar: {
      left: "prev,next",

      center: "title",

      right: "today",
    },

    buttonText: {
      today: "Today",
    },

    // ------------------------------------------------------
    // BOOKING WINDOW
    // ------------------------------------------------------

    validRange() {
      const today = new Date();

      today.setHours(0, 0, 0, 0);

      const end = new Date(today);

      end.setDate(end.getDate() + 30);

      return {
        start: today,

        end: end,
      };
    },

    // ------------------------------------------------------
    // DAY CELL
    // ------------------------------------------------------

    dayCellDidMount(info) {
      const date = info.date.toISOString().split("T")[0];

      const frame = info.el.querySelector(".fc-daygrid-day-frame");

      if (!frame) {
        return;
      }

      const availability = getDateAvailability(date);

      info.el.classList.remove(
        "calendar-available",
        "calendar-full",
        "calendar-unavailable",
      );

      // CLOSED
      if (availability.status === "closed") {
        info.el.classList.add("calendar-unavailable");

        addAvailabilityBadge(frame, "closed", "Closed");
      }

      // FULL
      else if (availability.status === "full") {
        info.el.classList.add("calendar-full");

        addAvailabilityBadge(frame, "full", "Fully Booked");
      }

      // AVAILABLE
      else {
        info.el.classList.add("calendar-available");

        addAvailabilityBadge(frame, "available", "Available");
      }
    },

    // ------------------------------------------------------
    // CLICK DATE
    // ------------------------------------------------------

    dateClick(info) {
      selectDate(info.dateStr);
    },

    // ------------------------------------------------------
    // CALENDAR CHANGED
    // ------------------------------------------------------

    datesSet() {
      setTimeout(refreshCalendarBadges, 50);
    },
  });

  calendarInstance.render();

  window.millrodCalendar = calendarInstance;
}

// ============================================================
// GET BOOKING DATA
// ============================================================

function getBookingData() {
  const form = $("bookingForm");

  if (!form) {
    return {};
  }

  const name =
    form.elements["name"]?.value?.trim() ||
    form.elements["student_name"]?.value?.trim() ||
    "";

  const email = form.elements["email"]?.value?.trim() || "";

  const phone = form.elements["phone"]?.value?.trim() || "";

  const lessonDate = form.elements["lesson_date"]?.value || "";

  const lessonTime = form.elements["lesson_time"]?.value || "";

  return {
    // Customer
    name: name,

    student_name: name,

    email: email,

    phone: phone,

    // Lesson
    lesson_type: form.elements["lesson_type"]?.value || "",

    package: form.elements["package"]?.value || "",

    // Schedule
    lesson_date: lessonDate,

    date: lessonDate,

    lesson_time: lessonTime,

    time: lessonTime,

    // Price
    price: getSelectedPrice(),

    // Student information
    age: form.elements["age"]?.value || "",

    dob: form.elements["dob"]?.value || "",

    // Parent
    parent_name: form.elements["parent_name"]?.value?.trim() || "",

    // Emergency
    emergency_contact: form.elements["emergency_contact"]?.value?.trim() || "",

    emergency_phone: form.elements["emergency_phone"]?.value?.trim() || "",

    // Swimming information
    swimming_experience: form.elements["swimming_experience"]?.value || "",

    // Additional information
    medical: form.elements["medical"]?.value || "",

    notes: form.elements["notes"]?.value || "",
  };
}

// ============================================================
// SUBMIT BOOKING
// ============================================================
//
// IMPORTANT:
// We listen to the FORM submit event.
//
// This prevents the browser from doing:
//
// GET /?student_name=...
//
// and instead sends:
//
// POST /api/create-booking
//
// ============================================================

async function submitBooking(event) {
  // IMPORTANT FIX
  event.preventDefault();

  event.stopPropagation();

  const form = $("bookingForm");

  if (!form) {
    return;
  }

  console.log("BOOKING FORM SUBMIT INTERCEPTED");

  // ----------------------------------------------------------
  // HTML VALIDATION
  // ----------------------------------------------------------

  if (!form.checkValidity()) {
    form.reportValidity();

    return;
  }

  const data = getBookingData();

  // ----------------------------------------------------------
  // DATE REQUIRED
  // ----------------------------------------------------------

  if (!data.lesson_date) {
    showMessage("Please choose an available date.", false);

    return;
  }

  // ----------------------------------------------------------
  // TIME REQUIRED
  // ----------------------------------------------------------

  if (!data.lesson_time) {
    showMessage("Please choose an available lesson time.", false);

    return;
  }

  // ----------------------------------------------------------
  // REFRESH AVAILABILITY
  // ----------------------------------------------------------

  await fetchBookedSlots();

  const availability = getDateAvailability(data.lesson_date);

  // ----------------------------------------------------------
  // SUNDAY
  // ----------------------------------------------------------

  if (availability.status === "closed") {
    showMessage("Sunday is closed. Please choose another date.", false);

    return;
  }

  // ----------------------------------------------------------
  // FULL DATE
  // ----------------------------------------------------------

  if (availability.status === "full") {
    showMessage(
      "This date is fully booked. Please choose another date.",
      false,
    );

    return;
  }

  // ----------------------------------------------------------
  // CHECK SPECIFIC TIME
  // ----------------------------------------------------------

  if (getBookedTimes(data.lesson_date).includes(data.lesson_time)) {
    showMessage(
      "That time has just been booked. Please choose another available time.",
      false,
    );

    updateAvailableTimes(data.lesson_date);

    return;
  }

  // ----------------------------------------------------------
  // BUTTON LOADING STATE
  // ----------------------------------------------------------

  const button = $("sendApprovalBtn");

  const text = button?.querySelector(".button-text");

  const loading = button?.querySelector(".button-loading");

  if (button) {
    button.disabled = true;
  }

  if (text) {
    text.hidden = true;
  }

  if (loading) {
    loading.hidden = false;
  }

  console.log("POST /api/create-booking", data);

  // ----------------------------------------------------------
  // SEND TO SERVER
  // ----------------------------------------------------------

  try {
    const response = await fetch("/api/create-booking", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",

        Accept: "application/json",
      },

      body: JSON.stringify(data),
    });

    const result = await response.json();

    console.log("CREATE BOOKING RESPONSE:", result);

    // --------------------------------------------------------
    // SERVER ERROR
    // --------------------------------------------------------

    if (!response.ok || !result.success) {
      showMessage(
        result.error || "Unable to send your registration for approval.",
        false,
      );

      return;
    }

    // --------------------------------------------------------
    // SUCCESS
    // --------------------------------------------------------

    showMessage(
      `
        <div>
          <h3>✅ Request Sent Successfully!</h3>

          <p>
            Your swimming lesson request has been
            sent to Millrod Swim Academy for approval.
          </p>

          <p>
            You will receive an email after the
            owner reviews your request.
          </p>

          <p>
            <strong>
              Booking #${result.booking_id}
            </strong>
          </p>
        </div>
      `,
      true,
    );

    // --------------------------------------------------------
    // RESET FORM
    // --------------------------------------------------------

    form.reset();

    updatePrice();

    const timeSelect = $("lesson_time");

    if (timeSelect) {
      timeSelect.innerHTML = `
        <option value="">
          Select a date first
        </option>
      `;
    }

    // --------------------------------------------------------
    // REFRESH CALENDAR
    // --------------------------------------------------------

    await fetchBookedSlots();

    calendarInstance?.render();
  } catch (error) {
    console.error("BOOKING SUBMISSION ERROR:", error);

    showMessage(
      "Unable to contact the booking server. Please try again.",
      false,
    );
  } finally {
    // --------------------------------------------------------
    // RESTORE BUTTON
    // --------------------------------------------------------

    if (button) {
      button.disabled = false;
    }

    if (text) {
      text.hidden = false;
    }

    if (loading) {
      loading.hidden = true;
    }
  }
}

// ============================================================
// ATTACH FORM
// ============================================================

function attachBookingForm() {
  const form = $("bookingForm");

  if (!form) {
    console.error("ERROR: #bookingForm was not found.");

    return;
  }

  // ==========================================================
  // IMPORTANT
  // ==========================================================
  //
  // Listen to SUBMIT, not just CLICK.
  //
  // This handles:
  //
  // 1. Clicking the button
  // 2. Pressing Enter
  // 3. Mobile form submission
  //
  // And prevents normal GET submission.
  //
  // ==========================================================

  form.addEventListener("submit", submitBooking);

  console.log("Booking form handler attached.");
}

// ============================================================
// DOM READY
// ============================================================

document.addEventListener("DOMContentLoaded", async function () {
  console.log("Millrod Swim Academy booking system loaded.");

  // ----------------------------------------------------------
  // PRICE EVENTS
  // ----------------------------------------------------------

  $("lesson_type")?.addEventListener("change", updatePrice);

  $("package")?.addEventListener("change", updatePrice);

  // ----------------------------------------------------------
  // DATE EVENT
  // ----------------------------------------------------------

  $("lesson_date")?.addEventListener("change", async function () {
    if (!this.value) {
      return;
    }

    await fetchBookedSlots();

    selectDate(this.value);
  });

  // ----------------------------------------------------------
  // TIME EVENT
  // ----------------------------------------------------------

  $("lesson_time")?.addEventListener("change", async function () {
    const date = $("lesson_date")?.value;

    if (!date || !this.value) {
      return;
    }

    await fetchBookedSlots();

    if (getBookedTimes(date).includes(this.value)) {
      showMessage(
        "That time is no longer available. Please choose another time.",
        false,
      );

      updateAvailableTimes(date);
    }
  });

  // ----------------------------------------------------------
  // FORM
  // ----------------------------------------------------------

  attachBookingForm();

  // ----------------------------------------------------------
  // PRICE
  // ----------------------------------------------------------

  updatePrice();

  // ----------------------------------------------------------
  // CALENDAR
  // ----------------------------------------------------------

  await initializeCalendar();
});
