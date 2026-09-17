'use client';

import { useEffect, useRef, useState } from 'react';
import { useAppStore } from '../../lib/store';
import { mockFindings } from '../../mocks/data';
import { classifyAlgorithm, type Finding } from '../../types/crypto';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { Network, Sparkles, Layers, RefreshCw, Eye, Info, ZoomIn } from 'lucide-react';
import * as THREE from 'three';

export default function CryptoEstateGraphPage() {
  const { openDrawer } = useAppStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [use3D, setUse3D] = useState(true);
  const [hoveredNode, setHoveredNode] = useState<{ finding: Finding; x: number; y: number } | null>(null);

  useEffect(() => {
    if (!use3D || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const width = canvas.parentElement?.clientWidth || 900;
    const height = 550;

    // Three.js Scene Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0c10); // Observatory deep void

    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    camera.position.z = 24;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Ambient & Directional Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x2dd4bf, 2, 50); // Teal light
    pointLight.position.set(0, 5, 10);
    scene.add(pointLight);

    // Central Root System Node
    const rootGeo = new THREE.SphereGeometry(1.6, 32, 32);
    const rootMat = new THREE.MeshStandardMaterial({
      color: 0x2dd4bf,
      emissive: 0x0f766e,
      roughness: 0.3,
      metalness: 0.8,
    });
    const rootMesh = new THREE.Mesh(rootGeo, rootMat);
    scene.add(rootMesh);

    // Create File and Finding Nodes
    const nodeMeshes: Array<{ mesh: THREE.Mesh; finding: Finding }> = [];
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x334155, transparent: true, opacity: 0.6 });

    mockFindings.forEach((finding, idx) => {
      const angle = (idx / mockFindings.length) * Math.PI * 2;
      const radius = 8 + (idx % 3) * 3;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      const z = ((idx % 5) - 2) * 2;

      // Color mapping
      const cls = classifyAlgorithm(finding.family, finding.displayName, finding.risk.classicallyBroken);
      let colorHex = 0xf43f5e; // Shor red
      if (cls === 'classically-broken') colorHex = 0xd946ef; // magenta
      else if (cls === 'pqc') colorHex = 0x2dd4bf; // lattice teal
      else if (cls === 'grover') colorHex = 0xf59e0b; // amber
      else if (cls === 'quantum-safe-classical') colorHex = 0x38bdf8; // steel blue

      const nodeGeo = new THREE.SphereGeometry(finding.risk.score >= 60 ? 0.9 : 0.6, 16, 16);
      const nodeMat = new THREE.MeshStandardMaterial({
        color: colorHex,
        emissive: colorHex,
        emissiveIntensity: finding.risk.score >= 60 ? 0.6 : 0.2,
      });
      const mesh = new THREE.Mesh(nodeGeo, nodeMat);
      mesh.position.set(x, y, z);
      scene.add(mesh);
      nodeMeshes.push({ mesh, finding });

      // Connecting line to root
      const lineGeo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(x, y, z),
      ]);
      const line = new THREE.Line(lineGeo, lineMaterial);
      scene.add(line);
    });

    // Raycaster for interactions
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handleMouseMove = (event: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(nodeMeshes.map((n) => n.mesh));

      if (intersects.length > 0) {
        const target = nodeMeshes.find((n) => n.mesh === intersects[0].object);
        if (target) {
          setHoveredNode({
            finding: target.finding,
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
          });
        }
      } else {
        setHoveredNode(null);
      }
    };

    const handleClick = () => {
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(nodeMeshes.map((n) => n.mesh));
      if (intersects.length > 0) {
        const target = nodeMeshes.find((n) => n.mesh === intersects[0].object);
        if (target) {
          openDrawer(target.finding);
        }
      }
    };

    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('click', handleClick);

    // Animation Loop
    let animationId: number;
    const animate = () => {
      animationId = requestAnimationFrame(animate);

      // Subtle slow rotation of entire graph cluster
      scene.rotation.y += 0.003;
      scene.rotation.x = Math.sin(scene.rotation.y * 0.5) * 0.1;

      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animationId);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('click', handleClick);
      renderer.dispose();
    };
  }, [use3D, openDrawer]);

  return (
    <div className="space-y-4 font-mono text-xs">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-3">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <Network className="w-3.5 h-3.5" />
            <span>SCREEN 6 · CRYPTO ESTATE HIERARCHY GRAPH</span>
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            System → File → Cryptographic Asset Topology
          </h1>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            Node radius = Occurrences · Color = Semantic Class · Glow = Risk Score. Click any node to focus camera and open finding drawer.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setUse3D(!use3D)}
            className="px-3 py-1.5 rounded bg-[var(--surface-raised)] border border-[var(--border-prominent)] hover:border-[var(--crypto-pqc)] transition-colors text-xs flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
            <span>{use3D ? 'SWITCH TO 2D CANVAS' : 'SWITCH TO 3D WEBGL'}</span>
          </button>
        </div>
      </div>

      {/* Graph Visualizer Container */}
      <div className="relative border border-[var(--border-subtle)] rounded-xl overflow-hidden bg-[var(--surface-base)] shadow-2xl">
        {/* Canvas */}
        <canvas ref={canvasRef} className="w-full h-[550px] cursor-grab active:cursor-grabbing block" />

        {/* 2D Fallback Render if 3D is toggled off */}
        {!use3D && (
          <div className="absolute inset-0 p-8 flex flex-col justify-between bg-[var(--surface-base)]">
            <div className="text-center space-y-1">
              <span className="text-xs font-bold text-[var(--crypto-pqc)]">HIGH-DENSITY 2D CANVASS CLUSTER</span>
              <p className="text-[11px] text-[var(--text-muted)]">
                Optimized 2D fallback for low-power GPUs and prefers-reduced-motion mode.
              </p>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {mockFindings.map((f) => {
                const cls = classifyAlgorithm(f.family, f.displayName, f.risk.classicallyBroken);
                return (
                  <div
                    key={f.id}
                    onClick={() => openDrawer(f)}
                    className="p-3 bg-[var(--surface-card)] border border-[var(--border-subtle)] rounded cursor-pointer hover:border-[var(--crypto-pqc)] transition-colors"
                  >
                    <CryptoBadge semanticClass={cls} displayName={f.displayName} size="sm" />
                    <div className="mt-2 text-[10px] text-[var(--text-muted)] truncate">{f.location.path}</div>
                    <div className="mt-1 flex justify-between items-center text-[10px]">
                      <span>Score:</span>
                      <RiskBandBadge band={f.risk.band} score={f.risk.score} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Interactive Hover Tooltip */}
        {hoveredNode && (
          <div
            style={{ left: `${hoveredNode.x + 15}px`, top: `${hoveredNode.y + 15}px` }}
            className="pointer-events-none absolute z-20 rounded-lg border border-[var(--border-prominent)] bg-[var(--surface-overlay)] p-3 shadow-xl backdrop-blur-md max-w-xs space-y-1"
          >
            <div className="font-bold text-[var(--text-primary)]">{hoveredNode.finding.displayName}</div>
            <div className="text-[10px] text-[var(--text-muted)]">{hoveredNode.finding.location.path}</div>
            <div className="flex items-center gap-2 pt-1">
              <RiskBandBadge band={hoveredNode.finding.risk.band} score={hoveredNode.finding.risk.score} />
              <span className="text-[10px] text-[var(--text-secondary)]">Click to open drawer</span>
            </div>
          </div>
        )}

        {/* Legend Overlay */}
        <div className="absolute bottom-4 left-4 z-10 bg-[var(--surface-overlay)] border border-[var(--border-subtle)] p-2.5 rounded-lg backdrop-blur-md flex flex-wrap items-center gap-3 text-[10px] text-[var(--text-secondary)]">
          <span className="flex items-center gap-1.5 font-bold text-[var(--text-primary)]">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--crypto-shor)] inline-block" /> Shor
          </span>
          <span className="flex items-center gap-1.5 font-bold text-[var(--text-primary)]">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--crypto-broken)] inline-block hatch-broken" /> Broken
          </span>
          <span className="flex items-center gap-1.5 font-bold text-[var(--text-primary)]">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--crypto-grover)] inline-block" /> Grover
          </span>
          <span className="flex items-center gap-1.5 font-bold text-[var(--text-primary)]">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--crypto-safe-classical)] inline-block" /> Classical Safe
          </span>
          <span className="flex items-center gap-1.5 font-bold text-[var(--text-primary)]">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--crypto-pqc)] inline-block" /> PQC
          </span>
        </div>
      </div>
    </div>
  );
}
