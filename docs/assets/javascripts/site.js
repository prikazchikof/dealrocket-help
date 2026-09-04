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

  function decorateExternalNavLinks() {
    var externalLinks = [
      "https://dealrocket.ru/how_to/",
      "https://dealrocket.ru/news/",
    ];

    document.querySelectorAll(".md-nav__link").forEach(function (link) {
      if (!externalLinks.includes(link.href)) return;

      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.classList.add("dr-external-nav-link");
      link.setAttribute("aria-label", link.textContent.trim() + " — откроется в новой вкладке");

      if (!link.querySelector(".dr-external-nav-link__icon")) {
        var icon = document.createElement("span");
        icon.className = "dr-external-nav-link__icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = "↗";
        link.appendChild(icon);
      }
    });
  }

  addHeaderActions();
  bindSearchPrompts();
  decorateExternalNavLinks();
  if (typeof document$ !== "undefined") {
    document$.subscribe(function () {
      addHeaderActions();
      bindSearchPrompts();
      decorateExternalNavLinks();
    });
  }
})();
