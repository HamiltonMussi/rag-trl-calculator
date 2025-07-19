// sw.js  (background service-worker)

chrome.runtime.onMessage.addListener((msg, sender, respond) => {
  if (msg.type === "SET_TECH"){
    // Store tech info in chrome.storage.local for persistence
    chrome.storage.local.set({ techInfo: msg.payload }).then(() => {
      console.log("Tech set", msg.payload);
      // Set technology context when tech info is available
      setTechnologyContext(msg.payload);
    });
  }
  else if (msg.type === "GET_TECH") {
    chrome.storage.local.get(['techInfo']).then(stored => {
      respond(stored.techInfo || {});
    });
    return true; // async response
  }
  else if (msg.type === "GET_SESSION_ID") {
    getValidSessionId().then(respond);
    return true; // async response
  }

  else if (msg.type === "API_FETCH") {
    fetch(msg.url, msg.init)
      .then(async r => ({ ok: r.ok, status: r.status, text: await r.text() }))
      .then(respond)
      .catch(err => respond({ ok: false, error: err.toString() }));
    return true;   // tells Chrome this is async
  }
});

async function setTechnologyContext(techInfo = null) {
  // Get techInfo from storage if not provided
  if (!techInfo) {
    const stored = await chrome.storage.local.get(['techInfo']);
    techInfo = stored.techInfo;
  }
  
  if (!techInfo || !techInfo.id) return;
  
  try {
    const response = await fetch("http://127.0.0.1:8000/set-technology-context", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ technology_id: techInfo.id })
    });
    
    if (response.ok) {
      const data = await response.json();
      // Store session data in chrome.storage.local
      await chrome.storage.local.set({
        sessionId: data.session_id,
        technologyId: techInfo.id
      });
      console.log("Technology context set, session_id:", data.session_id);
    } else {
      console.error("Failed to set technology context:", response.status);
    }
  } catch (error) {
    console.error("Error setting technology context:", error);
  }
}

async function getValidSessionId() {
  try {
    // Get stored tech info and session data
    const stored = await chrome.storage.local.get(['techInfo', 'sessionId', 'technologyId']);
    const techInfo = stored.techInfo;
    
    if (!techInfo || !techInfo.id) {
      console.log("No tech info found");
      return null;
    }
    
    // Check if technology changed or no session exists
    if (stored.technologyId !== techInfo.id || !stored.sessionId) {
      console.log("Technology changed or no session, creating new session");
      await setTechnologyContext(techInfo);
      const newStored = await chrome.storage.local.get(['sessionId']);
      return newStored.sessionId;
    }
    
    // Validate existing session with backend
    const isValid = await validateSession(stored.sessionId);
    if (isValid) {
      console.log("Using existing valid session:", stored.sessionId);
      return stored.sessionId;
    } else {
      console.log("Session invalid, creating new session");
      await setTechnologyContext(techInfo);
      const newStored = await chrome.storage.local.get(['sessionId']);
      return newStored.sessionId;
    }
  } catch (error) {
    console.error("Error getting valid session ID:", error);
    return null;
  }
}

async function validateSession(sessionId) {
  // For now, skip validation and assume session is valid
  // The real validation happens when the actual question is sent
  console.log("Skipping session validation, assuming valid:", sessionId);
  return true;
}