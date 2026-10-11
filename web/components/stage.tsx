"use client";

/**
 * Thesis
 * Metaphor — a week of search noise is pressed into one card.
 * Hero material — the Teams card. Scroll breaks it into cells; Slack shares the later seam.
 * Playhead — scroll progress is the press. Noise and the card lose their detail together.
 * Ceremony — "Read the guide" commits, a paper wave covers, then the route changes.
 * Still — reduced motion and phones show the claim, both cards, and the steps already resolved.
 */

import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent, type PointerEvent as ReactPointerEvent } from "react";

import "./stage.css";
import { DiagnosticsDrawer } from "@/components/diagnostics-drawer";
import { PaperPress } from "@/components/paper-press";
import { RunDrawer } from "@/components/run-drawer";

const GUIDE_HREF = "/guide";
const GITHUB_HREF = "https://github.com/Adit-Jain-srm/SerpApi_Track1";

const NOISE = [
  "10 new AI tools this week",
  "Top 20 copilots",
  "Best AI tools roundup",
  "Tools launched this week",
];

const STEPS = [
  {
    name: "A date window, not a hope",
    text: "Google web search takes SerpApi’s tbs=qdr:dN. Google News takes after:YYYY-MM-DD. Both stay inside the days you pass.",
  },
  {
    name: "Two engines, one list",
    text: "Web and news run together. The same URL collapses to one row. When the dates disagree, the news date wins.",
  },
  {
    name: "Articles point at products",
    text: "A launch post that names one product homepage is fetched next. The digest keeps that homepage. A listicle that names several products is dropped.",
  },
  {
    name: "A card, not a paragraph",
    text: "Each kept page becomes title, audience, summary, features, pricing, and source. The console prints it. Slack or Teams can post it.",
  },
];

const FAILURES = [
  ["One engine fails.", "The other engine’s rows are kept. The run continues."],
  ["Both engines fail.", "The process exits with an error. It does not print an empty success."],
  ["A page returns 403, or robots.txt says no.", "That URL is skipped. The rest of the batch continues."],
  ["The title is already a list.", "“10 new AI tools” is dropped before fetch. One named product site is fetched next."],
  ["Slack or Teams is unset.", "That delivery is skipped. The console still prints the cards."],
  ["Dry run.", "Search and compare only. No fetch, no extraction, no post."],
];

function cinematic(): boolean {
  // A pinned film clips the card, the stack, and the run log on a normal window.
  return false;
}

function easeInOut(t: number): number {
  return t < 0.5 ? 2 * t * t : 1 - ((-2 * t + 2) ** 2) / 2;
}

const GLYPHS = "█▓▒░•";
const cipherBuffer = typeof document === "undefined" ? null : document.createElement("canvas");

function cellHash(x: number, y: number): number {
  const value = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return value - Math.floor(value);
}

function paintCipher(canvas: HTMLCanvasElement, img: HTMLImageElement, press: number) {
  const ctx = canvas.getContext("2d");
  if (!ctx || !cipherBuffer || !img.complete || img.naturalWidth === 0) return;
  const rect = canvas.getBoundingClientRect();
  if (rect.width < 2 || rect.height < 2) return;
  const coarse = window.matchMedia("(pointer: coarse)").matches;
  const dpr = Math.min(window.devicePixelRatio || 1, coarse ? 1 : 1.25);
  const width = Math.max(1, Math.round(rect.width * dpr));
  const height = Math.max(1, Math.round(rect.height * dpr));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  if (press <= 0.02) {
    ctx.clearRect(0, 0, width, height);
    canvas.style.opacity = "0";
    return;
  }
  const eased = press * press;
  const cols = Math.max(14, Math.round(150 - eased * 136));
  const rows = Math.max(8, Math.round((cols * height) / width));
  cipherBuffer.width = cols;
  cipherBuffer.height = rows;
  const buffer = cipherBuffer.getContext("2d");
  if (!buffer) return;
  const ratio = img.naturalWidth / img.naturalHeight;
  const frame = cols / rows;
  let sx = 0;
  let sy = 0;
  let sw = img.naturalWidth;
  let sh = img.naturalHeight;
  if (ratio > frame) {
    sw = img.naturalHeight * frame;
    sx = (img.naturalWidth - sw) / 2;
  } else {
    sh = img.naturalWidth / frame;
    sy = (img.naturalHeight - sh) / 2;
  }
  buffer.drawImage(img, sx, sy, sw, sh, 0, 0, cols, rows);
  const pixels = buffer.getImageData(0, 0, cols, rows);
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      if (cellHash(col, row) > eased * 0.22) continue;
      const index = (row * cols + col) * 4;
      pixels.data[index] = 168;
      pixels.data[index + 1] = 52;
      pixels.data[index + 2] = 42;
      pixels.data[index + 3] = 255;
    }
  }
  buffer.putImageData(pixels, 0, 0);
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, width, height);
  ctx.drawImage(cipherBuffer, 0, 0, cols, rows, 0, 0, width, height);
  canvas.style.opacity = String(Math.min(1, (press - 0.02) / 0.18));
}

function censorLabel(el: HTMLElement, target: string) {
  let frame = 0;
  const id = window.setInterval(() => {
    frame += 1;
    const resolved = Math.floor((frame / 11) * target.length);
    let out = "";
    for (let i = 0; i < target.length; i += 1) {
      out += i < resolved ? GLYPHS[(Math.random() * GLYPHS.length) | 0] : target[i];
    }
    el.textContent = out;
    if (frame >= 11) {
      window.clearInterval(id);
      el.textContent = GLYPHS[0].repeat(target.length);
    }
  }, 38);
}

export function Stage() {
  const rootRef = useRef<HTMLDivElement>(null);
  const spacerRef = useRef<HTMLDivElement>(null);
  const heroRef = useRef<HTMLElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const outroRef = useRef<HTMLElement>(null);
  const waveRef = useRef<SVGSVGElement>(null);
  const plateRef = useRef<HTMLImageElement>(null);
  const cipherRef = useRef<HTMLCanvasElement>(null);
  const cursorRef = useRef<HTMLDivElement>(null);
  const leaving = useRef(false);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [diagnosticStatus, setDiagnosticStatus] = useState<"checking" | "operational" | "degraded">("checking");

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/diagnostics", { signal: controller.signal, cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<{ status?: "operational" | "degraded" }>;
      })
      .then((result) => setDiagnosticStatus(result.status === "operational" ? "operational" : "degraded"))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setDiagnosticStatus("degraded");
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const root = rootRef.current;
    const spacer = spacerRef.current;
    const hero = heroRef.current;
    const panel = panelRef.current;
    const wrap = wrapRef.current;
    const outro = outroRef.current;
    const wave = waveRef.current;
    if (!root || !spacer || !hero || !panel || !wrap || !outro || !wave) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const narrow = window.matchMedia("(max-width: 800px)");
    const coarse = window.matchMedia("(pointer: coarse)");
    let raf = 0;
    let lastW = window.innerWidth;
    let ticker = 0;
    let idle = 0;
    let idleOn = false;
    const plate = plateRef.current;
    const cipher = cipherRef.current;
    const cursor = cursorRef.current;

    const clearStage = () => {
      cancelAnimationFrame(ticker);
      spacer.style.height = "";
      for (const el of [hero, panel, wrap, outro]) {
        el.style.transform = "";
        el.style.visibility = "";
        el.style.opacity = "";
        el.style.pointerEvents = "";
        el.removeAttribute("inert");
      }
      hero.style.removeProperty("--press");
      wrap.querySelectorAll<HTMLElement>("[data-scene]").forEach((scene) => {
        scene.style.removeProperty("--sp");
        const pin = scene.querySelector<HTMLElement>("[data-pin]");
        if (!pin) return;
        pin.style.transform = "";
        pin.style.opacity = "";
      });
    };

    const noiseLines = () => Array.from(hero.querySelectorAll<HTMLElement>("[data-line]"));
    const restoreNoise = () => {
      noiseLines().forEach((line) => {
        line.textContent = line.dataset.line ?? "";
      });
    };
    const stopIdle = () => {
      window.clearInterval(idle);
      idle = 0;
      idleOn = false;
      restoreNoise();
    };
    const startIdle = () => {
      if (idleOn || reduced.matches) return;
      idleOn = true;
      let index = 0;
      let frame = 0;
      idle = window.setInterval(() => {
        const lines = noiseLines();
        if (!lines.length) return;
        const line = lines[index % lines.length];
        const target = line.dataset.line ?? "";
        frame += 1;
        const resolved = Math.floor((frame / 11) * target.length);
        let out = "";
        for (let i = 0; i < target.length; i += 1) {
          out += i < resolved ? target[i] : GLYPHS[(Math.random() * GLYPHS.length) | 0];
        }
        line.textContent = out;
        if (frame >= 11) {
          line.textContent = target;
          frame = 0;
          index = (index + 1) % lines.length;
        }
      }, 38);
    };

    const measure = () => {
      if (!cinematic()) {
        root.classList.add("is-flat");
        stopIdle();
        if (cipher) cipher.style.opacity = "0";
        clearStage();
        return;
      }
      root.classList.remove("is-flat");
      const vh = window.innerHeight;
      const inner = wrap.scrollHeight;
      spacer.style.height = `${inner + vh * 2}px`;
    };

    const update = () => {
      const y = window.scrollY;
      const vh = window.innerHeight || 1;
      const press = Math.min(1, Math.max(0, y / (vh * 0.7)));
      hero.style.setProperty("--press", String(press));
      if (cipher && plate) {
        if (press > 0.02) paintCipher(cipher, plate, press);
        else cipher.style.opacity = "0";
      }
      if (press > 0.02) stopIdle();
      else if (!reduced.matches) startIdle();
      if (!cinematic()) return;
      const inner = wrap.scrollHeight;
      const maxInner = Math.max(0, inner - vh);
      const panelY = Math.max(0, vh - y);
      panel.style.transform = `translate3d(0, ${panelY}px, 0)`;
      const shift = Math.min(Math.max(0, y - vh), maxInner);
      wrap.style.transform = `translate3d(0, ${-shift}px, 0)`;

      const covered = y >= vh;
      hero.style.visibility = covered ? "hidden" : "visible";
      if (covered) hero.setAttribute("inert", "");
      else hero.removeAttribute("inert");

      const mast = hero.querySelector<HTMLElement>(".stage-mast");
      if (mast) {
        if (y <= 0) {
          mast.style.opacity = "";
          mast.removeAttribute("inert");
        } else {
          const t = Math.min(1, Math.max(0, (y - vh * 0.12) / (vh * 0.33)));
          mast.style.opacity = String(1 - t);
          if (t > 0.92) mast.setAttribute("inert", "");
          else mast.removeAttribute("inert");
        }
      }

      wrap.querySelectorAll<HTMLElement>("[data-scene]").forEach((scene) => {
        const pin = scene.querySelector<HTMLElement>("[data-pin]");
        if (!pin) return;
        const topVp = scene.getBoundingClientRect().top;
        const pinRange = Math.max(0, scene.offsetHeight - vh);
        const pinOffset = Math.min(Math.max(-topVp, 0), pinRange);
        pin.style.transform = `translate3d(0, ${pinOffset}px, 0)`;
        const sp = pinRange ? pinOffset / pinRange : 1;
        scene.style.setProperty("--sp", sp.toFixed(4));
        const fadeIn = Math.min(1, Math.max(0, (vh * 0.9 - topVp) / (vh * 0.45)));
        const exitP = Math.min(1, Math.max(0, (-topVp - pinRange) / (vh * 0.4)));
        pin.style.opacity = String(Math.min(fadeIn, 1 - exitP));
      });

      const outroStart = vh + maxInner;
      const outroP = Math.min(1, Math.max(0, (y - outroStart) / vh));
      outro.style.transform = `translate3d(0, ${(1 - outroP) * 100}%, 0)`;
      outro.style.pointerEvents = outroP < 0.55 ? "none" : "auto";
      if (outroP < 0.55) outro.setAttribute("inert", "");
      else outro.removeAttribute("inert");
    };

    const onScroll = () => {
      cancelAnimationFrame(ticker);
      ticker = requestAnimationFrame(update);
    };

    const schedule = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        measure();
        update();
      });
    };

    const onResize = () => {
      if (coarse.matches && window.innerWidth === lastW) return;
      lastW = window.innerWidth;
      schedule();
    };

    const onPointer = (event: PointerEvent) => {
      if (!cursor) return;
      cursor.style.transform = `translate3d(${event.clientX}px, ${event.clientY}px, 0) translate(-50%, -50%)`;
      const target = event.target instanceof Element ? event.target : null;
      const run = Boolean(target?.closest(".run-control"));
      cursor.classList.toggle("is-tag", run || Boolean(target?.closest("a.control")));
      cursor.classList.toggle("is-run", run);
      cursor.classList.toggle("is-quiet", Boolean(target?.closest(".seam, .paper-press")));
    };
    const fine =
      window.matchMedia("(pointer: fine) and (min-width: 1024px)").matches && cinematic();
    if (fine) window.addEventListener("pointermove", onPointer);

    schedule();
    startIdle();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);
    const fonts = document.fonts?.ready.then(schedule);
    const observer = new ResizeObserver(schedule);
    observer.observe(wrap);
    reduced.addEventListener("change", schedule);
    narrow.addEventListener("change", schedule);

    const onPageShow = (event: PageTransitionEvent) => {
      if (!event.persisted) return;
      leaving.current = false;
      root.classList.remove("is-leaving");
      resetWave(wave);
    };
    window.addEventListener("pageshow", onPageShow);

    return () => {
      cancelAnimationFrame(raf);
      cancelAnimationFrame(ticker);
      window.clearInterval(idle);
      if (fine) window.removeEventListener("pointermove", onPointer);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pageshow", onPageShow);
      reduced.removeEventListener("change", schedule);
      narrow.removeEventListener("change", schedule);
      observer.disconnect();
      void fonts;
    };
  }, []);

  const onGuide = (event: ReactMouseEvent<HTMLAnchorElement>) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    if (!cinematic() || leaving.current) return;
    event.preventDefault();
    const href = event.currentTarget.href;
    const root = rootRef.current;
    const wave = waveRef.current;
    if (!root || !wave) {
      window.location.assign(href);
      return;
    }
    leaving.current = true;
    root.classList.add("is-leaving");
    const label = event.currentTarget.querySelector<HTMLElement>(".control-label");
    if (label) censorLabel(label, label.textContent ?? "Read the guide");
    burst(event.clientX, event.clientY);
    playWave(wave, () => window.location.assign(href));
  };

  const onSeamMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!window.matchMedia("(pointer: fine) and (min-width: 801px)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const card = event.currentTarget;
    const box = card.getBoundingClientRect();
    const nx = (event.clientX - box.left) / box.width - 0.5;
    const ny = (event.clientY - box.top) / box.height - 0.5;
    card.style.setProperty("--rx", `${ny * 8}deg`);
    card.style.setProperty("--ry", `${-nx * 10}deg`);
    card.style.setProperty("--shine", String(-(nx + ny * 0.4) * 34));
  };

  const onSeamLeave = (event: ReactPointerEvent<HTMLDivElement>) => {
    const card = event.currentTarget;
    card.style.setProperty("--rx", "0deg");
    card.style.setProperty("--ry", "0deg");
    card.style.setProperty("--shine", "0");
  };

  return (
    <div className="stage-root" ref={rootRef}>
      <div className="stage-spacer" ref={spacerRef} />
      <header className="stage-hero" ref={heroRef}>
        <div className="stage-mast">
          <p className="mast-name">AI Tool Discovery Agent</p>
          <div className="mast-meta">
            <button
              type="button"
              className="status-pill-btn"
              onClick={() => setShowDiagnostics(true)}
              title="Click to inspect live APIs and Supabase health"
            >
              <span className={`status-dot ${diagnosticStatus === "operational" ? "is-live" : "is-warn"}`} />
              <span>
                {diagnosticStatus === "checking"
                  ? "Checking APIs & DB"
                  : diagnosticStatus === "operational"
                  ? "APIs & DB Operational"
                  : "APIs & DB Degraded"}
              </span>
            </button>
            <p className="mast-edition">Weekly digest</p>
          </div>
        </div>
        <div className="rules" aria-hidden="true">
          <span className="rule-ink" />
          <span className="rule-red" />
        </div>
        <div className="hero-grid">
          <div className="hero-copy">
            <p className="kicker">For teams who ship against new tools</p>
            <h1>Find the AI products that launched this week. Leave the roundups in the search results.</h1>
            <p className="lede">
              The agent plans a date window, searches SerpApi, compares web and news, and posts a card to the console, Slack, or Microsoft Teams.
            </p>
            <ul className="noise" aria-hidden="true">
              {NOISE.map((line) => (
                <li key={line} data-line={line}>
                  {line}
                </li>
              ))}
            </ul>
            <div className="actions">
              <a className="control" href="#run">
                Run the digest
              </a>
              <button
                type="button"
                className="control control-diag"
                onClick={() => setShowDiagnostics(true)}
              >
                ⚡ Diagnostics & APIs
              </button>
              <a className="control" href={GUIDE_HREF} onClick={onGuide}>
                <span className="control-label">Read the guide</span>
              </a>
              <a className="text-link" href="/subscribe">
                Subscribe
              </a>
              <a className="text-link" href={GITHUB_HREF} rel="noreferrer">
                Source on GitHub
              </a>
            </div>
          </div>
          <div className="hero-object">
            <figure className="press-figure">
              <PaperPress />
              <figcaption>Search pages in a stack. Scrolling presses them flat. The card below is what is kept.</figcaption>
            </figure>
            <figure className="plate hero-plate">
            <div className="card-frame">
              <img
                ref={plateRef}
                src="/teams_output_example.png"
                width={1024}
                height={506}
                alt="Sample Teams card for Quibim: title, website, audience, overview, features, pricing, and source."
              />
              <canvas className="cipher-plate" ref={cipherRef} aria-hidden="true" />
            </div>
            <figcaption>Sample Digest Card — Illustrative. Not a discovery from today.</figcaption>
          </figure>
          </div>
        </div>
        <RunDrawer />
      </header>

      <div className="stage-panel" ref={panelRef}>
        <div className="stage-wrap" ref={wrapRef}>
          <section className="act act-statement" data-scene aria-labelledby="useful">
            <div className="act-pin" data-pin>
              <div className="act-inner">
                <h2 id="useful">Who it is for</h2>
                <div className="useful">
                  <p>
                    A team lead who needs to know what shipped, not what a blog ranked. A researcher who wants the product page, not the article about the product page.
                  </p>
                  <p>
                    The useful part is the rejection. Search returns launch lists, museum pages, and news. The digest keeps a product: what it does, who it is for, what it costs, and where it lives.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {STEPS.map((step, index) => (
            <section className="act" data-scene key={step.name} aria-labelledby={`step-${index}`}>
              <div className="act-pin" data-pin>
                <div className="act-inner act-step">
                  <p className="act-index">{String(index + 1).padStart(2, "0")}</p>
                  <div>
                    <h2 id={`step-${index}`}>{step.name}</h2>
                    <p>{step.text}</p>
                  </div>
                </div>
              </div>
            </section>
          ))}

          <section className="act act-proof" data-scene aria-labelledby="output">
            <div className="act-pin" data-pin>
              <div className="act-inner">
                <h2 id="output">The same card, two rooms</h2>
                <p className="band-note">Teams on one side, Slack on the other. A phone shows both, one after the other.</p>
                <div
                  className="seam"
                  onPointerMove={onSeamMove}
                  onPointerLeave={onSeamLeave}
                >
                  <div className="seam-face seam-a" tabIndex={0}>
                    <img
                      src="/teams_output_example.png"
                      width={1024}
                      height={506}
                      alt="Teams digest card for the Quibim prostate-cancer detection tool."
                    />
                    <span>Teams</span>
                  </div>
                  <div className="seam-face seam-b" tabIndex={0}>
                    <img
                      src="/slack_output_example.png"
                      width={1024}
                      height={640}
                      alt="Slack digest in #tool-updates for SynthID Detector, posted by AI-Search-Buddy."
                    />
                    <span>Slack</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="act" data-scene aria-labelledby="robust">
            <div className="act-pin" data-pin>
              <div className="act-inner">
                <h2 id="robust">What happens when a step fails</h2>
                <ul className="robust">
                  {FAILURES.map(([title, text]) => (
                    <li key={title}>
                      <strong>{title}</strong>
                      <span>{text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        </div>
      </div>

      <footer className="stage-outro" ref={outroRef}>
        <p className="outro-kicker">Weekly digest</p>
        <p className="outro-mark">AI Tool Discovery Agent</p>
        <a className="control" href={GUIDE_HREF} onClick={onGuide}>
          <span className="control-label">Read the guide</span>
        </a>
      </footer>

      <div className="cursor" ref={cursorRef} aria-hidden="true" />
      <svg
        className="stage-wave"
        ref={waveRef}
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path className="wave-lead" />
        <path className="wave-ink" />
      </svg>
      <DiagnosticsDrawer
        isOpen={showDiagnostics}
        onClose={() => setShowDiagnostics(false)}
      />
    </div>
  );
}

function resetWave(wave: SVGSVGElement) {
  wave.querySelectorAll("path").forEach((path) => {
    path.setAttribute("d", "M 0 100 C 50 100 50 100 100 100 V 100 H 0");
  });
}

function playWave(wave: SVGSVGElement, done: () => void) {
  const paths = Array.from(wave.querySelectorAll("path"));
  const count = 10;
  const sets = paths.map(() => Array.from({ length: count }, () => 100));
  const delays = paths.map((_, pathIndex) =>
    Array.from({ length: count }, () => Math.random() * 250 + pathIndex * 150),
  );
  const start = performance.now() + 350;
  const duration = 750;

  const draw = () => {
    paths.forEach((path, pathIndex) => {
      const pts = sets[pathIndex];
      let d = `M 0 ${pts[0]} C`;
      for (let j = 0; j < count - 1; j += 1) {
        const p = ((j + 1) / (count - 1)) * 100;
        const cp = p - 100 / (count - 1) / 2;
        d += ` ${cp} ${pts[j]} ${cp} ${pts[j + 1]} ${p} ${pts[j + 1]}`;
      }
      path.setAttribute("d", `${d} V 100 H 0`);
    });
  };

  const tick = (now: number) => {
    let finished = true;
    sets.forEach((pts, pathIndex) => {
      for (let j = 0; j < count; j += 1) {
        const t = Math.min(1, Math.max(0, (now - start - delays[pathIndex][j]) / duration));
        if (t < 1) finished = false;
        pts[j] = 100 * (1 - easeInOut(t));
      }
    });
    draw();
    if (!finished) requestAnimationFrame(tick);
    else done();
  };
  requestAnimationFrame(tick);
}

function burst(x: number, y: number) {
  const root = document.createElement("div");
  root.className = "burst";
  root.style.left = `${x}px`;
  root.style.top = `${y}px`;
  for (let i = 0; i < 12; i += 1) {
    const bit = document.createElement("span");
    const angle = (Math.PI * 2 * i) / 12 + Math.random() * 0.35;
    const dist = 34 + Math.random() * 66;
    bit.style.setProperty("--dx", `${Math.cos(angle) * dist}px`);
    bit.style.setProperty("--dy", `${Math.sin(angle) * dist + 20}px`);
    root.appendChild(bit);
  }
  document.body.appendChild(root);
  window.setTimeout(() => root.remove(), 900);
}
