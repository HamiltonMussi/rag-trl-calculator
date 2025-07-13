// sw.js  (background service-worker)

let techInfo = {};

chrome.runtime.onMessage.addListener((msg, sender, respond) => {
  if (msg.type === "SET_TECH"){
    techInfo = msg.payload;
    console.log("Tech set", techInfo);
  }
  else if (msg.type === "GET_TECH") respond(techInfo);

  else if (msg.type === "API_FETCH") {
    fetch(msg.url, msg.init)
      .then(async r => ({ ok: r.ok, status: r.status, text: await r.text() }))
      .then(respond)
      .catch(err => respond({ ok: false, error: err.toString() }));
    return true;   // tells Chrome this is async
  }
});