function parseSpan(text) {
    // remove line-breaks/spaces
    const cleaned = text.replace(/\s+/g," ").trim();
    const m = cleaned.match(/ID:\s*(\d+)\).*?\/ Projeto (.*?) \/ Org\.: (.*)$/);
    if (!m) return null;
    return {
      id: m[1],
      name: cleaned.split("(ID")[0].trim(),
      project: m[2].trim(),
      org: m[3].trim()
    };
  }
  
  const span = document.querySelector("#select2-itemToSelect-container");
  if (span) {
    const mo = new MutationObserver(() => {
      const info = parseSpan(span.getAttribute("title") || span.textContent);
      if (info) chrome.runtime.sendMessage({type: "SET_TECH", payload: info});
    });
    mo.observe(span, {characterData: true, subtree: true, attributes: true});
    // run once
    const init = parseSpan(span.getAttribute("title") || span.textContent);
    if (init) chrome.runtime.sendMessage({type: "SET_TECH", payload: init});
  }

