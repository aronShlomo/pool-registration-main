/* ============================================================
   MILLROD SWIM ACADEMY
   BOOKING / REGISTRATION SCRIPT
============================================================ */

document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  /* ==========================================================
     ELEMENTS
  ========================================================== */

  const calendarEl = document.getElementById("calendar");

  const form = document.getElementById("bookingForm");

  const submitButton = document.getElementById("sendApprovalBtn");

  const dateInput = document.getElementById("lesson_date");

  const timeSelect = document.getElementById("lesson_time");

  const lessonTypeSelect = document.getElementById("lesson_type");

  const packageSelect = document.getElementById("package");

  const priceDisplay = document.getElementById("priceDisplay");

  const pricePreview = document.getElementById("pricePreview");

  const bookingMessage = document.getElementById("bookingMessage");

  const successModal = document.getElementById("successModal");

  const closeSuccessModal = document.getElementById("closeSuccessModal");

  const successDoneBtn = document.getElementById("successDoneBtn");

  /* ==========================================================
     API ENDPOINTS
  ========================================================== */

  const API = {
    bookedSlots: "/api/booked-slots",

    bookings: "/api/bookings",

    /*
     * IMPORTANT:
     *
     * The booking blueprint is registered with:
     *
     * /api
     *
     * therefore the actual endpoint is:
     *
     * /api/create-booking
     */

    createBooking: "/api/create-booking",
  };

  /* ==========================================================
     CONFIGURATION
  ========================================================== */

  const DAILY_CAPACITY = 8;

  const CLOSED_DAYS = [0];

  /* ==========================================================
     LESSON PRICES
  ========================================================== */

  const lessonPrices = {
    "Private Lesson": {
      "Single Lesson": "$80",

      "4 Lessons Package": "$300",

      "8 Lessons Package": "$560",

      "Monthly Program": "$650",
    },

    "Semi-Private Lesson": {
      "Single Lesson": "$60",

      "4 Lessons Package": "$220",

      "8 Lessons Package": "$400",

      "Monthly Program": "$500",
    },

    "Group Lesson": {
      "Single Lesson": "$40",

      "4 Lessons Package": "$150",

      "8 Lessons Package": "$280",

      "Monthly Program": "$350",
    },
  };

  /* ==========================================================
     STATE
  ========================================================== */

  let calendar = null;

  let bookedSlots = [];

  let selectedDate = "";

  let submitting = false;

  /* ==========================================================
     HELPERS
  ========================================================== */

  function normalizeDate(value) {
    if (!value) {
      return "";
    }

    const text = String(value).trim();

    if (!text) {
      return "";
    }

    if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
      return text;
    }

    if (text.includes("T")) {
      return text.split("T")[0];
    }

    return text.slice(0, 10);
  }

  function normalizeTime(value) {
    if (!value) {
      return "";
    }

    let text = String(value).trim();

    if (!text) {
      return "";
    }

    if (text.includes("T")) {
      text = text.split("T")[1];
    }

    return text.slice(0, 5);
  }

  function slotKey(date, time) {
    return `${normalizeDate(date)}|` + `${normalizeTime(time)}`;
  }

  function isSunday(dateString) {
    if (!dateString) {
      return false;
    }

    const date = new Date(`${dateString}T12:00:00`);

    return date.getDay() === 0;
  }

  function formatDateLong(dateString) {
    if (!dateString) {
      return "";
    }

    const date = new Date(`${dateString}T12:00:00`);

    if (Number.isNaN(date.getTime())) {
      return dateString;
    }

    return date.toLocaleDateString("en-US", {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatDateShort(dateString) {
    if (!dateString) {
      return "";
    }

    const date = new Date(`${dateString}T12:00:00`);

    if (Number.isNaN(date.getTime())) {
      return dateString;
    }

    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  }

  function getRequiredValue(id) {
    const element = document.getElementById(id);

    if (!element) {
      return "";
    }

    return String(element.value || "").trim();
  }

  /* ==========================================================
     MESSAGE
  ========================================================== */

  function clearMessage() {
    if (!bookingMessage) {
      return;
    }

    bookingMessage.textContent = "";

    bookingMessage.className = "booking-message";
  }

  function showMessage(message, type = "info") {
    if (!bookingMessage) {
      return;
    }

    bookingMessage.textContent = message;

    bookingMessage.className = `booking-message show ${type}`;
  }

  /* ==========================================================
     PRICE
  ========================================================== */

  function updatePrice() {
    if (!lessonTypeSelect || !packageSelect || !priceDisplay) {
      return;
    }

    const lessonType = lessonTypeSelect.value;

    const packageName = packageSelect.value;

    if (!lessonType || !packageName) {
      priceDisplay.textContent = "Select a lesson and package";

      pricePreview?.classList.remove("has-price");

      return;
    }

    const price = lessonPrices?.[lessonType]?.[packageName];

    if (!price) {
      priceDisplay.textContent = "Price available upon request";

      return;
    }

    priceDisplay.textContent = price;

    pricePreview?.classList.add("has-price");
  }

  lessonTypeSelect?.addEventListener("change", updatePrice);

  packageSelect?.addEventListener("change", updatePrice);

  /* ==========================================================
     LOAD BOOKED SLOTS
  ========================================================== */

  async function loadBookedSlots() {
    try {
      const response = await fetch(API.bookedSlots, {
        method: "GET",

        headers: {
          Accept: "application/json",
        },

        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`Availability request failed: ${response.status}`);
      }

      const result = await response.json();

      if (Array.isArray(result)) {
        bookedSlots = result;
      } else if (Array.isArray(result?.slots)) {
        bookedSlots = result.slots;
      } else if (Array.isArray(result?.booked_slots)) {
        bookedSlots = result.booked_slots;
      } else {
        bookedSlots = [];
      }

      bookedSlots = bookedSlots
        .map((row) => {
          if (!row) {
            return null;
          }

          const date = normalizeDate(row.date || row.lesson_date || row.start);

          let time = row.time || row.lesson_time;

          if (!time && row.start && String(row.start).includes("T")) {
            time = String(row.start).split("T")[1];
          }

          return {
            date,

            time: normalizeTime(time),
          };
        })

        .filter((row) => row && row.date && row.time);

      refreshTimeSelect();

      updateSelectedDatePanel(selectedDate);

      return bookedSlots;
    } catch (error) {
      console.error("LOAD BOOKED SLOTS ERROR:", error);

      bookedSlots = [];

      showMessage(
        "We could not refresh availability right now. Please try again in a moment.",
        "error",
      );

      return [];
    }
  }

  /* ==========================================================
     GET BOOKINGS FOR CALENDAR
  ========================================================== */

  async function loadCalendarBookings() {
    try {
      const response = await fetch(API.bookings, {
        method: "GET",

        headers: {
          Accept: "application/json",
        },

        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`Calendar request failed: ${response.status}`);
      }

      const result = await response.json();

      if (Array.isArray(result)) {
        return result;
      }

      if (Array.isArray(result?.bookings)) {
        return result.bookings;
      }

      return [];
    } catch (error) {
      console.warn("LOAD CALENDAR BOOKINGS ERROR:", error);

      return [];
    }
  }

  /* ==========================================================
     COUNT BOOKED SLOTS
  ========================================================== */

  function getBookedCountForDate(date) {
    const normalized = normalizeDate(date);

    return bookedSlots.filter((row) => normalizeDate(row.date) === normalized)
      .length;
  }

  /* ==========================================================
     GET AVAILABLE TIMES
  ========================================================== */

  function getAvailableTimesForDate(date) {
    const normalizedDate = normalizeDate(date);

    if (!normalizedDate || isSunday(normalizedDate)) {
      return [];
    }

    const bookedTimes = new Set(
      bookedSlots

        .filter((row) => normalizeDate(row.date) === normalizedDate)

        .map((row) => normalizeTime(row.time)),
    );

    const allTimes = [
      "09:00",

      "10:00",

      "11:00",

      "12:00",

      "13:00",

      "14:00",

      "15:00",

      "16:00",
    ];

    return allTimes.filter((time) => !bookedTimes.has(time));
  }

  /* ==========================================================
     AVAILABILITY STATUS
  ========================================================== */

  function getAvailability(date) {
    const normalized = normalizeDate(date);

    if (!normalized) {
      return {
        status: "closed",

        booked: 0,

        available: 0,

        total: 0,
      };
    }

    if (isSunday(normalized)) {
      return {
        status: "closed",

        booked: 0,

        available: 0,

        total: 0,
      };
    }

    const booked = getBookedCountForDate(normalized);

    const available = getAvailableTimesForDate(normalized).length;

    const total = Math.max(DAILY_CAPACITY, booked + available);

    if (available <= 0) {
      return {
        status: "full",

        booked,

        available: 0,

        total,
      };
    }

    if (available <= 2) {
      return {
        status: "limited",

        booked,

        available,

        total,
      };
    }

    return {
      status: "available",

      booked,

      available,

      total,
    };
  }

  /* ==========================================================
     SELECT DATE
  ========================================================== */

  function selectDate(date) {
    const normalized = normalizeDate(date);

    if (!normalized) {
      return;
    }

    if (isSunday(normalized)) {
      showMessage(
        "The academy is closed on Sundays. Please select another date.",
        "info",
      );

      return;
    }

    const availability = getAvailability(normalized);

    if (availability.status === "full") {
      showMessage(
        "This date is fully booked. Please select another date.",
        "info",
      );

      return;
    }

    selectedDate = normalized;

    if (dateInput) {
      dateInput.value = normalized;
    }

    refreshTimeSelect();

    updateSelectedDatePanel(normalized);

    clearMessage();

    if (window.innerWidth <= 700) {
      setTimeout(() => {
        timeSelect?.scrollIntoView({
          behavior: "smooth",

          block: "center",
        });
      }, 100);
    }
  }

  /* ==========================================================
     TIME SELECT
  ========================================================== */

  function setTimePlaceholder(text) {
    if (!timeSelect) {
      return;
    }

    timeSelect.innerHTML = "";

    const option = document.createElement("option");

    option.value = "";

    option.textContent = text;

    timeSelect.appendChild(option);
  }

  function refreshTimeSelect() {
    if (!timeSelect) {
      return;
    }

    const date = normalizeDate(dateInput?.value || selectedDate);

    if (!date) {
      setTimePlaceholder("Select a date first");

      timeSelect.disabled = true;

      return;
    }

    if (isSunday(date)) {
      setTimePlaceholder("Academy closed on Sunday");

      timeSelect.disabled = true;

      return;
    }

    const times = getAvailableTimesForDate(date);

    if (!times.length) {
      setTimePlaceholder("No times available");

      timeSelect.disabled = true;

      return;
    }

    const previousValue = timeSelect.value;

    timeSelect.innerHTML = "";

    const placeholder = document.createElement("option");

    placeholder.value = "";

    placeholder.textContent = "Select an available time";

    timeSelect.appendChild(placeholder);

    times.forEach((time) => {
      const option = document.createElement("option");

      option.value = time;

      option.textContent = formatTime(time);

      timeSelect.appendChild(option);
    });

    timeSelect.disabled = false;

    if (times.includes(previousValue)) {
      timeSelect.value = previousValue;
    }
  }

  function formatTime(time) {
    if (!time) {
      return "";
    }

    const parts = time.split(":");

    const hour = Number(parts[0]);

    const minute = parts[1] || "00";

    if (Number.isNaN(hour)) {
      return time;
    }

    const suffix = hour >= 12 ? "PM" : "AM";

    const displayHour = hour % 12 || 12;

    return `${displayHour}:${minute} ${suffix}`;
  }

  /* ==========================================================
     SELECTED DATE PANEL
  ========================================================== */

  function updateSelectedDatePanel(date) {
    const panel = document.getElementById("selectedDatePanel");

    if (!panel) {
      return;
    }

    const title = document.getElementById("selectedDateTitle");

    const subtitle = document.getElementById("selectedDateSubtitle");

    const count = document.getElementById("selectedDateCount");

    if (!date) {
      panel.classList.add("empty");

      if (title) {
        title.textContent = "Choose a date";
      }

      if (subtitle) {
        subtitle.textContent = "Select a date to see available lesson times.";
      }

      if (count) {
        count.className = "selected-date-count";

        count.innerHTML = `
          <strong>—</strong>
          <span>spots</span>
        `;
      }

      return;
    }

    const availability = getAvailability(date);

    panel.classList.remove("empty");

    if (title) {
      title.textContent = formatDateLong(date);
    }

    if (subtitle) {
      if (availability.status === "available") {
        subtitle.textContent = "This date has available lesson times.";
      } else if (availability.status === "limited") {
        subtitle.textContent = "Only a few lesson times remain.";
      } else if (availability.status === "full") {
        subtitle.textContent = "All lesson times are reserved.";
      } else {
        subtitle.textContent = "The academy is closed.";
      }
    }

    if (count) {
      count.className = `selected-date-count ${availability.status}`;

      let label = "spots available";

      if (availability.available === 1) {
        label = "spot available";
      }

      if (availability.status === "full") {
        label = "fully booked";
      }

      if (availability.status === "closed") {
        label = "closed";
      }

      count.innerHTML = `
        <strong>
          ${availability.status === "closed" ? "—" : availability.available}
        </strong>

        <span>
          ${label}
        </span>
      `;
    }
  }

  /* ==========================================================
     CALENDAR DAY CLASS
  ========================================================== */

  function getDayClass(dateString) {
    const availability = getAvailability(dateString);

    const classes = [];

    classes.push(`availability-${availability.status}`);

    if (availability.status === "available") {
      classes.push("has-availability");
    }

    if (
      selectedDate &&
      normalizeDate(selectedDate) === normalizeDate(dateString)
    ) {
      classes.push("is-selected-date");
    }

    if (availability.status === "limited") {
      classes.push("is-limited");
    }

    if (availability.status === "full") {
      classes.push("is-full");
    }

    if (availability.status === "closed") {
      classes.push("is-closed");
    }

    return classes;
  }

  /* ==========================================================
     CALENDAR
  ========================================================== */

  async function initializeCalendar() {
    if (!calendarEl) {
      return;
    }

    if (typeof FullCalendar === "undefined") {
      console.error("FullCalendar is not loaded.");

      showMessage(
        "The calendar could not be loaded. Please refresh the page.",
        "error",
      );

      return;
    }

    calendar = new FullCalendar.Calendar(calendarEl, {
      initialView: "dayGridMonth",

      height: "auto",

      fixedWeekCount: false,

      showNonCurrentDates: false,

      selectable: true,

      navLinks: false,

      dayMaxEvents: true,

      headerToolbar: {
        left: "prev,next today",

        center: "title",

        right: "dayGridMonth,listMonth",
      },

      buttonText: {
        today: "Today",

        month: "Month",

        list: "List",
      },

      dateClick: function (info) {
        selectDate(info.dateStr);
      },

      dayCellDidMount: function (info) {
        const date = info.date.toISOString().split("T")[0];

        const cell = info.el;

        const availability = getAvailability(date);

        const classes = getDayClass(date);

        classes.forEach((className) => {
          cell.classList.add(className);
        });

        const frame = cell.querySelector(".fc-daygrid-day-frame");

        if (!frame) {
          return;
        }

        const existing = frame.querySelector(".calendar-day-availability");

        if (existing) {
          existing.remove();
        }

        const label = document.createElement("div");

        label.className = "calendar-day-availability";

        if (availability.status === "available") {
          label.classList.add("available");

          label.textContent = `${availability.available} spots`;
        } else if (availability.status === "limited") {
          label.classList.add("limited");

          label.textContent = `${availability.available} left`;
        } else if (availability.status === "full") {
          label.classList.add("full");

          label.textContent = "Full";
        } else {
          label.classList.add("closed");

          label.textContent = "Closed";
        }

        frame.appendChild(label);
      },

      datesSet: function () {
        setTimeout(decorateCalendarCells, 0);
      },
    });

    calendar.render();

    decorateCalendarCells();

    await refreshCalendarEvents();
  }

  /* ==========================================================
     DECORATE CALENDAR CELLS
  ========================================================== */

  function decorateCalendarCells() {
    if (!calendarEl) {
      return;
    }

    const cells = calendarEl.querySelectorAll(".fc-daygrid-day");

    cells.forEach((cell) => {
      const date = cell.getAttribute("data-date");

      if (!date) {
        return;
      }

      const availability = getAvailability(date);

      const classes = [
        "has-availability",

        "is-selected-date",

        "is-limited",

        "is-full",

        "is-closed",

        "availability-available",

        "availability-limited",

        "availability-full",

        "availability-closed",
      ];

      classes.forEach((className) => {
        cell.classList.remove(className);
      });

      getDayClass(date).forEach((className) => {
        cell.classList.add(className);
      });

      const frame = cell.querySelector(".fc-daygrid-day-frame");

      if (!frame) {
        return;
      }

      let label = frame.querySelector(".calendar-day-availability");

      if (!label) {
        label = document.createElement("div");

        label.className = "calendar-day-availability";

        frame.appendChild(label);
      }

      label.className = "calendar-day-availability";

      if (availability.status === "available") {
        label.classList.add("available");

        label.textContent = `${availability.available} spots`;
      } else if (availability.status === "limited") {
        label.classList.add("limited");

        label.textContent = `${availability.available} left`;
      } else if (availability.status === "full") {
        label.classList.add("full");

        label.textContent = "Full";
      } else {
        label.classList.add("closed");

        label.textContent = "Closed";
      }
    });
  }

  /* ==========================================================
     VALIDATION
  ========================================================== */

  function validateForm() {
    if (!form) {
      return false;
    }

    clearMessage();

    const requiredFields = form.querySelectorAll("[required]");

    let firstInvalid = null;

    for (const field of requiredFields) {
      if (field.type === "checkbox") {
        if (!field.checked) {
          firstInvalid = field;

          break;
        }

        continue;
      }

      if (!String(field.value || "").trim()) {
        firstInvalid = field;

        break;
      }
    }

    if (firstInvalid) {
      showMessage(
        "Please complete all required fields before sending your registration.",
        "error",
      );

      firstInvalid.focus();

      return false;
    }

    const email = getRequiredValue("email");

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!emailPattern.test(email)) {
      showMessage("Please enter a valid email address.", "error");

      document.getElementById("email")?.focus();

      return false;
    }

    const age = Number(getRequiredValue("age"));

    if (!Number.isFinite(age) || age < 1 || age > 120) {
      showMessage("Please enter a valid age.", "error");

      document.getElementById("age")?.focus();

      return false;
    }

    const date = getRequiredValue("lesson_date");

    if (!date) {
      showMessage("Please select a lesson date.", "error");

      return false;
    }

    if (isSunday(date)) {
      showMessage(
        "The academy is closed on Sundays. Please choose another date.",
        "error",
      );

      return false;
    }

    const time = getRequiredValue("lesson_time");

    if (!time) {
      showMessage("Please select an available lesson time.", "error");

      timeSelect?.focus();

      return false;
    }

    const availability = getAvailability(date);

    if (availability.available <= 0) {
      showMessage(
        "There are no lesson times remaining on this date. Please select another date.",
        "error",
      );

      return false;
    }

    return true;
  }

  /* ==========================================================
     BUILD PAYLOAD
  ========================================================== */

  function buildBookingPayload() {
    const payload = {};

    const fields =
      form?.querySelectorAll("input[name], select[name], textarea[name]") || [];

    fields.forEach((field) => {
      if (field.name === "registrationAgreement") {
        return;
      }

      if (field.type === "checkbox") {
        payload[field.name] = field.checked;

        return;
      }

      payload[field.name] = String(field.value || "").trim();
    });

    payload.lesson_date = normalizeDate(payload.lesson_date);

    payload.lesson_time = normalizeTime(payload.lesson_time);

    return payload;
  }

  /* ==========================================================
     SUBMITTING STATE
  ========================================================== */

  function setSubmittingState(state) {
    submitting = state;

    if (!submitButton) {
      return;
    }

    submitButton.disabled = state;

    const text = submitButton.querySelector(".button-text");

    const loading = submitButton.querySelector(".button-loading");

    if (text) {
      text.hidden = state;
    }

    if (loading) {
      loading.hidden = !state;
    }
  }

  /* ==========================================================
     VERIFY SLOT STILL AVAILABLE
  ========================================================== */

  async function verifySlotStillAvailable(date, time) {
    try {
      await loadBookedSlots();

      const key = slotKey(date, time);

      const alreadyBooked = bookedSlots.some((row) => {
        return slotKey(row.date, row.time) === key;
      });

      return !alreadyBooked;
    } catch (error) {
      console.warn("Could not perform client availability check:", error);

      return true;
    }
  }

  /* ==========================================================
     CREATE BOOKING
  ========================================================== */

  async function submitBooking() {
    if (submitting) {
      return;
    }

    if (!validateForm()) {
      return;
    }

    const date = getRequiredValue("lesson_date");

    const time = getRequiredValue("lesson_time");

    setSubmittingState(true);

    clearMessage();

    showMessage(
      "Checking availability and securely sending your registration...",
      "info",
    );

    try {
      const stillAvailable = await verifySlotStillAvailable(date, time);

      if (!stillAvailable) {
        await loadBookedSlots();

        refreshTimeSelect();

        showMessage(
          "That time was just reserved by someone else. Please choose another available time.",
          "error",
        );

        return;
      }

      const payload = buildBookingPayload();

      console.log("Submitting booking to:", API.createBooking);

      console.log("Booking payload:", payload);

      const response = await fetch(API.createBooking, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",

          Accept: "application/json",
        },

        body: JSON.stringify(payload),
      });

      let result = null;

      try {
        result = await response.json();
      } catch {
        result = null;
      }

      if (!response.ok || !result?.success) {
        const serverMessage =
          result?.error ||
          result?.message ||
          `Registration failed (${response.status}).`;

        throw new Error(serverMessage);
      }

      console.log("BOOKING CREATED:", result);

      await loadBookedSlots();

      if (calendar) {
        await refreshCalendarEvents();

        decorateCalendarCells();
      }

      openSuccessModal();

      form.reset();

      selectedDate = "";

      if (dateInput) {
        dateInput.value = "";
      }

      setTimePlaceholder("Select a date first");

      timeSelect.disabled = true;

      updatePrice();

      updateSelectedDatePanel("");

      if (calendar) {
        calendar.unselect();
      }
    } catch (error) {
      console.error("BOOKING SUBMISSION ERROR:", error);

      showMessage(
        error.message ||
          "We could not submit your registration. Please try again.",
        "error",
      );
    } finally {
      setSubmittingState(false);
    }
  }

  /* ==========================================================
     REFRESH CALENDAR EVENTS
  ========================================================== */

  async function refreshCalendarEvents() {
    if (!calendar) {
      return;
    }

    const events = await loadCalendarBookings();

    calendar.removeAllEvents();

    events.forEach((item) => {
      if (!item) {
        return;
      }

      const start = item.start || item.lesson_date;

      if (!start) {
        return;
      }

      calendar.addEvent({
        title: item.title || "Reserved",

        start,

        display: "block",

        backgroundColor: "#a9b6c2",

        borderColor: "#a9b6c2",

        textColor: "#ffffff",
      });
    });

    decorateCalendarCells();
  }

  /* ==========================================================
     SUCCESS MODAL
  ========================================================== */

  function openSuccessModal() {
    if (!successModal) {
      showMessage(
        "Your registration was submitted successfully. Please check your email for updates.",
        "success",
      );

      return;
    }

    successModal.classList.add("is-open");

    successModal.setAttribute("aria-hidden", "false");

    document.body.style.overflow = "hidden";

    setTimeout(() => {
      successDoneBtn?.focus();
    }, 50);
  }

  function closeModal() {
    if (!successModal) {
      return;
    }

    successModal.classList.remove("is-open");

    successModal.setAttribute("aria-hidden", "true");

    document.body.style.overflow = "";
  }

  closeSuccessModal?.addEventListener("click", closeModal);

  successDoneBtn?.addEventListener("click", closeModal);

  document.querySelectorAll("[data-close-modal]").forEach((element) => {
    element.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeModal();
    }
  });

  /* ==========================================================
     DATE INPUT MANUAL CHANGE
  ========================================================== */

  dateInput?.addEventListener("change", () => {
    const date = normalizeDate(dateInput.value);

    if (!date) {
      selectedDate = "";

      refreshTimeSelect();

      updateSelectedDatePanel("");

      return;
    }

    if (isSunday(date)) {
      dateInput.value = "";

      selectedDate = "";

      refreshTimeSelect();

      updateSelectedDatePanel("");

      showMessage(
        "The academy is closed on Sundays. Please choose another date.",
        "info",
      );

      return;
    }

    selectDate(date);

    if (calendar) {
      calendar.gotoDate(date);
    }
  });

  /* ==========================================================
     TIME CHANGE
  ========================================================== */

  timeSelect?.addEventListener("change", () => {
    clearMessage();

    if (!timeSelect.value) {
      return;
    }

    const date = normalizeDate(dateInput?.value);

    if (!date) {
      timeSelect.value = "";

      showMessage("Please select a date before choosing a time.", "error");
    }
  });

  /* ==========================================================
     PHONE FORMATTING
  ========================================================== */

  function formatPhoneInput(input) {
    if (!input) {
      return;
    }

    input.addEventListener("input", () => {
      const digits = input.value.replace(/\D/g, "").slice(0, 10);

      if (digits.length <= 3) {
        input.value = digits;
      } else if (digits.length <= 6) {
        input.value = `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
      } else {
        input.value = `(${digits.slice(0, 3)}) ${digits.slice(
          3,
          6,
        )}-${digits.slice(6)}`;
      }
    });
  }

  formatPhoneInput(document.getElementById("phone"));

  formatPhoneInput(document.getElementById("emergency_phone"));

  /* ==========================================================
     AGE / DOB
  ========================================================== */

  const dobInput = document.getElementById("dob");

  const ageInput = document.getElementById("age");

  dobInput?.addEventListener("change", () => {
    if (!dobInput.value || !ageInput) {
      return;
    }

    const birthDate = new Date(`${dobInput.value}T12:00:00`);

    const today = new Date();

    if (Number.isNaN(birthDate.getTime())) {
      return;
    }

    let age = today.getFullYear() - birthDate.getFullYear();

    const monthDifference = today.getMonth() - birthDate.getMonth();

    if (
      monthDifference < 0 ||
      (monthDifference === 0 && today.getDate() < birthDate.getDate())
    ) {
      age--;
    }

    if (age >= 0 && age <= 120) {
      ageInput.value = age;
    }
  });

  /* ==========================================================
     FORM SUBMISSION
  ========================================================== */

  form?.addEventListener("submit", (event) => {
    event.preventDefault();

    submitBooking();
  });

  /*
   * HTML uses type="button"
   * for the approval button,
   * so explicitly listen for click.
   */

  submitButton?.addEventListener("click", (event) => {
    event.preventDefault();

    submitBooking();
  });

  /* ==========================================================
     CALENDAR CONTROLS
  ========================================================== */

  document.getElementById("calendarTodayBtn")?.addEventListener("click", () => {
    if (!calendar) {
      return;
    }

    calendar.today();

    const today = new Date();

    const date = today.toISOString().split("T")[0];

    const availability = getAvailability(date);

    if (availability.status !== "closed") {
      selectDate(date);
    }
  });

  document
    .getElementById("continueToTimeBtn")
    ?.addEventListener("click", () => {
      const button = document.getElementById("continueToTimeBtn");

      if (button?.disabled) {
        return;
      }

      timeSelect?.scrollIntoView({
        behavior: "smooth",

        block: "center",
      });

      timeSelect?.focus({
        preventScroll: true,
      });
    });

  /* ==========================================================
     INITIALIZE
  ========================================================== */

  setTimePlaceholder("Select a date first");

  if (timeSelect) {
    timeSelect.disabled = true;
  }

  updatePrice();

  updateSelectedDatePanel(selectedDate);

  Promise.all([loadBookedSlots(), initializeCalendar()]).catch((error) => {
    console.error("BOOKING PAGE INITIALIZATION ERROR:", error);
  });

  /* ==========================================================
     REFRESH AVAILABILITY EVERY 60 SECONDS
  ========================================================== */

  setInterval(async () => {
    if (document.visibilityState !== "visible") {
      return;
    }

    await loadBookedSlots();

    if (calendar) {
      await refreshCalendarEvents();

      decorateCalendarCells();
    }
  }, 60000);
});
