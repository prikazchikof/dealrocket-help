(function () {
  function addHeaderActions() {
    var header = document.querySelector(".md-header__inner");
    if (!header || header.querySelector(".dr-header-actions")) return;

    var actions = document.createElement("nav");
    actions.className = "dr-header-actions";
    actions.setAttribute("aria-label", "Ссылки DealRocket");
    actions.innerHTML =
      '<a class="dr-header-action" href="https://dealrocket.ru/app/pricing/">Тарифы</a>' +
      '<a class="dr-header-action dr-header-action--primary" href="https://dealrocket.ru/app/">Открыть DealRocket</a>';
    header.appendChild(actions);
  }

  function bindSearchPrompts() {
    document.querySelectorAll("[data-open-search]").forEach(function (prompt) {
      if (prompt.dataset.bound === "true") return;
      prompt.dataset.bound = "true";
      prompt.addEventListener("click", function () {
        var toggle = document.querySelector('label[for="__search"]');
        if (toggle) toggle.click();
      });
    });
  }

  addHeaderActions();
  bindSearchPrompts();
  if (typeof document$ !== "undefined") {
    document$.subscribe(function () {
      addHeaderActions();
      bindSearchPrompts();
    });
  }
})();
