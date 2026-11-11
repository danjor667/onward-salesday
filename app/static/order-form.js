// Two enhancements to the order form. Without JavaScript the form still
// works: all three sections are shown and the price appears after ordering.
//   1. Show one section at a time, with Back and Continue.
//   2. Show the price as soon as the route, size and speed are chosen.
(function () {
  const form = document.getElementById("order-form");
  if (!form) return;

  // ---- 1. Steps -------------------------------------------------------------
  const steps = Array.from(form.querySelectorAll(".step"));
  const progress = form.querySelector(".progress");
  const back = form.querySelector("[data-back]");
  const next = form.querySelector("[data-next]");
  const submit = form.querySelector("[data-submit]");
  let current = 0;

  function show(index) {
    current = index;
    steps.forEach((step, i) => { step.hidden = i !== current; });
    Array.from(progress.children).forEach((item, i) => {
      item.classList.toggle("active", i === current);
      item.classList.toggle("done", i < current);
    });
    back.hidden = current === 0;
    next.hidden = current === steps.length - 1;
    submit.hidden = current !== steps.length - 1;
  }

  // The browser's own checks (required, max length) for the visible section.
  function stepIsValid() {
    const fields = Array.from(steps[current].querySelectorAll("input, select"));
    const invalid = fields.find((field) => !field.checkValidity());
    if (invalid) invalid.reportValidity();
    return !invalid;
  }

  progress.hidden = false;
  next.addEventListener("click", () => { if (stepIsValid()) show(current + 1); });
  back.addEventListener("click", () => show(current - 1));
  form.addEventListener("keydown", (event) => {
    // Enter moves to the next section instead of submitting too early.
    if (event.key === "Enter" && current < steps.length - 1 && event.target.tagName !== "BUTTON") {
      event.preventDefault();
      next.click();
    }
  });
  show(0);

  // ---- 2. Live price ----------------------------------------------------------
  const total = document.querySelector("[data-quote-total]");
  const detail = document.querySelector("[data-quote-detail]");
  let latest = 0;

  async function refreshQuote() {
    const data = new FormData(form);
    const query = new URLSearchParams();
    for (const name of ["pickup_city", "delivery_city", "size", "service"]) {
      query.set(name, data.get(name) || "");
    }
    if (!query.get("pickup_city") || !query.get("delivery_city")) {
      total.textContent = "—";
      detail.textContent = "Choose the two cities to see the price.";
      return;
    }
    const request = ++latest;
    try {
      const response = await fetch(form.dataset.quoteUrl + "?" + query);
      const quote = await response.json();
      if (request !== latest) return; // a newer choice was made meanwhile
      if (!response.ok) throw new Error(quote.error);
      total.textContent = quote.total;
      detail.textContent = quote.route_label + " delivery, " + quote.eta + ".";
    } catch (error) {
      total.textContent = "—";
      detail.textContent = "The price will be confirmed when you place the order.";
    }
  }

  form.addEventListener("change", refreshQuote);
  refreshQuote();
})();
