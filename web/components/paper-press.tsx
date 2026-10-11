"use client";

import { useEffect, useRef } from "react";

/**
 * A stack of sheets, always turning. Scroll press flattens it.
 * Reduced motion leaves the canvas unmounted in CSS and this loop never starts.
 */
export function PaperPress() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const narrow = window.matchMedia("(max-width: 800px)");
    let dead = false;
    let frame = 0;
    let dispose = () => {};
    const shouldRun = () =>
      !dead && !reduced.matches && !narrow.matches && document.visibilityState === "visible" && canvas.clientWidth > 0;

    void import("three").then((THREE) => {
      if (dead) return;
      const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 20);
      camera.position.set(0.2, 0.85, 4.4);

      const key = new THREE.DirectionalLight(0xfff3e4, 2.4);
      key.position.set(2.2, 3.2, 3.4);
      scene.add(key);
      scene.add(new THREE.AmbientLight(0xf6efe4, 0.9));

      const paper = new THREE.MeshStandardMaterial({ color: 0xf4efe4, roughness: 0.86, metalness: 0 });
      const accent = new THREE.MeshStandardMaterial({ color: 0x8d3d32, roughness: 0.55, metalness: 0 });
      const ink = new THREE.MeshStandardMaterial({ color: 0x2a241c, roughness: 0.7, metalness: 0 });
      const group = new THREE.Group();
      const plinth = new THREE.Mesh(
        new THREE.BoxGeometry(2.15, 0.12, 1.4),
        ink,
      );
      plinth.position.y = -0.22;
      group.add(plinth);
      const sheets: import("three").Mesh[] = [];
      for (let index = 0; index < 6; index += 1) {
        const sheet = new THREE.Mesh(new THREE.BoxGeometry(1.85, 0.045, 1.12), index === 5 ? accent : paper);
        sheet.position.y = index * 0.07;
        sheets.push(sheet);
        group.add(sheet);
      }
      const rule = new THREE.Mesh(new THREE.BoxGeometry(1.85, 0.012, 0.035), accent);
      rule.position.set(0, 0.28, 0.42);
      group.add(rule);
      scene.add(group);

      const fit = () => {
        const width = canvas.clientWidth || 1;
        const height = canvas.clientHeight || 1;
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
      };
      fit();
      const observer = new ResizeObserver(fit);
      observer.observe(canvas);

      const loop = (time: number) => {
        frame = 0;
        if (!shouldRun()) return;
        const host = canvas.closest(".stage-hero");
        const press = host ? Number.parseFloat(getComputedStyle(host).getPropertyValue("--press") || "0") || 0 : 0;
        group.rotation.y = time * 0.00032 + Math.sin(time * 0.0004) * 0.12;
        group.rotation.x = 0.42 - press * 0.28;
        sheets.forEach((sheet, index) => {
          const spread = (index - 2.5) * 0.07 * (1 - press);
          sheet.rotation.z = spread;
          sheet.position.x = spread * 0.8;
        });
        rule.position.y = 0.27 + Math.sin(time * 0.0015) * 0.01 * (1 - press);
        renderer.render(scene, camera);
        frame = window.requestAnimationFrame(loop);
      };
      const arm = () => {
        if (!shouldRun()) {
          if (frame) window.cancelAnimationFrame(frame);
          frame = 0;
          return;
        }
        if (!frame) frame = window.requestAnimationFrame(loop);
      };
      arm();
      reduced.addEventListener("change", arm);
      narrow.addEventListener("change", arm);
      document.addEventListener("visibilitychange", arm);

      dispose = () => {
        reduced.removeEventListener("change", arm);
        narrow.removeEventListener("change", arm);
        document.removeEventListener("visibilitychange", arm);
        observer.disconnect();
        renderer.dispose();
        paper.dispose();
        accent.dispose();
        ink.dispose();
        sheets.forEach((sheet) => sheet.geometry.dispose());
        plinth.geometry.dispose();
        rule.geometry.dispose();
      };
    });

    return () => {
      dead = true;
      if (frame) window.cancelAnimationFrame(frame);
      dispose();
    };
  }, []);

  return <canvas ref={canvasRef} className="paper-press" aria-hidden="true" />;
}
