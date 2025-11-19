(() => {
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
    const btn = document.getElementById("analyze-button");
    if (btn) {
      btn.addEventListener("click", analyzeSelection);
    }
    setStatus("Ready. Select text and click the button.");
  });
})();

