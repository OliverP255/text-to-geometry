/** Packed FlatIR (WGSL-aligned) from backend. */
export interface PackedFlatIR {
  instrs: Array<{ op: number; arg0: number; arg1: number; constIdx: number }>;
  transforms: number[];  // 8 per: tx,ty,tz,0, sx,sy,sz,minScale
  spheres: number[];     // 4 per: r,0,0,0
  boxes: number[];       // 4 per: hx,hy,hz,0
  planes: number[];      // 4 per: nx,ny,nz,d
  rootTemp: number;
}

export const FlatOp = {
  EvalSphere: 0,
  EvalBox: 1,
  EvalPlane: 2,
  CsgUnion: 3,
  CsgIntersect: 4,
  CsgSubtract: 5,
} as const;
