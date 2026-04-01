/** Packed FlatIR (WGSL-aligned) from backend packForWebGPU. */
export interface PackedFlatIR {
  instrs: Array<{ op: number; arg0: number; arg1: number; constIdx: number }>;
  transforms: number[]; // 12 per: tx,ty,tz,0, sx,sy,sz,minScale, qx,qy,qz,qw
  spheres: number[];
  boxes: number[];
  cylinders: number[];
  smoothKs: number[];
  rootTemp: number;
}

export const FlatOp = {
  EvalSphere: 0,
  EvalBox: 1,
  CsgUnion: 2,
  CsgIntersect: 3,
  CsgSubtract: 4,
  EvalCylinder: 5,
  CsgSmoothUnion: 6,
} as const;

/** WGSL SDF scene from server / agent. */
export interface WGSLSdfScene {
  type: 'wgsl-sdf';
  code: string;
}

export type SceneData = WGSLSdfScene | PackedFlatIR;
