/* =========================================================
   MILLROD SWIM ACADEMY - PROFESSIONAL BOOKING SCRIPT
========================================================= */

document.addEventListener("DOMContentLoaded", () => {
  "use strict";

  const API = {
    createBooking: "/api/create-booking",
    bookings: "/api/bookings",
    bookedSlots: "/api/booked-slots",
  };

  // Keep synchronized with Config.LESSON_PRICES.
  const lessonPrices = {
    "Private Lesson": {
      "Single Lesson": 80,
      "4 Lessons Package": 300,
      "8 Lessons Package": 560,
      "Monthly Program": 1000,
    },

    "Semi-Private Lesson": {
      "Single Lesson": 120,
      "4 Lessons Package": 450,
      "8 Lessons Package": 850,
      "Monthly Program": 1500,
    },

    "Group Lesson": {
      "Single Lesson": 60,
      "4 Lessons Package": 220,
      "8 Lessons Package": 400,
      "Monthly Program": 700,
    },
  };

  const timeSlots = [
    ["09:00", "09:00 AM"],
    ["10:00", "10:00 AM"],
    ["11:00", "11:00 AM"],
    ["12:00", "12:00 PM"],
    ["13:00", "01:00 PM"],
    ["14:00", "02:00 PM"],
    ["15:00", "03:00 PM"],
    ["16:00", "04:00 PM"],
    ["17:00", "05:00 PM"],
  ];

  const form = document.getElementById("bookingForm");
  const calendarElement = document.getElementById("calendar");

  const lessonType = document.getElementById("lesson_type");
  const packageType = document.getElementById("package");

  const dateInput = document.getElementById("lesson_date");
  const timeSelect = document.getElementById("lesson_time");

  const priceDisplay = document.getElementById("priceDisplay");

  const sendApprovalBtn = document.getElementById("sendApprovalBtn");

  const bookingMessage = document.getElementById("bookingMessage");

  const agreement = document.getElementById("registrationAgreement");

  const successModal = document.getElementById("successModal");

  const closeSuccessModal = document.getElementById("closeSuccessModal");

  const successDoneBtn = document.getElementById("successDoneBtn");

  let calendar = null;
  let bookedSlots = new Set();
  let isSubmitting = false;

  if (!form) {
    console.error("bookingForm was not found.");
    return;
  }

  /* =========================================================
     MESSAGES
  ========================================================= */

  function showMessage(message, type = "info") {
    if (!bookingMessage) return;

    bookingMessage.textContent = message;
    bookingMessage.className = `booking-message ${type}`;
  }

  function clearMessage() {
    if (!bookingMessage) return;

    bookingMessage.textContent = "";
    bookingMessage.className = "booking-message";
  }

  /* =========================================================
     LOADING STATE
  ========================================================= */

  function setLoading(loading) {
    isSubmitting = loading;

    if (!sendApprovalBtn) return;

    sendApprovalBtn.disabled = loading;

    const text = sendApprovalBtn.querySelector(".button-text");

    const spinner = sendApprovalBtn.querySelector(".button-loading");

    if (text) {
      text.hidden = loading;
    }

    if (spinner) {
      spinner.hidden = !loading;
    }
  }

  /* =========================================================
     HELPERS
  ========================================================= */

  function value(id) {
    const element = document.getElementById(id);

    return element ? String(element.value || "").trim() : "";
  }

  function normalizeDate(value) {
    return value ? String(value).trim().slice(0, 10) : "";
  }

  function normalizeTime(value) {
    if (!value) return "";

    const match = String(value)
      .trim()
      .match(/^(\d{1,2}):(\d{2})/);

    return match
      ? `${match[1].padStart(2, "0")}:${match[2]}`
      : String(value).trim();
  }

  function slotKey(date, time) {
    return `${normalizeDate(date)}|` + `${normalizeTime(time)}`;
  }

  function isSunday(date) {
    const d = new Date(`${date}T12:00:00`);

    return !Number.isNaN(d.getTime()) && d.getDay() === 0;
  }

  /* =========================================================
     PRICE
  ========================================================= */

  function getSelectedPrice() {
    return lessonPrices[lessonType?.value]?.[packageType?.value] ?? null;
  }

  function updatePrice() {
    if (!priceDisplay) return;

    const price = getSelectedPrice();

    if (price === null) {
      priceDisplay.textContent = "Select a lesson and package";
      return;
    }

    priceDisplay.textContent = `$${price.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }

  lessonType?.addEventListener("change", updatePrice);

  packageType?.addEventListener("change", updatePrice);

  /* =========================================================
     LOAD BOOKED SLOTS
  ========================================================= */

  async function loadBookedSlots() {
    try {
      const response = await fetch(API.bookedSlots, {
        headers: {
          Accept: "application/json",
        },
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (!Array.isArray(data)) {
        throw new Error("Invalid availability response");
      }

      bookedSlots = new Set();

      data.forEach((slot) => {
        if (!slot) return;

        let date = normalizeDate(slot.date || slot.lesson_date);

        let time = normalizeTime(slot.time || slot.lesson_time);

        if ((!date || !time) && slot.start) {
          const parts = String(slot.start).split("T");

          date = normalizeDate(parts[0]);

          time = normalizeTime(parts[1]);
        }

        if (date && time) {
          bookedSlots.add(slotKey(date, time));
        }
      });

      updateTimeOptions();

      return true;
    } catch (error) {
      console.error("Availability error:", error);

      showMessage(
        "Availability could not be refreshed. Please try again.",
        "info",
      );

      return false;
    }
  }

  /* =========================================================
     TIME SELECT
  ========================================================= */

  function resetTimeSelect(message = "Select a date first") {
    if (!timeSelect) return;

    timeSelect.innerHTML = "";

    const option = document.createElement("option");

    option.value = "";
    option.textContent = message;
    option.selected = true;

    timeSelect.appendChild(option);

    timeSelect.disabled = true;
  }

  function updateTimeOptions() {
    if (!timeSelect) return;

    const date = normalizeDate(dateInput?.value);

    if (!date) {
      resetTimeSelect();
      return;
    }

    if (isSunday(date)) {
      resetTimeSelect("Closed on Sundays");
      return;
    }

    timeSelect.innerHTML = "";

    const first = document.createElement("option");

    first.value = "";
    first.textContent = "Select an available time";
    first.selected = true;

    timeSelect.appendChild(first);

    let available = 0;

    timeSlots.forEach(([slotValue, label]) => {
      const option = document.createElement("option");

      option.value = slotValue;

      if (bookedSlots.has(slotKey(date, slotValue))) {
        option.textContent = `${label} — Reserved`;

        option.disabled = true;
      } else {
        option.textContent = label;
        available++;
      }

      timeSelect.appendChild(option);
    });

    if (available === 0) {
      resetTimeSelect("No times available for this date");
    } else {
      timeSelect.disabled = false;
    }
  }

  /* =========================================================
     SELECT DATE
  ========================================================= */

  function selectDate(date) {
    date = normalizeDate(date);

    if (!date) return;

    if (isSunday(date)) {
      showMessage(
        "The academy is closed on Sundays. Please choose another date.",
        "info",
      );

      return;
    }

    const selected = new Date(`${date}T12:00:00`);

    const today = new Date();

    today.setHours(0, 0, 0, 0);

    if (selected < today) {
      showMessage("Please choose a future lesson date.", "error");

      return;
    }

    dateInput.value = date;

    updateTimeOptions();

    clearMessage();

    if (window.innerWidth <= 700) {
      dateInput.closest(".form-section")?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }

  dateInput?.addEventListener("change", () => {
    selectDate(dateInput.value);

    if (calendar && dateInput.value) {
      calendar.gotoDate(dateInput.value);
    }
  });

  /* =========================================================
     CALENDAR EVENTS
  ========================================================= */

  async function getCalendarEvents() {
    try {
      const response = await fetch(API.bookings, {
        headers: {
          Accept: "application/json",
        },
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      return Array.isArray(data) ? data : [];
    } catch (error) {
      console.error("Calendar events error:", error);

      return [];
    }
  }

  function convertEvents(items) {
    return items
      .map((item) => {
        if (!item) return null;

        let start = item.start;

        if (!start && item.lesson_date) {
          start = item.lesson_date;

          if (item.lesson_time) {
            start += `T${normalizeTime(item.lesson_time)}`;
          }
        }

        if (!start) return null;

        return {
          title: item.title || "Reserved",

          start,

          display: "block",

          backgroundColor: "#a9b6c2",

          borderColor: "#a9b6c2",

          textColor: "#ffffff",
        };
      })
      .filter(Boolean);
  }

  /* =========================================================
     INITIALIZE CALENDAR
  ========================================================= */

  async function initializeCalendar() {
    if (!calendarElement) {
      return;
    }

    if (typeof FullCalendar === "undefined") {
      showMessage(
        "The booking calendar could not load. Please refresh the page.",
        "error",
      );

      return;
    }

    calendar = new FullCalendar.Calendar(calendarElement, {
      initialView: "dayGridMonth",

      height: "auto",

      contentHeight: "auto",

      fixedWeekCount: false,

      firstDay: 1,

      selectable: true,

      selectMirror: true,

      dayMaxEvents: 2,

      headerToolbar: {
        left: "prev,next today",

        center: "title",

        right: "",
      },

      buttonText: {
        today: "Today",
      },

      events: convertEvents(await getCalendarEvents()),

      dateClick(info) {
        selectDate(info.dateStr);
      },

      select(info) {
        selectDate(info.startStr);

        calendar.unselect();
      },

      datesSet() {
        updateTimeOptions();
      },
    });

    calendar.render();
  }

  /* =========================================================
     REFRESH CALENDAR
  ========================================================= */

  async function refreshCalendar() {
    if (!calendar) return;

    const events = convertEvents(await getCalendarEvents());

    calendar.removeAllEvents();

    events.forEach((event) => {
      calendar.addEvent(event);
    });
  }

  /* =========================================================
     VALIDATION
  ========================================================= */

  function validEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function validPhone(phone) {
    return String(phone || "").replace(/\D/g, "").length >= 7;
  }

  function validateForm() {
    clearMessage();

    if (!form.checkValidity()) {
      form.reportValidity();

      showMessage("Please complete all required fields.", "error");

      return false;
    }

    const required = [
      ["student_name", "Please enter the student's full name."],

      ["parent_name", "Please enter the parent or guardian name."],

      ["emergency_contact", "Please enter an emergency contact."],

      ["swimming_experience", "Please describe the swimmer's experience."],

      ["lesson_date", "Please select a lesson date."],

      ["lesson_time", "Please select an available lesson time."],

      ["lesson_type", "Please select a lesson type."],

      ["package", "Please select a package."],
    ];

    for (const [id, message] of required) {
      if (!value(id)) {
        showMessage(message, "error");

        document.getElementById(id)?.focus();

        return false;
      }
    }

    if (!validEmail(value("email"))) {
      showMessage("Please enter a valid email address.", "error");

      document.getElementById("email")?.focus();

      return false;
    }

    if (!validPhone(value("phone"))) {
      showMessage("Please enter a valid phone number.", "error");

      document.getElementById("phone")?.focus();

      return false;
    }

    if (!validPhone(value("emergency_phone"))) {
      showMessage("Please enter a valid emergency phone number.", "error");

      document.getElementById("emergency_phone")?.focus();

      return false;
    }

    if (isSunday(value("lesson_date"))) {
      showMessage(
        "The academy is closed on Sundays. Please select another date.",
        "error",
      );

      return false;
    }

    if (getSelectedPrice() === null) {
      showMessage("Please select a valid lesson type and package.", "error");

      return false;
    }

    if (agreement && !agreement.checked) {
      showMessage(
        "Please confirm that the registration information is accurate.",
        "error",
      );

      agreement.focus();

      return false;
    }

    if (bookedSlots.has(slotKey(value("lesson_date"), value("lesson_time")))) {
      updateTimeOptions();

      showMessage(
        "That time is already reserved. Please choose another time.",
        "error",
      );

      return false;
    }

    return true;
  }

  /* =========================================================
     BUILD BOOKING PAYLOAD
  ========================================================= */

  function buildPayload() {
    const type = value("lesson_type");

    const pkg = value("package");

    const price = lessonPrices[type]?.[pkg];

    return {
      name: value("student_name"),

      email: value("email"),

      phone: value("phone"),

      lesson_type: type,

      package: pkg,

      price: `$${Number(price).toFixed(2)}`,

      lesson_date: value("lesson_date"),

      lesson_time: value("lesson_time"),

      student_name: value("student_name"),

      dob: value("dob"),

      age: value("age"),

      parent_name: value("parent_name"),

      emergency_contact: value("emergency_contact"),

      emergency_phone: value("emergency_phone"),

      swimming_experience: value("swimming_experience"),

      medical: value("medical"),

      notes: value("notes"),

      payment_method: "pending_approval",

      payment_status: "pending",

      status: "pending",
    };
  }

  /* =========================================================
     SEND FOR APPROVAL
  ========================================================= */

  async function sendForApproval() {
    if (isSubmitting || !validateForm()) {
      return;
    }

    setLoading(true);

    showMessage(
      "Checking availability and sending your registration...",
      "info",
    );

    try {
      await loadBookedSlots();

      const date = value("lesson_date");

      const time = value("lesson_time");

      if (bookedSlots.has(slotKey(date, time))) {
        updateTimeOptions();

        throw new Error(
          "That time was just reserved. Please choose another available time.",
        );
      }

      const response = await fetch(API.createBooking, {
        method: "POST",

        headers: {
          "Content-Type": "application/json",

          Accept: "application/json",
        },

        body: JSON.stringify(buildPayload()),
      });

      let result = null;

      try {
        result = await response.json();
      } catch {
        result = null;
      }

      if (!response.ok || !result?.success) {
        throw new Error(
          result?.error ||
            result?.message ||
            `Registration failed (${response.status}).`,
        );
      }

      console.log("BOOKING CREATED:", result.booking_id);

      await loadBookedSlots();

      await refreshCalendar();

      form.reset();

      if (dateInput) {
        dateInput.value = "";
      }

      resetTimeSelect();

      updatePrice();

      if (calendar) {
        calendar.unselect();
      }

      openSuccessModal();
    } catch (error) {
      console.error("SEND FOR APPROVAL ERROR:", error);

      showMessage(
        error.message ||
          "We could not send your registration. Please try again.",
        "error",
      );
    } finally {
      setLoading(false);
    }
  }

  /* =========================================================
     SUCCESS MODAL
  ========================================================= */

  function openSuccessModal() {
    if (!successModal) {
      showMessage("Your registration was submitted successfully.", "success");

      return;
    }

    successModal.classList.add("is-open");

    successModal.setAttribute("aria-hidden", "false");

    document.body.style.overflow = "hidden";

    setTimeout(() => successDoneBtn?.focus(), 50);
  }

  function closeModal() {
    if (!successModal) return;

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

  /* =========================================================
     PHONE FORMATTING
  ========================================================= */

  function formatPhone(input) {
    if (!input) return;

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

  formatPhone(document.getElementById("phone"));

  formatPhone(document.getElementById("emergency_phone"));

  /* =========================================================
     AUTOMATIC AGE CALCULATION
  ========================================================= */

  const dob = document.getElementById("dob");

  const age = document.getElementById("age");

  dob?.addEventListener("change", () => {
    if (!dob.value || !age) {
      return;
    }

    const birthDate = new Date(`${dob.value}T12:00:00`);

    if (Number.isNaN(birthDate.getTime())) {
      return;
    }

    const today = new Date();

    let calculatedAge = today.getFullYear() - birthDate.getFullYear();

    const monthDifference = today.getMonth() - birthDate.getMonth();

    if (
      monthDifference < 0 ||
      (monthDifference === 0 && today.getDate() < birthDate.getDate())
    ) {
      calculatedAge--;
    }

    if (calculatedAge >= 0 && calculatedAge <= 120) {
      age.value = calculatedAge;
    }
  });

  /* =========================================================
     BUTTON EVENTS
  ========================================================= */

  sendApprovalBtn?.addEventListener("click", (event) => {
    event.preventDefault();

    sendForApproval();
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    sendForApproval();
  });

  /* =========================================================
     INITIALIZATION
  ========================================================= */

  resetTimeSelect();

  updatePrice();

  Promise.all([loadBookedSlots(), initializeCalendar()]).catch((error) => {
    console.error("BOOKING INITIALIZATION ERROR:", error);
  });

  /* =========================================================
     REFRESH AVAILABILITY EVERY 60 SECONDS
  ========================================================= */

  setInterval(async () => {
    if (document.visibilityState !== "visible" || isSubmitting) {
      return;
    }

    await loadBookedSlots();

    await refreshCalendar();
  }, 60000);
});
