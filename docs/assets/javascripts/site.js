(function () {
  function trustedSupportOrigin(value) {
    try {
      var candidate = new URL(value);
      var localHost = candidate.hostname === "support.dealrocket.localhost" ||
        candidate.hostname === "support.dealrocket.lvh.me";
      if (candidate.origin !== value) return "https://support.dealrocket.ru";
      if (candidate.origin === "https://support.dealrocket.ru") return candidate.origin;
      if (candidate.protocol === "http:" && localHost) return candidate.origin;
    } catch (_) { /* Use the production origin for malformed test overrides. */ }
    return "https://support.dealrocket.ru";
  }
  var SUPPORT_ORIGIN = trustedSupportOrigin(
    document.documentElement.dataset.supportOrigin || "https://support.dealrocket.ru"
  );
  var SUPPORT_STATE_KEY = "dealrocket-support-widget-open";

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

  function supportPageContext(pathname) {
    if (pathname.indexOf("/billing/") === 0) return "billing";
    if (pathname === "/results/lists/") return "lists";
    if (pathname === "/results/export/") return "export";
    if (pathname === "/results/contacts/") return "contacts";
    if (pathname.indexOf("/search/") === 0) return "search";
    if (pathname === "/start/preparation/" || pathname === "/start/why-dealrocket/") return "search";
    return "";
  }

  function ensureSupportWidget() {
    var existing = document.querySelector(".dr-support-widget");
    if (existing) return existing.supportController;

    var root = document.createElement("div");
    root.className = "dr-support-widget";
    root.innerHTML =
      '<button class="dr-support-widget__launcher" type="button" aria-label="Открыть чат поддержки" aria-haspopup="dialog" aria-expanded="false">' +
        '<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M5 5.75A3.75 3.75 0 0 1 8.75 2h6.5A3.75 3.75 0 0 1 19 5.75v5.5A3.75 3.75 0 0 1 15.25 15H11l-4.7 4.08A.8.8 0 0 1 5 18.48V15.8a3.76 3.76 0 0 1-2-3.3V5.75A3.75 3.75 0 0 1 5 5.75Z"/></svg>' +
      '</button>' +
      '<section class="dr-support-widget__panel" role="dialog" aria-label="Чат поддержки DealRocket" hidden>' +
        '<div class="dr-support-widget__fallback" hidden>' +
          '<button type="button" class="dr-support-widget__fallback-close" aria-label="Закрыть чат">×</button>' +
          '<p>Не удалось открыть компактный чат.</p>' +
          '<a href="#" target="_blank" rel="noopener noreferrer">Открыть полный чат ↗</a>' +
        '</div>' +
      '</section>';
    document.body.appendChild(root);

    var launcher = root.querySelector(".dr-support-widget__launcher");
    var panel = root.querySelector(".dr-support-widget__panel");
    var fallback = root.querySelector(".dr-support-widget__fallback");
    var fallbackClose = root.querySelector(".dr-support-widget__fallback-close");
    fallback.querySelector("a").href = SUPPORT_ORIGIN + "/";
    var iframe = null;
    var ready = false;
    var readyTimer = null;

    function context() { return supportPageContext(location.pathname); }
    function updateLauncherOffset() {
      var consent = document.querySelector(".md-consent__inner");
      var bottom = 24;
      if (consent) {
        var style = window.getComputedStyle(consent);
        var bounds = consent.getBoundingClientRect();
        if (style.display !== "none" && style.visibility !== "hidden" && bounds.height > 0) {
          var consentBottom = Number.parseFloat(style.bottom);
          bottom = Math.max(bottom, bounds.height + (Number.isFinite(consentBottom) ? consentBottom : 0) + 12);
        }
      }
      root.style.setProperty("--dr-support-launcher-bottom", bottom + "px");
    }
    function setMobileState() {
      var mobile = window.matchMedia("(max-width: 720px)").matches;
      panel.setAttribute("aria-modal", mobile ? "true" : "false");
      document.body.classList.toggle("dr-support-widget-open", mobile && !panel.hidden);
    }
    function showFallback() {
      fallback.hidden = false;
      if (iframe) iframe.hidden = true;
    }
    function sendContext() {
      if (!iframe || !iframe.contentWindow) return;
      iframe.contentWindow.postMessage({type: "dr-support-context", page: context()}, SUPPORT_ORIGIN);
    }
    function createFrame() {
      iframe = document.createElement("iframe");
      iframe.className = "dr-support-widget__frame";
      iframe.title = "Помощник DealRocket";
      iframe.referrerPolicy = "no-referrer";
      iframe.setAttribute("sandbox", "allow-scripts allow-forms allow-same-origin allow-popups allow-popups-to-escape-sandbox");
      var source = SUPPORT_ORIGIN + "/widget?page=" + encodeURIComponent(context());
      if (SUPPORT_ORIGIN !== "https://support.dealrocket.ru") {
        source += "&parent_origin=" + encodeURIComponent(location.origin);
      }
      iframe.src = source;
      iframe.addEventListener("load", sendContext);
      panel.insertBefore(iframe, fallback);
      readyTimer = window.setTimeout(showFallback, 10000);
    }
    function openWidget() {
      if (!iframe) createFrame();
      panel.hidden = false;
      root.classList.add("dr-support-widget--open");
      launcher.setAttribute("aria-expanded", "true");
      sessionStorage.setItem(SUPPORT_STATE_KEY, "true");
      setMobileState();
      sendContext();
      if (ready) iframe.focus();
    }
    function closeWidget() {
      panel.hidden = true;
      root.classList.remove("dr-support-widget--open");
      launcher.setAttribute("aria-expanded", "false");
      sessionStorage.setItem(SUPPORT_STATE_KEY, "false");
      setMobileState();
      launcher.focus();
    }
    function toggleWidget() {
      if (panel.hidden) openWidget();
      else closeWidget();
    }

    launcher.addEventListener("click", toggleWidget);
    fallbackClose.addEventListener("click", closeWidget);
    window.addEventListener("resize", function () {
      setMobileState();
      updateLauncherOffset();
    });
    window.addEventListener("message", function (event) {
      if (event.origin !== SUPPORT_ORIGIN || !iframe || event.source !== iframe.contentWindow) return;
      if (event.data && event.data.type === "dr-support-ready") {
        ready = true;
        window.clearTimeout(readyTimer);
        fallback.hidden = true;
        iframe.hidden = false;
        if (!panel.hidden) iframe.focus();
      } else if (event.data && event.data.type === "dr-support-close") {
        closeWidget();
      }
    });
    document.addEventListener("keydown", function (event) {
      var mobile = window.matchMedia("(max-width: 720px)").matches;
      var widgetFocused = document.activeElement === iframe || root.contains(document.activeElement);
      if (event.key === "Escape" && !panel.hidden && (mobile || widgetFocused)) {
        event.preventDefault();
        closeWidget();
      }
    });

    var consent = document.querySelector(".md-consent");
    if (consent) {
      new MutationObserver(updateLauncherOffset).observe(consent, {
        attributes: true,
        childList: true,
        subtree: true,
      });
      if (window.ResizeObserver) new ResizeObserver(updateLauncherOffset).observe(consent);
    }
    new MutationObserver(updateLauncherOffset).observe(document.body, {
      attributes: true,
      attributeFilter: ["class", "hidden"],
      childList: true,
      subtree: true,
    });
    window.requestAnimationFrame(updateLauncherOffset);
    updateLauncherOffset();

    root.supportController = {sendContext: sendContext, updateLauncherOffset: updateLauncherOffset};
    if (sessionStorage.getItem(SUPPORT_STATE_KEY) === "true") openWidget();
    return root.supportController;
  }

  function updateSupportWidget() {
    var controller = ensureSupportWidget();
    controller.sendContext();
    controller.updateLauncherOffset();
  }

  addHeaderActions();
  bindSearchPrompts();
  decorateExternalNavLinks();
  updateSupportWidget();
  if (typeof document$ !== "undefined") {
    document$.subscribe(function () {
      addHeaderActions();
      bindSearchPrompts();
      decorateExternalNavLinks();
      updateSupportWidget();
    });
  }
})();
