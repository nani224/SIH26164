'use client';

import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAppStore } from '../../lib/store';
import { fetchScanGraph, fetchScanFindings } from '../../lib/api';
import { classifyAlgorithm, type Finding, type GraphNode, type RiskBand } from '../../types/crypto';
import { CryptoBadge } from '../../components/CryptoBadge';
import { RiskBandBadge } from '../../components/RiskBandBadge';
import { Network, Sparkles, Layers, RefreshCw, Eye, Info, ZoomIn } from 'lucide-react';
import * as THREE from 'three';

export default function CryptoEstateGraphPage() {
  const { activeScanId, openDrawer } = useAppStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [use3D, setUse3D] = useState(true);
  const [hoveredNode, setHoveredNode] = useState<{ node: GraphNode; x: number; y: number } | null>(null);

  const { data: graphData, isLoading: isGraphLoading } = useQuery({
    queryKey: ['graph', activeScanId],
    queryFn: () => fetchScanGraph(activeScanId),
  });

  const { data: findingsData } = useQuery({
    queryKey: ['findings', activeScanId],
    queryFn: () => fetchScanFindings(activeScanId),
  });

  const findingsMap = useRef(new Map<string, Finding>());
  useEffect(() => {
    if (findingsData?.items) {
      findingsData.items.forEach((f) => findingsMap.current.set(f.displayName, f));
    }
  }, [findingsData]);

  useEffect(() => {
    if (!use3D || !canvasRef.current || !graphData?.nodes) return;

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

    // Create System, File, and Asset Nodes from API Graph
    const nodeMeshes: Array<{ mesh: THREE.Mesh; node: GraphNode }> = [];
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0x334155, transparent: true, opacity: 0.6 });

    const nodes = graphData.nodes;
    const rootNode = nodes.find((n) => n.type === 'system') || nodes[0];

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
    if (rootNode) nodeMeshes.push({ mesh: rootMesh, node: rootNode });

    const childNodes = nodes.filter((n) => n.id !== rootNode?.id);

    childNodes.forEach((node, idx) => {
      const angle = (idx / childNodes.length) * Math.PI * 2;
      const radius = node.type === 'file' ? 6 + (idx % 2) * 2 : 10 + (idx % 3) * 2;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      const z = ((idx % 5) - 2) * 2;

      // Color mapping
      let colorHex = 0xf43f5e; // Shor red
      if (node.semanticClass === 'classically-broken') colorHex = 0xd946ef; // magenta
      else if (node.semanticClass === 'pqc') colorHex = 0x2dd4bf; // lattice teal
      else if (node.semanticClass === 'grover') colorHex = 0xf59e0b; // amber
      else if (node.semanticClass === 'quantum-safe-classical') colorHex = 0x38bdf8; // steel blue

      const nodeGeo = new THREE.SphereGeometry(node.riskScore >= 60 ? 0.9 : 0.6, 16, 16);
      const nodeMat = new THREE.MeshStandardMaterial({
        color: colorHex,
        emissive: colorHex,
        emissiveIntensity: node.riskScore >= 60 ? 0.6 : 0.2,
      });
      const mesh = new THREE.Mesh(nodeGeo, nodeMat);
      mesh.position.set(x, y, z);
      scene.add(mesh);
      nodeMeshes.push({ mesh, node });

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
            node: target.node,
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
          });
        }
      } else {
        setHoveredNode(null);
      }
    };

    const handleClick = () => {
      if (hoveredNode) {
        // Look up corresponding finding if available to open drawer
        const f = findingsMap.current.get(hoveredNode.node.name);
        if (f) {
          openDrawer(f);
        }
      }
    };

    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('click', handleClick);

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      // Subtle scene rotation
      scene.rotation.y += 0.0015;
      scene.rotation.x = Math.sin(Date.now() * 0.0005) * 0.05;

      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('click', handleClick);
      renderer.dispose();
    };
  }, [use3D, graphData, openDrawer]);

  return (
    <div className="space-y-4 font-mono">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[var(--border-subtle)] pb-3">
        <div>
          <div className="text-xs text-[var(--crypto-pqc)] font-bold flex items-center gap-1.5 mb-1">
            <Network className="w-3.5 h-3.5" />
            <span>SCREEN 6 · CRYPTO ESTATE GRAPH (3D / 2D)</span>
          </div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            System → File → Cryptographic Asset Topology
          </h1>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            Spatial estate visualization. Powered by live graph API endpoint. Node size = severity, bloom = Mosca risk score.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={() => setUse3D(!use3D)}
            className="px-3 py-1.5 rounded border border-[var(--border-subtle)] bg-[var(--surface-raised)] hover:border-[var(--border-prominent)] text-[var(--text-primary)] transition-colors flex items-center gap-1.5"
          >
            <Layers className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
            <span>{use3D ? 'SWITCH TO 2D CANVAS FALLBACK' : 'SWITCH TO 3D WEBGL ENGINE'}</span>
          </button>
        </div>
      </div>

      {/* Main Canvas Card */}
      <div className="relative border border-[var(--border-subtle)] rounded-lg overflow-hidden bg-[#0a0c10] h-[550px]">
        {isGraphLoading ? (
          <div className="flex h-full items-center justify-center text-xs text-[var(--text-muted)] gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-[var(--crypto-pqc)]" />
            <span>INITIALIZING WEBGL SPATIAL MESH FROM API...</span>
          </div>
        ) : use3D ? (
          <canvas ref={canvasRef} className="w-full h-full cursor-grab active:cursor-grabbing" />
        ) : (
          /* 2D Canvas Fallback for low-end / reduced-motion environments */
          <div className="p-8 h-full flex flex-col justify-between">
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-2 text-xs text-[var(--text-secondary)]">
              <span>2D Hierarchical Projection Mode</span>
              <span>Root: NTRO Core</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-auto">
              {graphData?.nodes.slice(0, 9).map((node) => {
                const band: RiskBand = node.riskScore >= 60 ? 'critical' : node.riskScore >= 35 ? 'high' : node.riskScore >= 15 ? 'medium' : 'low';
                return (
                  <div
                    key={node.id}
                    className="p-3 rounded border border-[var(--border-subtle)] bg-[var(--surface-card)] flex items-center justify-between"
                  >
                    <div className="min-w-0 pr-2">
                      <span className="text-xs font-bold text-[var(--text-primary)] truncate block">
                        {node.name}
                      </span>
                      <span className="text-[10px] text-[var(--text-muted)] truncate block uppercase">
                        Type: {node.type} · {node.occurrences} instances
                      </span>
                    </div>
                    <RiskBandBadge band={band} score={node.riskScore} />
                  </div>
                );
              })}
            </div>

            <div className="text-[11px] text-[var(--text-muted)] flex items-center gap-2">
              <Info className="w-3.5 h-3.5 text-[var(--crypto-pqc)]" />
              <span>Accessible 2D fallback mode enabled for screen readers and prefers-reduced-motion.</span>
            </div>
          </div>
        )}

        {/* Hover Tooltip Overlay */}
        {hoveredNode && (() => {
          const band: RiskBand = hoveredNode.node.riskScore >= 60 ? 'critical' : hoveredNode.node.riskScore >= 35 ? 'high' : hoveredNode.node.riskScore >= 15 ? 'medium' : 'low';
          return (
            <div
              style={{ left: hoveredNode.x + 16, top: hoveredNode.y + 16 }}
              className="absolute z-30 pointer-events-none p-3 rounded-lg border border-[var(--border-prominent)] bg-[var(--surface-overlay)] backdrop-blur-md shadow-lg text-xs max-w-xs space-y-1.5 font-mono"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold text-[var(--text-primary)] truncate">{hoveredNode.node.name}</span>
                <RiskBandBadge band={band} score={hoveredNode.node.riskScore} />
              </div>
              <div className="text-[10px] text-[var(--text-muted)] truncate">
                Type: {hoveredNode.node.type}
              </div>
              <div className="text-[10px] text-[var(--text-muted)]">
                Occurrences: {hoveredNode.node.occurrences} · Class: {hoveredNode.node.semanticClass}
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
