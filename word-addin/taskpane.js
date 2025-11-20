(() => {
  const THEME_KEY = "lectio-theme";

  function setStatus(message) {
    const el = document.getElementById("status");
    if (el) {
      el.textContent = message;
    }
  }

  function renderResults(results) {
    const container = document.getElementById("results");
    if (!container) {
      return;
    }
    container.innerHTML = "";

    if (!results || results.length === 0) {
      const empty = document.createElement("div");
      empty.textContent = "No related paragraphs found.";
      container.appendChild(empty);
      return;
    }

    results.forEach((r) => {
      const item = document.createElement("div");
      item.className = "result-item";

      const meta = document.createElement("div");
      meta.className = "result-meta";
      meta.textContent = `${r.file} — score: ${r.score.toFixed(3)}`;

      const text = document.createElement("div");
      text.className = "result-text";
      text.textContent = r.text;

      item.appendChild(meta);
      item.appendChild(text);
      container.appendChild(item);
    });
  }

  function applyTheme(theme) {
    let effective = theme;
    if (theme === "system" && window.matchMedia) {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      effective = prefersDark ? "dark" : "light";
    }

    document.body.classList.remove("theme-light", "theme-dark");
    document.body.classList.add(effective === "dark" ? "theme-dark" : "theme-light");

    const select = document.getElementById("theme-select");
    if (select && select.value !== theme) {
      select.value = theme;
    }
  }

  function initTheme() {
    let saved = "system";
    try {
      const stored = window.localStorage.getItem(THEME_KEY);
      if (stored === "light" || stored === "dark" || stored === "system") {
        saved = stored;
      }
    } catch (e) {
      // localStorage might not be available; ignore and use default
    }

    applyTheme(saved);

    const select = document.getElementById("theme-select");
    if (select) {
      select.value = saved;
      select.addEventListener("change", () => {
        const value = select.value;
        try {
          window.localStorage.setItem(THEME_KEY, value);
        } catch (e) {
          // ignore
        }
        applyTheme(value);
      });
    }

    if (window.matchMedia) {
      const mq = window.matchMedia("(prefers-color-scheme: dark)");
      const handler = () => {
        let current = "system";
        try {
          const stored = window.localStorage.getItem(THEME_KEY);
          if (stored === "light" || stored === "dark" || stored === "system") {
            current = stored;
          }
        } catch (e) {
          // ignore
        }
        if (current === "system") {
          applyTheme("system");
        }
      };
      if (mq.addEventListener) {
        mq.addEventListener("change", handler);
      } else if (mq.addListener) {
        mq.addListener(handler);
      }
    }
  }

  function analyzeSelection() {
    setStatus("Reading selection...");
    Office.context.document.getSelectedDataAsync(
      Office.CoercionType.Text,
      (asyncResult) => {
        if (asyncResult.status !== Office.AsyncResultStatus.Succeeded) {
          setStatus("Could not read selection.");
          return;
        }

        const text = String(asyncResult.value || "").trim();
        if (!text) {
          setStatus("Select some text in the document first.");
          return;
        }

        setStatus("Searching corpus...");

        fetch("/search", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ query: text, top_k: 5 }),
        })
          .then((resp) => {
            if (!resp.ok) {
              throw new Error(`Backend error (${resp.status})`);
            }
            return resp.json();
          })
          .then((data) => {
            renderResults(data.results || []);
            setStatus("Done.");
          })
          .catch((err) => {
            setStatus(`Error: ${err.message}`);
          });
      }
    );
  }

  Office.onReady(() => {
    initTheme();

    const btn = document.getElementById("analyze-button");
    if (btn) {
      btn.addEventListener("click", analyzeSelection);
    }
    setStatus("Ready. Select text and click the button.");
  });
})();
