#!/usr/bin/env python3
"""Capture REAL footage of the live Veritas app functioning.

No Playwright/Puppeteer (offline box, no installs): we drive headless Chromium
directly over the DevTools Protocol with a stdlib-only websocket client, run a
choreographed click-through of the app (real navigation, real clicks, real
typing, real expand of the proof chain, the live self-draining runs queue), and
record it as a CDP screencast. Frames are reconstructed into true-timing,
constant-fps H.264 clips - one mp4 per beat - in docs/video_build/live/.

Every pixel is the actual web/ app rendering the real ingested data from the
local Postgres mirror of Aurora (identical rows: 3 cases / 2,257 facts / 11
AI-overruled). This is the project functioning, not a slideshow of screenshots.

    python3 docs/capture_live.py            # capture all beats
    SMOKE=1 python3 docs/capture_live.py     # just prove the CDP pipe works
"""
from __future__ import annotations
import base64, json, os, shutil, socket, struct, subprocess, sys, threading, time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.join(HERE, "video_build", "live")
FRAMES = os.path.join(LIVE, "_frames")
os.makedirs(LIVE, exist_ok=True)

BASE = "http://localhost:3000"
DBG_PORT = 9223 + (os.getpid() % 600)   # unique per run; dodge stray chromium
VW, VH, DSF = 1280, 800, 2          # logical viewport; 2x for crisp text
OUT_W, OUT_H = 1920, 1080
BG = "0x070a10"
CHROMIUM = "chromium"
CASE_OPUS = "7f581182-232d-56d4-8016-8e33d55449a0"   # rd01 (opus): 4 overruled

# hero finding ids (verified against the DB)
F_OVERRULED = "F001"   # model: confirmed_malicious -> Veritas: suspicious (gate)
F_CONFIRMED = "F008"   # PsExec/PWDumpX, real proof chain
PIVOT_TERM = "8712"    # a PID present in all 3 cases


# ----------------------------------------------------------------------------
# minimal websocket client (RFC6455, client side) -- stdlib only
# ----------------------------------------------------------------------------
class WS:
    def __init__(self, url: str):
        # ws://host:port/path
        assert url.startswith("ws://")
        hostpart, self.path = url[5:].split("/", 1)
        self.path = "/" + self.path
        self.host, port = hostpart.split(":")
        self.port = int(port)
        self.sock = socket.create_connection((self.host, self.port), timeout=30)
        self.sock.settimeout(30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET {self.path} HTTP/1.1\r\nHost: {self.host}:{self.port}\r\n"
               "Upgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        # read handshake response headers
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(1)
        assert b"101" in buf.split(b"\r\n")[0], buf[:120]
        self._sendlock = threading.Lock()

    def _recvn(self, n: int) -> bytes:
        out = b""
        while len(out) < n:
            chunk = self.sock.recv(n - len(out))
            if not chunk:
                raise ConnectionError("ws closed")
            out += chunk
        return out

    def _recv_one(self):
        """one frame -> (fin, opcode, payload)"""
        b0, b1 = self._recvn(2)
        fin = b0 & 0x80
        opcode = b0 & 0x0F
        masked = b1 & 0x80
        ln = b1 & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", self._recvn(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", self._recvn(8))[0]
        mask = self._recvn(4) if masked else b""
        data = self._recvn(ln) if ln else b""
        if masked:
            data = bytes(d ^ mask[i % 4] for i, d in enumerate(data))
        return fin, opcode, data

    def recv_message(self):
        """assemble (continuation) frames -> full text/binary payload, or
        ('ctl', opcode) for control frames the caller should handle."""
        fin, opcode, data = self._recv_one()
        if opcode in (0x8, 0x9, 0xA):
            return ("ctl", opcode, data)
        payload = data
        while not fin:
            fin, op2, d2 = self._recv_one()
            payload += d2
        return ("msg", opcode, payload)

    def send_text(self, s: str):
        data = s.encode()
        mask = os.urandom(4)
        masked = bytes(d ^ mask[i % 4] for i, d in enumerate(data))
        n = len(data)
        if n < 126:
            hdr = struct.pack(">BB", 0x81, 0x80 | n)
        elif n < 65536:
            hdr = struct.pack(">BBH", 0x81, 0x80 | 126, n)
        else:
            hdr = struct.pack(">BBQ", 0x81, 0x80 | 127, n)
        with self._sendlock:
            self.sock.sendall(hdr + mask + masked)

    def send_pong(self, data: bytes):
        mask = os.urandom(4)
        masked = bytes(d ^ mask[i % 4] for i, d in enumerate(data))
        hdr = struct.pack(">BB", 0x8A, 0x80 | len(data))
        with self._sendlock:
            self.sock.sendall(hdr + mask + masked)


# ----------------------------------------------------------------------------
# CDP wrapper over the websocket
# ----------------------------------------------------------------------------
class CDP:
    def __init__(self, ws: WS):
        self.ws = ws
        self.sid = None              # attached page session (flatten mode)
        self._id = 0
        self._idlock = threading.Lock()
        self._pending = {}           # id -> [event, result]
        self._frames = []            # (t, jpeg bytes) for active screencast
        self._recording = False
        self._sid = None
        self._t0 = 0.0
        self._stop = False
        self.th = threading.Thread(target=self._loop, daemon=True)
        self.th.start()

    def _loop(self):
        while not self._stop:
            try:
                kind, opcode, payload = self.ws.recv_message()
            except Exception:
                break
            if kind == "ctl":
                if opcode == 0x9:           # ping -> pong
                    self.ws.send_pong(payload)
                continue
            try:
                msg = json.loads(payload.decode("utf-8", "replace"))
            except Exception:
                continue
            if "id" in msg:
                slot = self._pending.get(msg["id"])
                if slot:
                    slot[1] = msg
                    slot[0].set()
            else:
                m = msg.get("method")
                if m == "Page.screencastFrame":
                    p = msg["params"]
                    if self._recording:
                        self._frames.append((time.monotonic() - self._t0,
                                             base64.b64decode(p["data"])))
                    # must ack or chromium stops sending frames
                    self.send("Page.screencastFrameAck",
                              {"sessionId": p["sessionId"]}, wait=False)

    def send(self, method, params=None, wait=True, timeout=30):
        with self._idlock:
            self._id += 1
            mid = self._id
        payload = {"id": mid, "method": method, "params": params or {}}
        # page-level commands ride the attached session; Target/Browser stay top-level
        if self.sid and not method.startswith(("Target.", "Browser.")):
            payload["sessionId"] = self.sid
        if wait:
            ev = threading.Event()
            self._pending[mid] = [ev, None]
        self.ws.send_text(json.dumps(payload))
        if not wait:
            return None
        if not ev.wait(timeout):
            raise TimeoutError(method)
        res = self._pending.pop(mid)[1]
        if "error" in res:
            raise RuntimeError(f"{method}: {res['error']}")
        return res.get("result", {})

    def close(self):
        self._stop = True

    def attach_page(self):
        """new headless has no ready 'page' target: create one and attach with
        flatten so we multiplex over the single browser websocket."""
        t = self.send("Target.createTarget", {"url": "about:blank"})
        tid = t["targetId"]
        a = self.send("Target.attachToTarget", {"targetId": tid, "flatten": True})
        self.sid = a["sessionId"]

    # ---- high-level helpers ----
    def evaluate(self, expr, await_promise=False):
        r = self.send("Runtime.evaluate", {
            "expression": expr, "returnByValue": True,
            "awaitPromise": await_promise})
        return r.get("result", {}).get("value")

    def navigate(self, url):
        self.send("Page.navigate", {"url": url})
        # wait for the document to be interactive + a beat for data/paint
        for _ in range(120):
            try:
                st = self.evaluate("document.readyState")
            except Exception:
                st = None
            if st in ("interactive", "complete"):
                break
            time.sleep(0.1)
        time.sleep(1.2)

    def wait_path(self, contains, tries=120):
        for _ in range(tries):
            try:
                p = self.evaluate("location.pathname + location.search")
            except Exception:
                p = ""
            if contains in (p or ""):
                return True
            time.sleep(0.1)
        return False

    def rect(self, selector):
        js = ("(()=>{const e=document.querySelector(%s);if(!e)return null;"
              "const r=e.getBoundingClientRect();"
              "return {x:r.x,y:r.y,w:r.width,h:r.height};})()" % json.dumps(selector))
        return self.evaluate(js)

    def move(self, x, y, steps=22):
        # ease the cursor so the injected pointer glides
        x0 = getattr(self, "_mx", x)
        y0 = getattr(self, "_my", y)
        for i in range(1, steps + 1):
            t = i / steps
            t = t * t * (3 - 2 * t)            # smoothstep
            cx, cy = x0 + (x - x0) * t, y0 + (y - y0) * t
            self.send("Input.dispatchMouseEvent",
                      {"type": "mouseMoved", "x": cx, "y": cy}, wait=False)
            time.sleep(0.012)
        self._mx, self._my = x, y

    def click_xy(self, x, y):
        self.move(x, y)
        time.sleep(0.18)
        for typ in ("mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent",
                      {"type": typ, "x": x, "y": y, "button": "left",
                       "clickCount": 1}, wait=False)
            time.sleep(0.05)

    def click(self, selector, settle=0.4):
        r = self.rect(selector)
        if not r:
            raise RuntimeError(f"no element {selector}")
        self.click_xy(r["x"] + r["w"] / 2, r["y"] + min(r["h"] / 2, 20))
        time.sleep(settle)

    def scroll_to(self, y, dur=0.9):
        self.evaluate(f"window.scrollTo({{top:{y},behavior:'smooth'}})")
        time.sleep(dur)

    def scroll_into(self, selector, block="center", dur=0.9):
        self.evaluate("(()=>{const e=document.querySelector(%s);"
                      "if(e)e.scrollIntoView({behavior:'smooth',block:%s});})()"
                      % (json.dumps(selector), json.dumps(block)))
        time.sleep(dur)

    def type_into(self, selector, text, cps=14):
        self.click(selector, settle=0.2)
        for ch in text:
            self.send("Input.insertText", {"text": ch}, wait=False)
            time.sleep(1.0 / cps)
        time.sleep(0.3)

    # ---- screencast capture ----
    def start_cast(self):
        self._frames = []
        self._t0 = time.monotonic()
        self._recording = True
        self.send("Page.startScreencast", {
            "format": "jpeg", "quality": 72,
            "maxWidth": 1920, "maxHeight": 1200, "everyNthFrame": 1})

    def stop_cast(self):
        self._recording = False
        try:
            self.send("Page.stopScreencast")
        except Exception:
            pass
        return list(self._frames)


CURSOR_JS = r"""
(function(){
  if (window.__vcur) return;
  window.__vcur = true;
  function mk(){
    if (document.getElementById('__vcursor')) return;
    var c = document.createElement('div');
    c.id='__vcursor';
    c.style.cssText='position:fixed;left:-50px;top:-50px;width:22px;height:22px;'+
      'margin:-3px 0 0 -3px;z-index:2147483647;pointer-events:none;'+
      'background:radial-gradient(circle at 8px 8px,#fff 0,#fff 3px,rgba(249,115,22,.95) 4px,rgba(249,115,22,.0) 12px);'+
      'border-radius:50%;filter:drop-shadow(0 0 6px rgba(249,115,22,.8));transition:transform .05s';
    (document.documentElement||document.body).appendChild(c);
    var ring=document.createElement('div');
    ring.id='__vring';
    ring.style.cssText='position:fixed;z-index:2147483646;pointer-events:none;'+
      'width:8px;height:8px;border:2px solid rgba(249,115,22,.9);border-radius:50%;opacity:0;transform:translate(-50%,-50%)';
    (document.documentElement||document.body).appendChild(ring);
    window.addEventListener('mousemove',function(e){
      c.style.left=e.clientX+'px'; c.style.top=e.clientY+'px';
      ring.style.left=e.clientX+'px'; ring.style.top=e.clientY+'px';
    },true);
    window.addEventListener('mousedown',function(e){
      ring.style.transition='none';ring.style.opacity='1';
      ring.style.width='8px';ring.style.height='8px';
      requestAnimationFrame(function(){
        ring.style.transition='all .4s ease-out';
        ring.style.width='40px';ring.style.height='40px';ring.style.opacity='0';
      });
    },true);
  }
  if (document.readyState!=='loading') mk();
  else document.addEventListener('DOMContentLoaded',mk);
  // Next.js SPA nav keeps the document; keep re-ensuring the node exists.
  setInterval(mk, 700);
})();
"""


# ----------------------------------------------------------------------------
# chromium launch + target discovery
# ----------------------------------------------------------------------------
def launch_chromium():
    profile = os.path.join(LIVE, "_profile")
    shutil.rmtree(profile, ignore_errors=True)
    os.makedirs(profile, exist_ok=True)
    args = [CHROMIUM, "--headless=new", "--no-sandbox", "--hide-scrollbars",
            f"--remote-debugging-port={DBG_PORT}",
            f"--user-data-dir={profile}",
            "--remote-allow-origins=*",
            f"--window-size={VW},{VH}",
            f"--force-device-scale-factor={DSF}",
            "--no-first-run", "--no-default-browser-check",
            "--disable-gpu", "--default-background-color=ff070a10",
            "about:blank"]
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # wait for the BROWSER endpoint (always present); we create a page ourselves
    ws_url = None
    for _ in range(80):
        try:
            data = urllib.request.urlopen(
                f"http://127.0.0.1:{DBG_PORT}/json/version", timeout=2).read()
            ws_url = json.loads(data).get("webSocketDebuggerUrl")
            if ws_url:
                break
        except Exception:
            pass
        time.sleep(0.5)
    if not ws_url:
        proc.kill()
        raise RuntimeError("chromium devtools never came up")
    return proc, ws_url


def setup(cdp: CDP):
    cdp.attach_page()
    cdp.send("Page.enable")
    cdp.send("Runtime.enable")
    cdp.send("DOM.enable")
    cdp.send("Emulation.setDeviceMetricsOverride", {
        "width": VW, "height": VH, "deviceScaleFactor": DSF, "mobile": False})
    cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": CURSOR_JS})


# ----------------------------------------------------------------------------
# frames -> true-timing constant-fps mp4
# ----------------------------------------------------------------------------
def encode(frames, name, fps=30, tail=0.6):
    if not frames:
        print(f"  !! no frames for {name}", file=sys.stderr)
        return None
    fdir = os.path.join(FRAMES, name)
    if os.path.isdir(fdir):
        for f in os.listdir(fdir):
            os.remove(os.path.join(fdir, f))
    os.makedirs(fdir, exist_ok=True)
    listpath = os.path.join(fdir, "list.txt")
    lines = []
    for i, (t, jpg) in enumerate(frames):
        fn = os.path.join(fdir, f"{i:05d}.jpg")
        with open(fn, "wb") as fh:
            fh.write(jpg)
        if i < len(frames) - 1:
            d = max(0.012, frames[i + 1][0] - t)
        else:
            d = tail
        lines.append(f"file '{fn}'")
        lines.append(f"duration {d:.3f}")
    lines.append(f"file '{os.path.join(fdir, f'{len(frames)-1:05d}.jpg')}'")
    with open(listpath, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    out = os.path.join(LIVE, f"{name}.mp4")
    vf = (f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=decrease,"
          f"pad={OUT_W}:{OUT_H}:(ow-iw)/2:(oh-ih)/2:color={BG},"
          f"fps={fps},format=yuv420p")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listpath,
           "-vf", vf, "-r", str(fps), "-c:v", "libx264", "-preset", "slow",
           "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:], file=sys.stderr)
        return None
    dur = frames[-1][0] + tail
    print(f"  -> {name}.mp4  ({len(frames)} frames, ~{dur:.1f}s)")
    return out


# ----------------------------------------------------------------------------
# the choreography -- one function per beat, each returns frames
# ----------------------------------------------------------------------------
def beat(cdp, fn, name):
    cdp.start_cast()
    time.sleep(0.4)
    fn()
    time.sleep(0.5)
    frames = cdp.stop_cast()
    return encode(frames, name)


def b_intro(cdp):
    """Longer, continuously-moving opener so the live app is on screen from
    frame one while the title + problem narration plays over it (footage-first)."""
    cdp.navigate(BASE + "/")
    cdp.move(640, 130, steps=10)
    time.sleep(1.4)
    cdp.move(300, 250)                     # across the stat tiles
    time.sleep(1.5)
    cdp.move(780, 250)
    time.sleep(1.4)
    cdp.scroll_to(360, dur=1.3)            # down to the real case cards
    cdp.move(360, 470)
    time.sleep(1.7)
    cdp.move(780, 480)                     # hover the other case
    time.sleep(1.6)
    cdp.scroll_to(120, dur=1.1)            # back up past the headline
    cdp.move(420, 210)
    time.sleep(1.7)
    cdp.scroll_to(360, dur=1.1)
    cdp.move(360, 470)
    time.sleep(1.8)


def b_landing(cdp):
    cdp.navigate(BASE + "/")
    cdp.move(640, 120, steps=8)
    time.sleep(1.3)
    cdp.scroll_to(0)
    cdp.move(300, 250)
    time.sleep(1.6)                       # stats row
    cdp.scroll_to(360, dur=1.1)           # down to the case cards
    cdp.move(360, 470)
    time.sleep(1.8)


def b_dashboard(cdp):
    cdp.navigate(BASE + "/")
    cdp.scroll_to(360, dur=0.8)
    # click the rd01 (opus) case card
    sel = f'a[href="/case/{CASE_OPUS}"]'
    cdp.scroll_into(sel, dur=0.7)
    time.sleep(0.4)
    cdp.click(sel, settle=0.4)
    cdp.wait_path(f"/case/{CASE_OPUS}")
    time.sleep(1.4)
    cdp.scroll_to(0)
    cdp.move(360, 200)
    time.sleep(1.8)                       # verdict banner + evidence chip
    cdp.scroll_to(150, dur=0.9)
    cdp.move(360, 360)
    time.sleep(1.8)                       # the "overruled 4x" highlight


def b_overrule(cdp):
    cdp.navigate(BASE + f"/case/{CASE_OPUS}/finding/{F_OVERRULED}")
    cdp.scroll_to(0)
    cdp.move(360, 200)
    time.sleep(2.0)                       # title + verdict pills
    cdp.scroll_into("section.border-brand\\/30", dur=0.9)
    cdp.move(700, 360)
    time.sleep(2.6)                       # the overrule panel: model -> code + gate


def b_proof(cdp):
    cdp.navigate(BASE + f"/case/{CASE_OPUS}/finding/{F_CONFIRMED}")
    cdp.scroll_to(0)
    time.sleep(1.0)
    cdp.scroll_into("details", dur=0.9)   # the proof chain
    time.sleep(1.2)
    # expand the first proof to reveal the raw forensic-tool output
    r = cdp.rect("details summary")
    if r:
        cdp.click_xy(r["x"] + 40, r["y"] + r["h"] / 2)
        time.sleep(0.4)
        cdp.scroll_into("details[open] pre", dur=0.8)
        time.sleep(2.2)                   # raw tool output on screen
    # expand a second proof
    cdp.evaluate("(()=>{const d=document.querySelectorAll('details')[1];"
                 "if(d){d.scrollIntoView({behavior:'smooth',block:'center'});}})()")
    time.sleep(0.6)
    r2 = cdp.rect("details:nth-of-type(2) summary")
    if r2:
        cdp.click_xy(r2["x"] + 40, r2["y"] + r2["h"] / 2)
        time.sleep(1.8)


def b_pivot(cdp):
    cdp.navigate(BASE + "/pivot")
    cdp.scroll_to(0)
    time.sleep(1.2)
    cdp.type_into('input[name="q"]', PIVOT_TERM, cps=7)
    time.sleep(0.5)
    cdp.click('form[action="/pivot"] button', settle=0.3)
    cdp.wait_path("q=" + PIVOT_TERM)
    time.sleep(1.6)
    cdp.scroll_to(150, dur=0.9)
    cdp.move(500, 430)
    time.sleep(2.2)                       # the cross-case rows (3 cases)


def b_runs(cdp):
    # stage authentically through the app's OWN endpoints (in-page fetch):
    # enqueue two runs, then advance one several steps so the queue is live.
    cdp.navigate(BASE + "/runs")
    cdp.evaluate(
        "(async()=>{"
        "await fetch('/api/runs',{method:'POST',headers:{'content-type':'application/json'},"
        "body:JSON.stringify({case_name:'acme-dc01 triage',evidence:'run-rd01-opus-20260611'})});"
        "await fetch('/api/runs',{method:'POST',headers:{'content-type':'application/json'},"
        "body:JSON.stringify({case_name:'falcon-ir nodeC',evidence:'run-rd01-golden-20260611'})});"
        "for(let i=0;i<7;i++){await fetch('/api/worker/tick',{method:'POST'});}"
        "return 'staged';})()", await_promise=True)
    cdp.navigate(BASE + "/runs")          # reload so SSR shows the live queue
    cdp.scroll_to(0)
    time.sleep(1.6)
    # queue a fresh investigation on camera
    cdp.type_into('input[placeholder^="e.g. acme"]', "ir-bravo host17", cps=12)
    time.sleep(0.3)
    cdp.click('form button', settle=0.5)
    time.sleep(2.0)
    cdp.scroll_to(120, dur=0.8)
    time.sleep(3.0)                       # polling drives the bars (live tick)


def smoke(cdp):
    v = cdp.send("Browser.getVersion")
    print("Browser:", v.get("product"))
    cdp.navigate(BASE + "/")
    title = cdp.evaluate("document.title")
    print("title:", title)
    cdp.start_cast()
    cdp.move(640, 400)
    time.sleep(1.5)
    frames = cdp.stop_cast()
    print(f"captured {len(frames)} frames")
    if frames:
        sizes = [len(j) for _, j in frames]
        print(f"frame bytes: min={min(sizes)} max={max(sizes)} avg={sum(sizes)//len(sizes)}")
        encode(frames, "_smoke")


BEATS = [
    (b_intro, "beat0_intro"),
    (b_landing, "beat1_landing"),
    (b_dashboard, "beat2_dashboard"),
    (b_overrule, "beat3_overrule"),
    (b_proof, "beat4_proof"),
    (b_pivot, "beat5_pivot"),
    (b_runs, "beat6_runs"),
]


def main():
    proc, ws_url = launch_chromium()
    print("devtools:", ws_url)
    cdp = CDP(WS(ws_url))
    try:
        setup(cdp)
        if os.environ.get("SMOKE"):
            smoke(cdp)
            return
        only = os.environ.get("ONLY")
        for fn, name in BEATS:
            if only and name not in only:
                continue
            print(f"== {name} ==")
            beat(cdp, lambda fn=fn: fn(cdp), name)
    finally:
        cdp.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
