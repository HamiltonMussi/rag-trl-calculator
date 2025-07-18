// sw.js  (background service-worker)

let techInfo = {};
let sessionId = null;

chrome.runtime.onMessage.addListener((msg, sender, respond) => {
  if (msg.type === "SET_TECH"){
    techInfo = msg.payload;
    console.log("Tech set", techInfo);
    // Set technology context when tech info is available
    setTechnologyContext();
  }
  else if (msg.type === "GET_TECH") respond(techInfo);
  else if (msg.type === "GET_SESSION_ID") respond(sessionId);

  else if (msg.type === "API_FETCH") {
    fetch(msg.url, msg.init)
      .then(async r => ({ ok: r.ok, status: r.status, text: await r.text() }))
      .then(respond)
      .catch(err => respond({ ok: false, error: err.toString() }));
    return true;   // tells Chrome this is async
  }
});

async function setTechnologyContext() {
  if (!techInfo.id) return;
  
  try {
    const response = await fetch("http://127.0.0.1:8000/set-technology-context", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ technology_id: techInfo.id })
    });
    
    if (response.ok) {
      const data = await response.json();
      sessionId = data.session_id;
      console.log("Technology context set, session_id:", sessionId);
    } else {
      console.error("Failed to set technology context:", response.status);
    }
  } catch (error) {
    console.error("Error setting technology context:", error);
  }
}