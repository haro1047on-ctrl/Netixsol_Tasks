import React, { useEffect, useRef } from "react";
import * as THREE from "three";

export default function ThreeCanvas() {
  const mountRef = useRef(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0, 3, 14);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Group for entire 3D structure
    const worldGroup = new THREE.Group();
    scene.add(worldGroup);

    // 1. Calming architectural ground grid
    const gridHelper = new THREE.GridHelper(24, 24, 0x5a7d6b, 0x18241d);
    gridHelper.position.y = -2;
    worldGroup.add(gridHelper);

    // 2. Central Architectural Modern Villa / Pavilion
    // Main Frosted Glass Tower
    const towerGeo = new THREE.BoxGeometry(3.5, 4.2, 3.5);
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: 0xa8c2b5,
      transparent: true,
      opacity: 0.35,
      roughness: 0.15,
      metalness: 0.5,
      transmission: 0.65,
      clearcoat: 1.0,
    });
    const tower = new THREE.Mesh(towerGeo, glassMat);
    tower.position.set(0, 0.2, 0);
    worldGroup.add(tower);

    // Wireframe edges on the tower for sharp architectural aesthetics
    const towerEdges = new THREE.EdgesGeometry(towerGeo);
    const edgeMat = new THREE.LineBasicMaterial({ color: 0x8fa89b, linewidth: 2 });
    const wireframe = new THREE.LineSegments(towerEdges, edgeMat);
    tower.add(wireframe);

    // Cantilever Balcony / Terrace (Rich architectural limestone)
    const balconyGeo = new THREE.BoxGeometry(5.2, 0.35, 4.5);
    const balconyMat = new THREE.MeshStandardMaterial({
      color: 0x1f2b23,
      metalness: 0.4,
      roughness: 0.4,
    });
    const balcony = new THREE.Mesh(balconyGeo, balconyMat);
    balcony.position.set(0.4, 0.6, 0.2);
    worldGroup.add(balcony);

    const balconyEdges = new THREE.EdgesGeometry(balconyGeo);
    const balconyWire = new THREE.LineSegments(balconyEdges, new THREE.LineBasicMaterial({ color: 0xd4c29d }));
    balcony.add(balconyWire);

    // Upper Penthouse Cube
    const penthouseGeo = new THREE.BoxGeometry(2.4, 2.0, 2.4);
    const penthouse = new THREE.Mesh(penthouseGeo, glassMat);
    penthouse.position.set(-0.5, 2.8, -0.3);
    worldGroup.add(penthouse);

    const penthouseEdges = new THREE.EdgesGeometry(penthouseGeo);
    const penthouseWire = new THREE.LineSegments(penthouseEdges, new THREE.LineBasicMaterial({ color: 0xc89d66 }));
    penthouse.add(penthouseWire);

    // 3. Orbital Rings (representing AI Intelligence & Nature Harmony)
    const ringGeo1 = new THREE.TorusGeometry(5.5, 0.03, 16, 100);
    const ringMat1 = new THREE.MeshBasicMaterial({ color: 0x8fa89b, transparent: true, opacity: 0.6 });
    const ring1 = new THREE.Mesh(ringGeo1, ringMat1);
    ring1.rotation.x = Math.PI / 3;
    worldGroup.add(ring1);

    const ringGeo2 = new THREE.TorusGeometry(6.5, 0.025, 16, 100);
    const ringMat2 = new THREE.MeshBasicMaterial({ color: 0xd4c4a8, transparent: true, opacity: 0.5 });
    const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
    ring2.rotation.y = Math.PI / 4;
    ring2.rotation.x = -Math.PI / 6;
    worldGroup.add(ring2);

    // 4. Floating Warm Champagne Dust Particles
    const particleCount = 200;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 20;
      positions[i + 1] = (Math.random() - 0.2) * 12;
      positions[i + 2] = (Math.random() - 0.5) * 20;
    }
    particleGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0xdfd2bf,
      size: 0.08,
      transparent: true,
      opacity: 0.75,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    worldGroup.add(particles);

    // 5. Architectural Ambient & Nature Lighting
    const ambientLight = new THREE.AmbientLight(0xfffaed, 1.3);
    scene.add(ambientLight);

    const warmLight = new THREE.PointLight(0xffecd1, 3.0, 20);
    warmLight.position.set(-6, 6, 6);
    scene.add(warmLight);

    const sageLight = new THREE.PointLight(0x8fa89b, 2.5, 20);
    sageLight.position.set(6, -2, 4);
    scene.add(sageLight);

    const amberLight = new THREE.PointLight(0xdeb076, 2.0, 15);
    amberLight.position.set(0, 8, -4);
    scene.add(amberLight);

    // Mouse Interaction
    let mouseX = 0;
    let mouseY = 0;
    let targetRotationX = 0;
    let targetRotationY = 0;

    const handleMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouseY = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
      targetRotationY = mouseX * 0.45;
      targetRotationX = mouseY * 0.25;
    };

    window.addEventListener("mousemove", handleMouseMove);

    // Handle Resize
    const handleResize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener("resize", handleResize);

    // Animation Loop
    let animId;
    const clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Smooth auto rotation + mouse parallax interpolation
      worldGroup.rotation.y += (targetRotationY + elapsedTime * 0.08 - worldGroup.rotation.y) * 0.04;
      worldGroup.rotation.x += (targetRotationX - worldGroup.rotation.x) * 0.04;

      // Independent ring rotations
      ring1.rotation.z = elapsedTime * 0.2;
      ring2.rotation.z = -elapsedTime * 0.15;

      // Subtle breathing float for structure
      tower.position.y = 0.2 + Math.sin(elapsedTime * 1.5) * 0.08;
      balcony.position.y = 0.6 + Math.sin(elapsedTime * 1.5) * 0.08;
      penthouse.position.y = 2.8 + Math.sin(elapsedTime * 1.5) * 0.08;

      particles.rotation.y = elapsedTime * 0.02;

      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", handleResize);
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className="w-full h-full relative cursor-grab active:cursor-grabbing"
      style={{ minHeight: "440px" }}
    />
  );
}
