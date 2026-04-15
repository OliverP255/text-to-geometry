/**
 * Three.js-based mesh renderer for B-Rep geometry.
 *
 * B-Rep produces explicit geometry (vertices/faces), so we use Three.js
 * mesh rendering instead of WebGPU ray marching used for SDFs.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { BRepMeshScene } from './types';

const MESH_COLOR = 0xe8ecf2;
const LAB_BG = 0x070c14;
const LAB_BG_TOP = 0x0d1628;
const RIM_COLOR = 0x6ab0ff;
const GRID_COLOR1 = 0x2a4a72;
const GRID_COLOR2 = 0x152238;

const CAM_OFFSET = new THREE.Vector3(2, 1.5, 3);

export class BRepRenderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer | null = null;
  private controls: OrbitControls | null = null;
  private mesh: THREE.Mesh | null = null;
  private brepCanvas: HTMLCanvasElement | null = null;

  private hemi: THREE.HemisphereLight;
  private ambient: THREE.AmbientLight;
  private rim: THREE.DirectionalLight;
  private ground: THREE.Mesh;
  private grid: THREE.GridHelper | null = null;
  private underlight: THREE.PointLight;

  private orbiting = false;
  private initialized = false;
  private visible = false;
  private hasMesh = false;

  constructor() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(LAB_BG);

    const c = new THREE.Color(LAB_BG);
    const c2 = new THREE.Color(LAB_BG_TOP);
    this.scene.fog = new THREE.Fog(c.getHex(), 4, 22);

    this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 10000);
    this.camera.position.set(100, 100, 100);

    this.hemi = new THREE.HemisphereLight(c2.getHex(), LAB_BG, 0.85);
    this.scene.add(this.hemi);

    this.ambient = new THREE.AmbientLight(0xc8dcff, 0.28);
    this.scene.add(this.ambient);

    this.rim = new THREE.DirectionalLight(RIM_COLOR, 0.55);
    this.rim.castShadow = true;
    this.rim.shadow.mapSize.set(2048, 2048);
    this.rim.shadow.camera.near = 0.5;
    this.rim.shadow.camera.far = 500;
    this.scene.add(this.rim);
    this.scene.add(this.rim.target);

    this.underlight = new THREE.PointLight(0x4fd0ff, 1.1, 0, 2);
    this.underlight.decay = 2;
    this.scene.add(this.underlight);

    const groundGeo = new THREE.PlaneGeometry(1, 1);
    const groundMat = new THREE.MeshStandardMaterial({
      color: LAB_BG,
      metalness: 0.05,
      roughness: 0.92,
    });
    this.ground = new THREE.Mesh(groundGeo, groundMat);
    this.ground.rotation.x = -Math.PI / 2;
    this.ground.receiveShadow = true;
    this.scene.add(this.ground);
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
      this.renderer.shadowMap.enabled = true;
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;

      this.controls = new OrbitControls(this.camera, this.brepCanvas);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;

      this.controls.addEventListener('start', () => {
        this.orbiting = true;
      });
      this.controls.addEventListener('end', () => {
        this.orbiting = false;
      });

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
      metalness: 0.06,
      roughness: 0.62,
      flatShading: false,
      side: THREE.FrontSide,
    });

    this.mesh = new THREE.Mesh(geometry, material);
    this.mesh.castShadow = true;
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

    const toCam = new THREE.Vector3().subVectors(this.camera.position, center).normalize();
    this.rim.position.copy(center).addScaledVector(toCam, -maxDim * 4);
    this.rim.target.position.copy(center);
    this.rim.shadow.camera.left = -maxDim * 3;
    this.rim.shadow.camera.right = maxDim * 3;
    this.rim.shadow.camera.top = maxDim * 3;
    this.rim.shadow.camera.bottom = -maxDim * 3;

    const fogNear = Math.max(2, maxDim * 0.45);
    const fogFar = Math.max(18, maxDim * 4.2);
    if (this.scene.fog instanceof THREE.Fog) {
      this.scene.fog.near = fogNear;
      this.scene.fog.far = fogFar;
    }

    const groundSize = Math.max(12, maxDim * 10);
    this.ground.scale.set(groundSize, groundSize, 1);
    const floorY = box.min.y - maxDim * 0.015;
    this.ground.position.set(center.x, floorY, center.z);

    if (this.grid) {
      this.scene.remove(this.grid);
      this.grid.geometry.dispose();
      const oldMat = this.grid.material;
      if (Array.isArray(oldMat)) oldMat.forEach((m) => m.dispose());
      else oldMat.dispose();
      this.grid = null;
    }
    const divisions = Math.min(48, Math.max(16, Math.round(groundSize / maxDim)));
    const grid = new THREE.GridHelper(groundSize, divisions, GRID_COLOR1, GRID_COLOR2);
    grid.position.set(center.x, floorY + 0.002, center.z);
    const gMat = grid.material;
    if (Array.isArray(gMat)) {
      gMat.forEach((m) => {
        m.transparent = true;
        m.opacity = 0.38;
      });
    } else {
      gMat.transparent = true;
      gMat.opacity = 0.38;
    }
    this.scene.add(grid);
    this.grid = grid;

    this.underlight.position.set(center.x, floorY + maxDim * 0.08, center.z);
    this.underlight.intensity = Math.min(1.8, 0.5 + maxDim * 0.25);
  }

  render(): void {
    if (!this.renderer || !this.brepCanvas || !this.initialized || !this.visible) {
      return;
    }

    if (this.mesh && !this.orbiting && this.hasMesh) {
      this.mesh.rotation.y += 0.002;
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