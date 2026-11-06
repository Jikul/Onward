/* Spoken callouts: reads new flight messages aloud with the browser's own voice. */
const Voice = (() => {
  let heard = null, on = false, voice = null;
  const pick = () => {
    const vs = speechSynthesis.getVoices();
    voice = vs.find((v) => /en[-_]US/i.test(v.lang) && /natural|online|google/i.test(v.name)) || vs.find((v) => /en[-_]US/i.test(v.lang)) || vs.find((v) => /^en/i.test(v.lang)) || null;
  };
  if ("speechSynthesis" in window) { pick(); speechSynthesis.onvoiceschanged = pick; }
  const clean = (t) => t
    .replace(/\(([^)]*)\)/g, "")
    .replace(/(\d{3})°M/g, (m, d) => d.split("").join(" ") + " magnetic")
    .replace(/°/g, " degrees").replace(/\bnm\b/g, "miles").replace(/\bkt\b/g, "knots").replace(/\bfpm\b/g, "feet per minute")
    .replace(/\bft\b/g, "feet").replace(/\bRWY\b/g, "runway").replace(/\bMSA\b/g, "minimum safe altitude").replace(/\s+/g, " ").trim();
  function say(text, force) {
    if (!("speechSynthesis" in window) || (!on && !force)) return;
    const u = new SpeechSynthesisUtterance(clean(text));
    if (voice) u.voice = voice;
    u.rate = 1.02;
    speechSynthesis.speak(u);
  }
  function feed(msgs) {
    if (!msgs) { heard = null; return; }
    const ids = msgs.map((m) => m.t + m.text);
    if (heard === null) { heard = new Set(ids); return; } // don't read the backlog
    msgs.forEach((m, i) => { if (!heard.has(ids[i])) { heard.add(ids[i]); if (!m.quiet) say(m.text); } });
  }
  return { say, feed, set: (v) => { on = !!v; if (!on && "speechSynthesis" in window) speechSynthesis.cancel(); }, get on() { return on; } };
})();
