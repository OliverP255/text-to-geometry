/**
 * Three.js-based mesh renderer for B-Rep geometry.
 *
 * B-Rep produces explicit geometry (vertices/faces), so we use Three.js
 * mesh rendering instead of WebGPU ray marching used for SDFs.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { BRepMeshScene } from './types';

const BG_COLOR = 0x1f1f1f;
const MESH_COLOR = 0xf2f2ed;

const CAM_OFFSET = new THREE.Vector3(2, 1.5, 3);

export class BRepRenderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer | null = null;
  private controls: OrbitControls | null = null;
  private mesh: THREE.Mesh | null = null;
  private brepCanvas: HTMLCanvasElement | null = null;

  private ambient: THREE.AmbientLight;
  private keyLight: THREE.DirectionalLight;
  private fillLight: THREE.DirectionalLight;

  private initialized = false;
  private visible = false;
  private hasMesh = false;

  constructor() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(BG_COLOR);

    this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 10000);
    this.camera.position.set(100, 100, 100);

    this.ambient = new THREE.AmbientLight(0xffffff, 0.5);
    this.scene.add(this.ambient);

    this.keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    this.keyLight.position.set(0.5, 0.8, 0.6).normalize();
    this.scene.add(this.keyLight);

    this.fillLight = new THREE.DirectionalLight(0xffffff, 0.6);
    this.fillLight.position.set(-0.4, 0.3, -0.5).normalize();
    this.scene.add(this.fillLight);
  }

  init(_canvas: HTMLCanvasElement): boolean {
    // Create a separate canvas for Three.js WebGL rendering
    this.brepCanvas = document.createElement('canvas');
    this.brepCanvas.id = 'brep-canvas';
    Object.assign(this.brepCanvas.style, {
      position: 'fixed',
      top: '0',
      left: '0',
      width: '100vw',
      height: '100vh',
      zIndex: '2',
      display: 'none',
      cursor: 'grab',
    });
    document.body.appendChild(this.brepCanvas);

    try {
      this.renderer = new THREE.WebGLRenderer({
        canvas: this.brepCanvas,
        antialias: true,
        alpha: false,
      });
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      this.controls = new OrbitControls(this.camera, this.brepCanvas);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;

      this.initialized = true;
      return true;
    } catch (e) {
      console.error('Failed to initialize Three.js renderer:', e);
      return false;
    }
  }

  show(): void {
    if (this.brepCanvas) {
      this.brepCanvas.style.display = 'block';
    }
    this.visible = true;
  }

  hide(): void {
    if (this.brepCanvas) {
      this.brepCanvas.style.display = 'none';
    }
    this.visible = false;
  }

  setMesh(sceneData: BRepMeshScene): void {
    if (this.mesh) {
      this.scene.remove(this.mesh);
      this.mesh.geometry.dispose();
      if (Array.isArray(this.mesh.material)) {
        this.mesh.material.forEach((m) => m.dispose());
      } else {
        this.mesh.material.dispose();
      }
    }

    const geometry = new THREE.BufferGeometry();

    const vertices = new Float32Array(sceneData.vertices.flat());
    const indices = new Uint32Array(sceneData.faces.flat());

    geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
    geometry.setIndex(new THREE.BufferAttribute(indices, 1));

    if (sceneData.normals && sceneData.normals.length > 0) {
      const normals = new Float32Array(sceneData.normals.flat());
      geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
    } else {
      geometry.computeVertexNormals();
    }

    const material = new THREE.MeshStandardMaterial({
      color: MESH_COLOR,
      metalness: 0.0,
      roughness: 0.5,
      flatShading: false,
      side: THREE.FrontSide,
    });

    this.mesh = new THREE.Mesh(geometry, material);
    this.scene.add(this.mesh);
    this.hasMesh = true;

    const box = new THREE.Box3(
      new THREE.Vector3(...sceneData.bounds.min),
      new THREE.Vector3(...sceneData.bounds.max)
    );
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z, 1e-6);

    const dist = maxDim * 2.2;
    const offset = CAM_OFFSET.clone().normalize().multiplyScalar(dist);

    if (this.controls) {
      this.controls.target.copy(center);
    }
    this.camera.position.copy(center).add(offset);
    this.controls?.update();
  }

  render(): void {
    if (!this.renderer || !this.brepCanvas || !this.initialized || !this.visible) {
      return;
    }

    this.controls?.update();
    this.renderer.render(this.scene, this.camera);
  }

  handleResize(): void {
    if (!this.renderer || !this.brepCanvas || !this.initialized) {
      return;
    }

    const dpr = Math.min(window.devicePixelRatio ?? 1, 2);
    const width = Math.floor(window.innerWidth * dpr);
    const height = Math.floor(window.innerHeight * dpr);

    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  }
}