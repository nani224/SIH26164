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

  useEffect(() => {
    if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      if (mediaQuery.matches) {
        setUse3D(false);
      }
      const handler = (e: MediaQueryListEvent) => {
        if (e.matches) setUse3D(false);
      };
      mediaQuery.addEventListener?.('change', handler);
      return () => mediaQuery.removeEventListener?.('change', handler);
    }
  }, []);

  const { data: graphData, isLoading: isGraphLoading, error: graphError } = useQuery({
    queryKey: ['graph', activeScanId],
    queryFn: () => fetchScanGraph(activeScanId),
  });

  const { data: findingsData } = useQuery({
    queryKey: ['findings', activeScanId],
    queryFn: () => fetchScanFindings(activeScanId),
  });

  // Keyed by finding id (matches an asset GraphNode's id 1:1 -- see
  // api/graph.py::build_graph) rather than displayName, which can collide
  // across multiple findings of the same algorithm.
  const findingsMap = useRef(new Map<string, Finding>());
  useEffect(() => {
    if (findingsData?.items) {
      findingsData.items.forEach((f) => findingsMap.current.set(f.id, f));
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

    const childNodes = nodes.filter((n) => n.id !== rootNode?.id);
    const count = childNodes.length;

    // High-performance instanced rendering: 5,000+ nodes rendered in 1 single draw call
    const instanceGeo = new THREE.SphereGeometry(0.7, 12, 12);
    const instanceMat = new THREE.MeshStandardMaterial({
      roughness: 0.4,
      metalness: 0.5,
    });
    const instancedMesh = new THREE.InstancedMesh(instanceGeo, instanceMat, Math.max(count, 1));
    const matrix = new THREE.Matrix4();
    const color = new THREE.Color();
    const linePoints: THREE.Vector3[] = [];

    childNodes.forEach((node, idx) => {
      const angle = (idx / count) * Math.PI * 2;
      const radius = node.type === 'file' ? 6 + (idx % 3) * 2 : 11 + (idx % 5) * 2;
      const x = Math.cos(angle) * radius;
      const y = Math.sin(angle) * radius;
      const z = ((idx % 7) - 3) * 2;

      // Color mapping: node.band is computed server-side (api/graph.py) from
      // the same Mosca thresholds as everywhere else -- never recompute them
      // here. GraphNode carries no algorithm family, so band is the only
      // real signal available for this color mapping.
      let colorHex = 0xf43f5e; // critical: Shor red
      if (node.band === 'high') colorHex = 0xf59e0b; // amber
      else if (node.band === 'medium') colorHex = 0x38bdf8; // steel blue
      else if (node.band === 'low') colorHex = 0x2dd4bf; // lattice teal

      const score = node.score ?? 0;
      const scale = node.band === 'critical' ? 1.3 : 0.9;
      matrix.makeScale(scale, scale, scale);
      matrix.setPosition(x, y, z);
      instancedMesh.setMatrixAt(idx, matrix);
      instancedMesh.setColorAt(idx, color.setHex(colorHex));

      linePoints.push(new THREE.Vector3(0, 0, 0), new THREE.Vector3(x, y, z));
    });

    instancedMesh.instanceMatrix.needsUpdate = true;
    if (instancedMesh.instanceColor) instancedMesh.instanceColor.needsUpdate = true;
    scene.add(instancedMesh);

    // Single draw call for all connecting lines
    const lineGeo = new THREE.BufferGeometry().setFromPoints(linePoints);
    const lineSegments = new THREE.LineSegments(lineGeo, lineMaterial);
    scene.add(lineSegments);

    // Raycaster for interactions
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handleMouseMove = (event: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects([rootMesh, instancedMesh]);

      if (intersects.length > 0) {
        const hit = intersects[0];
        if (hit.object === rootMesh && rootNode) {
          setHoveredNode({
            node: rootNode,
            x: event.clientX - rect.left,
            y: event.clientY - rect.top,
          });
        } else if (hit.object === instancedMesh && hit.instanceId !== undefined) {
          const target = childNodes[hit.instanceId];
          if (target) {
            setHoveredNode({
              node: target,
              x: event.clientX - rect.left,
              y: event.clientY - rect.top,
            });
          }
        }
      } else {
        setHoveredNode(null);
      }
    };

    const handleClick = () => {
      if (hoveredNode) {
        // Look up corresponding finding if available to open drawer
        const f = findingsMap.current.get(hoveredNode.node.id);
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
      instanceGeo.dispose();
      instanceMat.dispose();
      lineGeo.dispose();
      lineMaterial.dispose();
      rootGeo.dispose();
      rootMat.dispose();
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
        ) : graphError ? (
          <div className="flex h-full items-center justify-center p-8 text-center text-xs text-[var(--band-critical)]">
            <div className="border border-[var(--band-critical)] rounded-lg p-6 bg-[var(--surface-card)]">
              <p>Failed to query crypto estate topology from API endpoint.</p>
            </div>
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
                const nodeScore = node.score ?? 0;
                const band: RiskBand = node.band ?? 'low';
                const nodeLabel = node.label || 'Crypto Component';
                return (
                  <div
                    key={node.id}
                    className="p-3 rounded border border-[var(--border-subtle)] bg-[var(--surface-card)] flex items-center justify-between"
                  >
                    <div className="min-w-0 pr-2">
                      <span className="text-xs font-bold text-[var(--text-primary)] truncate block">
                        {nodeLabel}
                      </span>
                      <span className="text-[10px] text-[var(--text-muted)] truncate block uppercase">
                        Type: {node.type} · {node.occurrences} instances
                      </span>
                    </div>
                    <RiskBandBadge band={band} score={nodeScore} />
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
          const nodeScore = hoveredNode.node.score ?? 0;
          const band: RiskBand = hoveredNode.node.band ?? 'low';
          const nodeLabel = hoveredNode.node.label || 'Crypto Component';
          return (
            <div
              style={{ left: hoveredNode.x + 16, top: hoveredNode.y + 16 }}
              className="absolute z-30 pointer-events-none p-3 rounded-lg border border-[var(--border-prominent)] bg-[var(--surface-overlay)] backdrop-blur-md shadow-lg text-xs max-w-xs space-y-1.5 font-mono"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-bold text-[var(--text-primary)] truncate">{nodeLabel}</span>
                <RiskBandBadge band={band} score={nodeScore} />
              </div>
              <div className="text-[10px] text-[var(--text-muted)] truncate">
                Type: {hoveredNode.node.type}
              </div>
              <div className="text-[10px] text-[var(--text-muted)]">
                Occurrences: {hoveredNode.node.occurrences}
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
