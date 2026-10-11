"use client";

/**
 * Motion thesis, written before any tween.
 * Metaphor: the weekly is already on the desk. Scroll finishes a line on the card. It does not search an empty field.
 * Hero material: the Teams sample card, held beside the claim.
 * Playhead: scroll moves a red rule along the pipeline and resolves one slug on the card. Scroll up puts both back. The name, the sentence, and the image stay in the frame.
 * Ceremony: "Read the guide" censors, throws a short burst, then a two-path wave, then opens the guide. Modifier-clicks and the middle button skip it.
 * Still: reduced motion shows the card, the headline, the sentence, and the slug already reading "Posted to Teams".
 */

import { useLayoutEffect, useRef, type CSSProperties, type MouseEvent } from "react";

import type { DigestFile } from "@/lib/types";

const GUIDE_HREF = "/guide";
const GITHUB_HREF = "https://github.com/Adit-Jain-srm/SerpApi_Track1";
const CEREMONY = "Read the guide";
const SLUG = "Posted to Teams";

const GLYPHS = "█▓▒░•";
const WAVE_POINTS = 10;
const EASE = [0.22, 1, 0.36, 1] as const;

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
  for (let i = 0; i < 12; i += 1) {
    const bit = document.createElement("span");
    const angle = Math.random() * Math.PI * 2;
    const dist = 28 + Math.random() * 56;
    const dx = Math.cos(angle) * dist;
    const dy = Math.sin(angle) * dist + 14 + Math.random() * 28;
    bit.style.left = `${x}px`;
    bit.style.top = `${y}px`;
    bit.style.transitionDuration = `${0.5 + Math.random() * 0.2}s`;
    root.appendChild(bit);
    requestAnimationFrame(() => {
      bit.style.transform = `translate3d(${dx}px, ${dy}px, 0) scale(0.4)`;
      bit.style.opacity = "0";
    });
  }
  document.body.appendChild(root);
  window.setTimeout(() => root.remove(), 900);
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

export function Film({ digest }: { digest: DigestFile }) {
  const caption = digest.label || "Sample Digest Card — Illustrative. Not a discovery from today.";
  const spacerRef = useRef<HTMLDivElement>(null);
  const frontRef = useRef<HTMLElement>(null);
  const labelRef = useRef<HTMLSpanElement>(null);
  const waveRef = useRef<SVGSVGElement>(null);
  const paleRef = useRef<SVGPathElement>(null);
  const deepRef = useRef<SVGPathElement>(null);

  useLayoutEffect(() => {
    const spacer = spacerRef.current;
    const front = frontRef.current;
    const pale = paleRef.current;
    const deep = deepRef.current;
    const wave = waveRef.current;
    if (!spacer || !front || !pale || !deep || !wave) return;

    const reduceMq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const coarse = window.matchMedia("(pointer: coarse)").matches;
    const paths = [pale, deep];
    let vh = window.innerHeight;
    let travel = vh;
    let lastW = window.innerWidth;
    let raf = 0;
    let measureRaf = 0;
    let waveRaf = 0;
    let leaving = false;
    let intervals: number[] = [];

    const reduced = () => reduceMq.matches;

    const resetWave = () => {
      cancelAnimationFrame(waveRaf);
      const flat = Array.from({ length: WAVE_POINTS }, () => 100);
      const d = buildWave(flat);
      for (const path of paths) path.setAttribute("d", d);
      wave.style.visibility = "hidden";
      wave.style.pointerEvents = "none";
      wave.setAttribute("inert", "");
    };

    const clearMotion = () => {
      cancelAnimationFrame(raf);
      front.style.removeProperty("--sp");
      front.dataset.rest = "true";
    };

    const update = () => {
      if (reduced()) return;
      const y = window.scrollY;
      const sp = clamp(y / Math.max(travel, 1), 0, 1);
      front.style.setProperty("--sp", sp.toFixed(4));
      if (y < 2) front.dataset.rest = "true";
      else delete front.dataset.rest;
    };

    const measure = () => {
      if (reduced()) return;
      vh = window.innerHeight;
      travel = vh;
      spacer.style.height = `${vh + travel}px`;
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

    const onLeave = (event: Event) => {
      if (leaving || reduced()) return;
      leaving = true;
      const detail = (event as CustomEvent<{ x: number; y: number }>).detail;
      if (labelRef.current) intervals.push(censorLabel(labelRef.current));
      if (detail) spawnBurst(detail.x, detail.y);
      const delays = [0, 1].map(() =>
        Array.from({ length: WAVE_POINTS }, () => Math.random() * 220),
      );
      const points = [0, 1].map(() => Array.from({ length: WAVE_POINTS }, () => 100));
      const offset = [0, 140];
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
            const u = clamp((elapsed - 350 - offset[i] - delays[i][j]) / 720, 0, 1);
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
      document.querySelector(".burst")?.remove();
      resetWave();
      if (!reduced()) measure();
    };

    document.documentElement.dataset.motion = reduced() ? "reduce" : "full";
    resetWave();
    if (!reduced()) measure();
    else clearMotion();

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);
    window.addEventListener("film-leave", onLeave);
    window.addEventListener("pageshow", onPageShow);
    reduceMq.addEventListener("change", onMode);
    document.fonts?.ready.then(() => {
      if (!reduced()) scheduleMeasure();
    }).catch(() => undefined);

    return () => {
      cancelAnimationFrame(raf);
      cancelAnimationFrame(measureRaf);
      cancelAnimationFrame(waveRaf);
      for (const id of intervals) window.clearInterval(id);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
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

  return (
    <div className="film">
      <div className="spacer" ref={spacerRef} />
      <section className="front" data-rest="true" ref={frontRef} aria-label="Weekly digest">
        <header className="mast">
          <p className="mast-name">AI Tool Discovery Agent</p>
          <p className="mast-edition">Weekly digest</p>
        </header>
        <div className="rules" aria-hidden="true">
          <span className="rule-ink" />
          <span className="rule-red" />
        </div>
        <div className="spread">
          <h1 className="claim">
            It searches SerpApi for newly launched AI tools and posts a card to Teams, Slack, and the console.
          </h1>
          <figure className="plate">
            <div className="plate-frame">
              <img
                src="/teams_output_example.png"
                width={1024}
                height={506}
                alt="Sample Microsoft Teams card for a Quibim prostate-cancer tool, with website, audience, overview, features, pricing, and source. Not a discovery from today."
                fetchPriority="high"
              />
              <p className="slug" aria-hidden="true">
                <CipherLine text={SLUG} from={0.06} span={0.82} />
              </p>
            </div>
            <figcaption className="plate-cap">{caption}</figcaption>
          </figure>
          <div className="actions">
            <a
              className="control"
              href={GUIDE_HREF}
              aria-label={CEREMONY}
              onClick={onControlClick}
            >
              <span className="control-label" data-label={CEREMONY} ref={labelRef}>
                {CEREMONY}
              </span>
            </a>
            <a className="text-link" href={GITHUB_HREF} rel="noreferrer">
              Source on GitHub
            </a>
          </div>
        </div>
        <div className="proof">
          <p className="sr-only">SerpApi web and news, then extract, then Teams or Slack.</p>
          <p className="proof-row" aria-hidden="true">
            <span>SerpApi web + news</span>
            <span>then extract</span>
            <span>then Teams or Slack</span>
          </p>
          <div className="proof-mark" aria-hidden="true" />
        </div>
      </section>
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
