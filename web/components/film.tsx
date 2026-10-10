"use client";

/**
 * Motion thesis, written before any tween.
 * Metaphor: a raw result stays censored until the pipeline resolves it into a named tool.
 * Hero material: a full-bleed mosaic of search cells.
 * Playhead: scroll is the pipeline. Rest is unresolved and alive. Forward scroll resolves. Scroll up censors again.
 * Ceremony: one control, "Read the guide", censors its label, throws a short burst, then a two-path wave, then opens the guide. Modifier-clicks and the middle button skip the ceremony and follow the real link.
 * Still: reduced motion shows the resolved digest card, final type, and scene opacity 1. No interval, cursor, burst, or marquee.
 */

import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type MouseEvent } from "react";

import type { DigestFile, ProofResponse } from "@/lib/types";

const GUIDE_HREF = "/guide";
const GITHUB_HREF = "https://github.com/Adit-Jain-srm/SerpApi_Track1";
const CEREMONY = "Read the guide";

const GLYPHS = "█▓▒░•";
const WAVE_POINTS = 10;
const EASE = [0.22, 1, 0.36, 1] as const;

const CELLS: { c: number; r: number; tool?: boolean }[] = [
  { c: 1, r: 1 },
  { c: 2, r: 1 },
  { c: 5, r: 1, tool: true },
  { c: 8, r: 1 },
  { c: 11, r: 1 },
  { c: 3, r: 2 },
  { c: 6, r: 2 },
  { c: 10, r: 2, tool: true },
  { c: 12, r: 2 },
  { c: 1, r: 3, tool: true },
  { c: 4, r: 3 },
  { c: 9, r: 3 },
  { c: 2, r: 4 },
  { c: 6, r: 4 },
  { c: 8, r: 4, tool: true },
  { c: 11, r: 4 },
  { c: 4, r: 5, tool: true },
  { c: 7, r: 5 },
  { c: 12, r: 5 },
  { c: 1, r: 6 },
  { c: 3, r: 6 },
  { c: 5, r: 6, tool: true },
  { c: 9, r: 6 },
  { c: 2, r: 7 },
  { c: 6, r: 7 },
  { c: 8, r: 7 },
];

const ACTS = [
  {
    n: "01",
    t: "Ask the window, not the whole web.",
    b: "The plan fixes a date range. Web search stays on Google and sends tbs. News search puts after: in the query. Four launch phrases, two engines.",
  },
  {
    n: "02",
    t: "The same launch is one row.",
    b: "Aggregator domains drop. Matching URLs merge. When the web date and the news date disagree, the news date wins.",
  },
  {
    n: "03",
    t: "Name it, then send it.",
    b: "The page is fetched and read into a tool record. The digest prints. Teams gets a post only when a webhook is configured.",
  },
] as const;

const CARD_NOISE = Array.from({ length: 24 }, (_, i) => i);

const AGGREGATORS = ["reddit.com", "techcrunch.com", "medium.com", "producthunt.com"];

type Act = (typeof ACTS)[number];
type SceneBox = { el: HTMLElement; pin: HTMLElement; top: number; h: number; off: boolean | null };

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function cubicBezier(x1: number, y1: number, x2: number, y2: number) {
  const cx = 3 * x1;
  const bx = 3 * (x2 - x1) - cx;
  const ax = 1 - cx - bx;
  const cy = 3 * y1;
  const by = 3 * (y2 - y1) - cy;
  const ay = 1 - cy - by;
  const sampleX = (t: number) => ((ax * t + bx) * t + cx) * t;
  const sampleY = (t: number) => ((ay * t + by) * t + cy) * t;
  const sampleDX = (t: number) => (3 * ax * t + 2 * bx) * t + cx;
  return (x: number) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let t = x;
    for (let i = 0; i < 6; i += 1) {
      const slope = sampleDX(t);
      if (Math.abs(slope) < 1e-6) break;
      t = clamp(t - (sampleX(t) - x) / slope, 0, 1);
    }
    return sampleY(t);
  };
}

const easeOut = cubicBezier(EASE[0], EASE[1], EASE[2], EASE[3]);

function glyphAt(index: number) {
  return GLYPHS[index % GLYPHS.length] ?? GLYPHS[0];
}

function buildWave(points: number[]) {
  let d = `M 0 ${points[0] ?? 100} C`;
  for (let j = 0; j < WAVE_POINTS - 1; j += 1) {
    const p = ((j + 1) / (WAVE_POINTS - 1)) * 100;
    const cp = p - 100 / (WAVE_POINTS - 1) / 2;
    const a = points[j] ?? 100;
    const b = points[j + 1] ?? 100;
    d += ` ${cp} ${a} ${cp} ${b} ${p} ${b}`;
  }
  return `${d} V 100 H 0 Z`;
}

function setCovered(el: HTMLElement, covered: boolean) {
  el.style.visibility = covered ? "hidden" : "visible";
  el.style.pointerEvents = covered ? "none" : "";
  if (covered) el.setAttribute("inert", "");
  else el.removeAttribute("inert");
}

/** Left to right, resolved characters become glyphs. Same interval for every censor. */
function censorLabel(el: HTMLElement) {
  const target = el.dataset.label || el.textContent || "";
  el.dataset.label = target;
  el.classList.add("is-glyph");
  let frame = 0;
  const total = 11;
  const id = window.setInterval(() => {
    frame += 1;
    const count = Math.floor((frame / total) * target.length);
    let out = "";
    for (let i = 0; i < target.length; i += 1) {
      out += i < count ? glyphAt((Math.random() * GLYPHS.length) | 0) : target[i];
    }
    el.textContent = out;
    if (frame >= total) {
      window.clearInterval(id);
      el.textContent = Array.from(target, (_, i) => glyphAt(i)).join("");
    }
  }, 38);
  return id;
}

function restoreLabel(el: HTMLElement | null) {
  if (!el) return;
  const label = el.dataset.label;
  if (label) el.textContent = label;
  el.classList.remove("is-glyph");
}

function spawnBurst(x: number, y: number) {
  const root = document.createElement("div");
  root.className = "burst";
  for (let i = 0; i < 14; i += 1) {
    const bit = document.createElement("span");
    const angle = Math.random() * Math.PI * 2;
    const dist = 34 + Math.random() * 66;
    const dx = Math.cos(angle) * dist;
    const dy = Math.sin(angle) * dist + 18 + Math.random() * 36;
    bit.style.left = `${x}px`;
    bit.style.top = `${y}px`;
    bit.style.transitionDuration = `${0.55 + Math.random() * 0.35}s`;
    root.appendChild(bit);
    requestAnimationFrame(() => {
      bit.style.transform = `translate3d(${dx}px, ${dy}px, 0) scale(0.35)`;
      bit.style.opacity = "0";
    });
  }
  document.body.appendChild(root);
  window.setTimeout(() => root.remove(), 1000);
}

function hostOf(link: string) {
  try {
    return new URL(link).host;
  } catch {
    return link;
  }
}

let proofInflight: Promise<ProofResponse> | null = null;

function loadProof(): Promise<ProofResponse> {
  if (!proofInflight) {
    proofInflight = fetch("/api/proof")
      .then((res) => {
        if (!res.ok) throw new Error("proof");
        return res.json() as Promise<unknown>;
      })
      .then((body) => {
        if (!body || typeof body !== "object") throw new Error("proof");
        const value = body as ProofResponse;
        if ((value.source !== "live" && value.source !== "sample") || !Array.isArray(value.results)) {
          throw new Error("proof");
        }
        return value;
      })
      .catch(
        (): ProofResponse => ({
          source: "sample",
          query: "new AI tool now available",
          tbs: "qdr:d7",
          results: [],
        }),
      );
  }
  return proofInflight;
}

function CipherLine({ text, from, span }: { text: string; from: number; span: number }) {
  const chars = Array.from(text);
  const step = span / Math.max(chars.length, 1);
  return (
    <span className="cipher" style={{ "--from": from, "--step": step } as CSSProperties}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">
        {chars.map((ch, i) => (
          <span className="ch" key={`${ch}-${i}`} style={{ "--i": i } as CSSProperties}>
            <span className="glyph">{ch === " " ? "\u00a0" : glyphAt(i)}</span>
            <span className="letter">{ch === " " ? "\u00a0" : ch}</span>
          </span>
        ))}
      </span>
    </span>
  );
}

function ActView({ act }: { act: Act }) {
  return (
    <>
      <p className="step-index nums">{act.n}</p>
      <div className="step-copy">
        <h2 className="step-title">{act.t}</h2>
        <p className="step-body">{act.b}</p>
      </div>
    </>
  );
}

function useLiveProof() {
  const [data, setData] = useState<ProofResponse | null>(null);
  useEffect(() => {
    let cancel = false;
    loadProof().then((value) => {
      if (!cancel) setData(value);
    });
    return () => {
      cancel = true;
    };
  }, []);
  return data;
}

function WebHit() {
  const live = useLiveProof();
  const hit = live?.source === "live" ? live.results[0] : undefined;
  return (
    <article className="hit hit-web">
      <h3 className="hit-title">{hit?.title || "Sample launch page"}</h3>
      <p className="hit-snippet">
        {hit?.snippet || "Sample web snippet for the same window. Not a live result."}
      </p>
      <p className="hit-meta nums">
        {hit ? `${hostOf(hit.link)} · fixed query` : "Sample hit. Not from today."}
      </p>
    </article>
  );
}

function LiveCaption() {
  const live = useLiveProof();
  if (live?.source !== "live") return null;
  const count = live.results.length;
  const line =
    count > 0
      ? `Live proof · ${live.tbs} · ${count} results. The card stays the sample shape.`
      : "Live proof returned no organic results. The card stays the sample shape.";
  return <p className="live-line nums">{line}</p>;
}

export function Film({ digest }: { digest: DigestFile }) {
  const tool = digest.tools[0];
  const spacerRef = useRef<HTMLDivElement>(null);
  const chromeRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);
  const outroRef = useRef<HTMLElement>(null);
  const labelRef = useRef<HTMLSpanElement>(null);
  const cursorRef = useRef<HTMLDivElement>(null);
  const pillRef = useRef<HTMLSpanElement>(null);
  const waveRef = useRef<SVGSVGElement>(null);
  const paleRef = useRef<SVGPathElement>(null);
  const deepRef = useRef<SVGPathElement>(null);

  useLayoutEffect(() => {
    const spacer = spacerRef.current;
    const chrome = chromeRef.current;
    const stage = stageRef.current;
    const panel = panelRef.current;
    const wrap = wrapRef.current;
    const outro = outroRef.current;
    const cursor = cursorRef.current;
    const pale = paleRef.current;
    const deep = deepRef.current;
    const wave = waveRef.current;
    if (!spacer || !chrome || !stage || !panel || !wrap || !outro || !cursor || !pale || !deep || !wave) {
      return;
    }

    const reduceMq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const fineMq = window.matchMedia("(pointer: fine)");
    const coarse = window.matchMedia("(pointer: coarse)").matches;
    const paths = [pale, deep];
    let vh = window.innerHeight;
    let lastW = window.innerWidth;
    let innerMax = 0;
    let raf = 0;
    let measureRaf = 0;
    let waveRaf = 0;
    let heroCovered = false;
    let leaving = false;
    let intervals: number[] = [];
    let scenes: SceneBox[] = [];
    let cursorSeen = false;

    const reduced = () => reduceMq.matches;
    const cursorOn = () => fineMq.matches && window.innerWidth >= 1024 && !reduced();

    const resetWave = () => {
      cancelAnimationFrame(waveRaf);
      const flat = Array.from({ length: WAVE_POINTS }, () => 100);
      const d = buildWave(flat);
      for (const path of paths) path.setAttribute("d", d);
      wave.style.visibility = "hidden";
      wave.style.pointerEvents = "none";
      wave.setAttribute("inert", "");
    };

    const restoreChrome = () => {
      chrome.style.removeProperty("opacity");
      chrome.style.removeProperty("visibility");
      chrome.style.removeProperty("pointer-events");
      chrome.removeAttribute("inert");
      setCovered(stage, false);
      heroCovered = false;
    };

    const clearMotion = () => {
      cancelAnimationFrame(raf);
      for (const el of [stage, panel, wrap, outro, chrome]) {
        el.style.removeProperty("transform");
        el.style.removeProperty("opacity");
        el.style.removeProperty("visibility");
        el.style.removeProperty("pointer-events");
        el.removeAttribute("inert");
      }
      for (const scene of scenes) {
        scene.pin.style.removeProperty("transform");
        scene.pin.style.removeProperty("opacity");
        scene.pin.style.removeProperty("visibility");
        scene.pin.style.removeProperty("pointer-events");
        scene.pin.removeAttribute("inert");
        scene.el.style.removeProperty("--sp");
      }
      stage.style.removeProperty("--sp");
      wrap.querySelectorAll<HTMLElement>(".digest-card").forEach((card) => {
        card.removeAttribute("inert");
      });
    };

    const update = () => {
      if (reduced()) return;
      const y = window.scrollY;
      const panelY = Math.max(0, vh - y);
      const innerY = -Math.max(0, y - vh);
      panel.style.transform = `translate3d(0, ${panelY}px, 0)`;
      wrap.style.transform = `translate3d(0, ${innerY}px, 0)`;

      const covered = y >= vh;
      if (covered !== heroCovered) {
        heroCovered = covered;
        setCovered(stage, covered);
      }
      const heroSp = clamp(y / Math.max(vh, 1), 0, 1);
      stage.style.setProperty("--sp", heroSp.toFixed(4));
      const rest = y < 2 ? "true" : "";
      if ((stage.dataset.rest ?? "") !== rest) {
        if (rest) stage.dataset.rest = "true";
        else delete stage.dataset.rest;
      }

      if (y <= 0) {
        restoreChrome();
      } else {
        const into = y - vh;
        const fade =
          into <= vh * 0.12 ? 0 : clamp((into - vh * 0.12) / (vh * 0.33), 0, 1);
        chrome.style.opacity = String(1 - fade);
        const chromeOff = fade > 0.98;
        chrome.style.visibility = chromeOff ? "hidden" : "visible";
        chrome.style.pointerEvents = chromeOff ? "none" : "";
        if (chromeOff) chrome.setAttribute("inert", "");
        else chrome.removeAttribute("inert");
      }

      for (const scene of scenes) {
        const topVp = panelY + innerY + scene.top;
        const pinRange = Math.max(0, scene.h - vh);
        const pinOffset = clamp(-topVp, 0, pinRange);
        scene.pin.style.transform = `translate3d(0, ${pinOffset}px, 0)`;
        const sp = pinRange ? pinOffset / pinRange : 1;
        scene.el.style.setProperty("--sp", sp.toFixed(4));
        const card = scene.el.querySelector<HTMLElement>(".digest-card");
        if (card) {
          const open = sp > 0.6;
          const locked = card.hasAttribute("inert");
          if (open && locked) card.removeAttribute("inert");
          else if (!open && !locked) card.setAttribute("inert", "");
        }
        const fadeIn = clamp((vh * 0.9 - topVp) / (vh * 0.45), 0, 1);
        const exitP = clamp((-topVp - pinRange) / (vh * 0.4), 0, 1);
        const opacity = Math.min(fadeIn, 1 - exitP);
        scene.pin.style.opacity = opacity.toFixed(4);
        const off = opacity <= 0.001;
        if (off !== scene.off) {
          scene.off = off;
          setCovered(scene.pin, off);
        }
      }

      const outroP = clamp((y - (vh + innerMax)) / Math.max(1, vh - 24), 0, 1);
      outro.style.transform = `translate3d(0, ${(1 - outroP) * 100}%, 0)`;
      if (outroP < 0.02) setCovered(outro, true);
      else if (outroP > 0.55) setCovered(outro, false);
      else {
        outro.style.visibility = "visible";
        outro.style.pointerEvents = "none";
        outro.setAttribute("inert", "");
      }
      if (outroP > 0.55) {
        panel.style.pointerEvents = "none";
        panel.setAttribute("inert", "");
      } else {
        panel.style.pointerEvents = "";
        panel.removeAttribute("inert");
      }
    };

    const measure = () => {
      if (reduced()) return;
      vh = window.innerHeight;
      scenes = [];
      const nodes = wrap.querySelectorAll<HTMLElement>("[data-scene]");
      nodes.forEach((el) => {
        if (el.offsetHeight === 0) return;
        const pin = el.querySelector<HTMLElement>("[data-pin]");
        if (!pin) return;
        scenes.push({ el, pin, top: el.offsetTop, h: el.offsetHeight, off: null });
      });
      innerMax = Math.max(0, wrap.scrollHeight - vh);
      spacer.style.height = `${wrap.scrollHeight + vh * 2 + 48}px`;
      update();
    };

    const schedule = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(update);
    };

    const scheduleMeasure = () => {
      cancelAnimationFrame(measureRaf);
      measureRaf = requestAnimationFrame(measure);
    };

    const onScroll = () => {
      if (window.scrollY === 0) {
        restoreChrome();
        update();
        return;
      }
      schedule();
    };

    const onResize = () => {
      if (coarse && window.innerWidth === lastW) return;
      lastW = window.innerWidth;
      if (!reduced()) scheduleMeasure();
    };

    const onMode = () => {
      document.documentElement.dataset.motion = reduced() ? "reduce" : "full";
      if (reduced()) clearMotion();
      else measure();
    };

    const onMove = (event: PointerEvent) => {
      if (!cursorOn()) return;
      if (!cursorSeen) {
        cursorSeen = true;
        cursor.dataset.live = "true";
      }
      cursor.style.transform = `translate3d(${event.clientX}px, ${event.clientY}px, 0)`;
    };

    const onOver = (event: Event) => {
      if (!cursorOn() || leaving) return;
      const target = event.target;
      if (!(target instanceof Element)) return;
      const control = target.closest("[data-control]");
      const link = target.closest("a");
      cursor.classList.toggle("tag", Boolean(control));
      cursor.classList.toggle("link", Boolean(link) && !control);
      if (control && pillRef.current && !pillRef.current.classList.contains("is-glyph")) {
        pillRef.current.textContent = CEREMONY;
      }
    };

    const onLeave = (event: Event) => {
      if (leaving || reduced()) return;
      leaving = true;
      const detail = (event as CustomEvent<{ x: number; y: number }>).detail;
      if (labelRef.current) intervals.push(censorLabel(labelRef.current));
      if (pillRef.current) intervals.push(censorLabel(pillRef.current));
      if (detail) spawnBurst(detail.x, detail.y);
      const delays = [0, 1].map(() =>
        Array.from({ length: WAVE_POINTS }, () => Math.random() * 250),
      );
      const points = [0, 1].map(() => Array.from({ length: WAVE_POINTS }, () => 100));
      const offset = [0, 150];
      const started = performance.now();
      let shown = false;
      let finished = false;
      const frame = (now: number) => {
        if (!leaving) return;
        const elapsed = now - started;
        if (!shown && elapsed >= 350) {
          shown = true;
          wave.style.visibility = "visible";
          wave.style.pointerEvents = "auto";
          wave.removeAttribute("inert");
        }
        let done = elapsed > 350;
        for (let i = 0; i < 2; i += 1) {
          for (let j = 0; j < WAVE_POINTS; j += 1) {
            const u = clamp((elapsed - 350 - offset[i] - delays[i][j]) / 750, 0, 1);
            points[i][j] = 100 * (1 - easeOut(u));
            if (u < 1) done = false;
          }
          paths[i]?.setAttribute("d", buildWave(points[i]));
        }
        if (done && !finished) {
          finished = true;
          window.location.assign(GUIDE_HREF);
          return;
        }
        waveRaf = requestAnimationFrame(frame);
      };
      waveRaf = requestAnimationFrame(frame);
    };

    const onPageShow = (event: PageTransitionEvent) => {
      if (!event.persisted) return;
      leaving = false;
      for (const id of intervals) window.clearInterval(id);
      intervals = [];
      restoreLabel(labelRef.current);
      restoreLabel(pillRef.current);
      document.querySelector(".burst")?.remove();
      resetWave();
      if (!reduced()) measure();
    };

    document.documentElement.dataset.motion = reduced() ? "reduce" : "full";
    resetWave();
    if (!reduced()) measure();

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);
    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerover", onOver);
    window.addEventListener("film-leave", onLeave);
    window.addEventListener("pageshow", onPageShow);
    reduceMq.addEventListener("change", onMode);
    const observer = new ResizeObserver(() => {
      if (reduced()) return;
      if (coarse && window.innerWidth === lastW) return;
      scheduleMeasure();
    });
    observer.observe(wrap);
    document.fonts?.ready.then(() => {
      if (!reduced()) scheduleMeasure();
    }).catch(() => undefined);

    return () => {
      cancelAnimationFrame(raf);
      cancelAnimationFrame(measureRaf);
      cancelAnimationFrame(waveRaf);
      for (const id of intervals) window.clearInterval(id);
      observer.disconnect();
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerover", onOver);
      window.removeEventListener("film-leave", onLeave);
      window.removeEventListener("pageshow", onPageShow);
      reduceMq.removeEventListener("change", onMode);
      document.querySelector(".burst")?.remove();
      delete document.documentElement.dataset.motion;
    };
  }, []);

  const onControlClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    event.preventDefault();
    window.dispatchEvent(
      new CustomEvent("film-leave", { detail: { x: event.clientX, y: event.clientY } }),
    );
  };

  if (!tool) return null;

  return (
    <div className="film">
      <div className="spacer" ref={spacerRef} />
      <header className="chrome" ref={chromeRef}>
        <span>Track 01</span>
        <span className="chrome-rule" aria-hidden="true" />
        <span>Weekly</span>
      </header>

      <div className="stage" data-rest="true" ref={stageRef}>
        <div className="mosaic" aria-hidden="true">
          {CELLS.map((cell) => (
            <div
              key={`${cell.c}-${cell.r}`}
              className={cell.tool ? "cell is-tool" : "cell"}
              data-wide={cell.c > 6 ? "true" : undefined}
              style={
                {
                  gridColumn: cell.c,
                  gridRow: cell.r,
                  "--c": cell.c,
                  "--r": cell.r,
                } as CSSProperties
              }
            >
              <span className="cell-drift">
                {cell.tool ? <span className="wash" /> : null}
                <span className="noise">{glyphAt(cell.c + cell.r)}</span>
              </span>
            </div>
          ))}
        </div>
        <div className="hero-copy">
          <p className="wordmark" aria-hidden="true">
            <CipherLine text="Digest" from={0.04} span={0.7} />
          </p>
          <a
            className="control"
            data-control=""
            href={GUIDE_HREF}
            aria-label={CEREMONY}
            onClick={onControlClick}
          >
            <span className="control-label" data-label={CEREMONY} ref={labelRef}>
              {CEREMONY}
            </span>
          </a>
        </div>
      </div>

      <div className="panel" ref={panelRef}>
        <div className="wrap" ref={wrapRef}>
          <section className="scene proof" data-scene>
            <div className="pin" data-pin>
              <div className="proof-layout">
                <div className="stage-cell">
                  <ul className="chips">
                    {AGGREGATORS.map((name) => (
                      <li className="chip" key={name}>
                        {name}
                      </li>
                    ))}
                  </ul>
                  <WebHit />
                  <article className="hit hit-news">
                    <h3 className="hit-title">Sample news page</h3>
                    <p className="hit-snippet">
                      Sample news snippet. Same window, different date. This one stays.
                    </p>
                    <p className="hit-meta nums">Sample hit. Not from today.</p>
                  </article>
                  <article className="digest-card">
                    <div className="card-censor" aria-hidden="true">
                      {CARD_NOISE.map((i) => (
                        <span key={i} className={i % 7 === 3 ? "is-tool" : undefined}>
                          {glyphAt(i + 2)}
                        </span>
                      ))}
                    </div>
                    <h2 className="card-title">
                      <CipherLine text={`AI Tool 2: ${tool.title}`} from={0.4} span={0.22} />
                    </h2>
                    <div className="card-rule" aria-hidden="true" />
                    <dl className="digest-fields">
                      <div>
                        <dt>Website</dt>
                        <dd>
                          <a href={tool.website} target="_blank" rel="noreferrer">
                            {tool.website}
                            <span className="sr-only"> (opens in a new tab)</span>
                          </a>
                        </dd>
                      </div>
                      <div>
                        <dt>Target audience</dt>
                        <dd>{tool.target_audience}</dd>
                      </div>
                      <div>
                        <dt>Overview</dt>
                        <dd>{tool.summary}</dd>
                      </div>
                      <div>
                        <dt>Key features</dt>
                        <dd>
                          {tool.features.length > 0 ? (
                            <ul>
                              {tool.features.map((feature) => (
                                <li key={feature}>{feature}</li>
                              ))}
                            </ul>
                          ) : (
                            "None listed"
                          )}
                        </dd>
                      </div>
                      <div>
                        <dt>Pricing</dt>
                        <dd>{tool.pricing ?? "No pricing information available."}</dd>
                      </div>
                      <div>
                        <dt>Source</dt>
                        <dd>
                          <a href={tool.source} target="_blank" rel="noreferrer">
                            {tool.source}
                            <span className="sr-only"> (opens in a new tab)</span>
                          </a>
                        </dd>
                      </div>
                    </dl>
                    <p className="sample-flag">{digest.label}</p>
                    <div className="card-live">
                      <LiveCaption />
                    </div>
                  </article>
                </div>
                <aside className="caption">
                  <p className="caption-lead">
                    Aggregators fall away. The two hits overlap. The name decrypts only once it is a tool.
                  </p>
                  <LiveCaption />
                  <figure className="source-still">
                    <img
                      src="/teams_output_example.png"
                      width={1024}
                      height={506}
                      alt="Sample Teams digest for Quibim, with title, website, audience, overview, features, pricing, and source."
                      loading="lazy"
                    />
                    <figcaption>The message this card copies. A sample, not a live post.</figcaption>
                  </figure>
                </aside>
              </div>
            </div>
          </section>

          <section className="scene statement" data-scene>
            <div className="pin" data-pin>
              <p className="verb">Search noise becomes a weekly digest.</p>
            </div>
          </section>

          {ACTS.map((act) => (
            <section className="scene step-scene" data-scene key={act.n}>
              <div className="pin step-pin" data-pin>
                <ActView act={act} />
              </div>
            </section>
          ))}

          <section className="scene steps-phone" data-scene>
            <div className="pin" data-pin>
              {ACTS.map((act, index) => (
                <div className={`act act-${index + 1}`} key={act.n}>
                  <ActView act={act} />
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>

      <footer className="outro" ref={outroRef}>
        <div className="marquee" aria-hidden="true">
          <div className="marquee-track">
            <span>{"█▓▒░•  ".repeat(18)}</span>
            <span>{"█▓▒░•  ".repeat(18)}</span>
          </div>
        </div>
        <p className="outro-mark">Digest</p>
        <nav className="outro-nav" aria-label="Leave the film">
          <a className="outro-link" href={GUIDE_HREF}>
            Read the usage guide
          </a>
          <a className="outro-link" href={GITHUB_HREF} rel="noreferrer">
            SerpApi Track 1 on GitHub
          </a>
        </nav>
        <p className="outro-quiet">Search noise, resolved once a week.</p>
      </footer>

      <div className="cursor" ref={cursorRef} aria-hidden="true">
        <span className="cursor-mark" />
        <span className="cursor-pill" data-label={CEREMONY} ref={pillRef}>
          {CEREMONY}
        </span>
      </div>

      <svg
        className="wave"
        ref={waveRef}
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path className="wave-pale" ref={paleRef} d="M 0 100 H 100 V 100 H 0 Z" />
        <path className="wave-deep" ref={deepRef} d="M 0 100 H 100 V 100 H 0 Z" />
      </svg>
    </div>
  );
}
