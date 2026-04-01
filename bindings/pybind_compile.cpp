#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "frontend/ir.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/optimise.h"
#include "kernel/pack_for_webgpu.h"
#include "kernel/param_extract.h"
#include "kernel/unparse_dsl.h"
#include <string>
#include <vector>

namespace py = pybind11;

namespace {

// Convert FlatIR to Python dict (semantic schema)
py::dict flatIRToDict(const kernel::FlatIR& ir) {
  py::dict d;

  py::list instrs;
  for (const auto& instr : ir.instrs) {
    py::dict i;
    i["op"] = static_cast<int>(instr.op);
    i["arg0"] = instr.arg0;
    i["arg1"] = instr.arg1;
    i["constIdx"] = instr.constIdx;
    instrs.append(i);
  }
  d["instrs"] = instrs;

  py::list transforms;
  for (const auto& t : ir.transforms) {
    py::dict item;
    item["tx"] = t.tx;
    item["ty"] = t.ty;
    item["tz"] = t.tz;
    item["sx"] = t.sx;
    item["sy"] = t.sy;
    item["sz"] = t.sz;
    item["qx"] = t.qx;
    item["qy"] = t.qy;
    item["qz"] = t.qz;
    item["qw"] = t.qw;
    transforms.append(item);
  }
  d["transforms"] = transforms;

  py::list spheres;
  for (const auto& s : ir.spheres) {
    py::dict item;
    item["r"] = s.r;
    spheres.append(item);
  }
  d["spheres"] = spheres;

  py::list boxes;
  for (const auto& b : ir.boxes) {
    py::dict item;
    item["hx"] = b.hx;
    item["hy"] = b.hy;
    item["hz"] = b.hz;
    boxes.append(item);
  }
  d["boxes"] = boxes;

  py::list cylinders;
  for (const auto& c : ir.cylinders) {
    py::dict item;
    item["r"] = c.r;
    item["h"] = c.h;
    cylinders.append(item);
  }
  d["cylinders"] = cylinders;

  py::list smoothKs;
  for (float k : ir.smoothKs) {
    smoothKs.append(k);
  }
  d["smoothKs"] = smoothKs;

  d["rootTemp"] = static_cast<int>(ir.rootTemp);

  return d;
}

// Convert Python dict to FlatIR
kernel::FlatIR dictToFlatIR(const py::dict& d) {
  kernel::FlatIR ir;

  py::list instrs = d["instrs"];
  for (py::handle h : instrs) {
    py::dict i = h.cast<py::dict>();
    kernel::FlatInstr instr;
    instr.op = static_cast<uint32_t>(i["op"].cast<int>());
    instr.arg0 = i["arg0"].cast<uint32_t>();
    instr.arg1 = i["arg1"].cast<uint32_t>();
    instr.constIdx = i["constIdx"].cast<uint32_t>();
    ir.instrs.push_back(instr);
  }

  py::list transforms = d["transforms"];
  for (py::handle h : transforms) {
    py::dict item = h.cast<py::dict>();
    kernel::FlatTransform t;
    t.tx = item["tx"].cast<float>();
    t.ty = item["ty"].cast<float>();
    t.tz = item["tz"].cast<float>();
    t.sx = item["sx"].cast<float>();
    t.sy = item["sy"].cast<float>();
    t.sz = item["sz"].cast<float>();
    t.qx = item.contains("qx") ? item["qx"].cast<float>() : 0.0f;
    t.qy = item.contains("qy") ? item["qy"].cast<float>() : 0.0f;
    t.qz = item.contains("qz") ? item["qz"].cast<float>() : 0.0f;
    t.qw = item.contains("qw") ? item["qw"].cast<float>() : 1.0f;
    ir.transforms.push_back(t);
  }

  py::list spheres = d["spheres"];
  for (py::handle h : spheres) {
    py::dict item = h.cast<py::dict>();
    ir.spheres.push_back({item["r"].cast<float>()});
  }

  py::list boxes = d["boxes"];
  for (py::handle h : boxes) {
    py::dict item = h.cast<py::dict>();
    ir.boxes.push_back(
        {item["hx"].cast<float>(), item["hy"].cast<float>(), item["hz"].cast<float>()});
  }

  if (d.contains("cylinders")) {
    py::list cylinders = d["cylinders"];
    for (py::handle h : cylinders) {
      py::dict item = h.cast<py::dict>();
      ir.cylinders.push_back({item["r"].cast<float>(), item["h"].cast<float>()});
    }
  }

  if (d.contains("smoothKs")) {
    py::list smoothKs = d["smoothKs"];
    for (py::handle h : smoothKs) {
      ir.smoothKs.push_back(h.cast<float>());
    }
  }

  ir.rootTemp = static_cast<uint32_t>(d["rootTemp"].cast<int>());

  return ir;
}

py::dict packedFlatIRToDict(const kernel::PackedFlatIR& packed) {
  py::dict d;
  py::list instrs;
  for (const auto& instr : packed.instrs) {
    py::dict i;
    i["op"] = static_cast<int>(instr.op);
    i["arg0"] = instr.arg0;
    i["arg1"] = instr.arg1;
    i["constIdx"] = instr.constIdx;
    instrs.append(i);
  }
  d["instrs"] = instrs;
  d["transforms"] = packed.transforms;
  d["spheres"] = packed.spheres;
  d["boxes"] = packed.boxes;
  d["cylinders"] = packed.cylinders;
  d["smoothKs"] = packed.smoothKs;
  d["rootTemp"] = static_cast<int>(packed.rootTemp);
  return d;
}

}  // namespace

PYBIND11_MODULE(text_to_geometry_bindings, m) {
  m.doc() = "text-to-geometry: DSL compile, FlatIR serialize/deserialize, writeBackParams";

  m.def("compile", [](const std::string& dsl) -> py::object {
    auto result = frontend::compileIR(dsl.c_str());
    if (!result.ok) {
      throw py::value_error(result.error);
    }
    auto opt = kernel::optimise(result.dag);
    auto flat = kernel::lower(opt.view);
    return flatIRToDict(flat);
  }, py::arg("dsl"), "Compile DSL string to FlatIR dict (compileIR + optimise + lower internally)");

  m.def("serialize", [](const py::dict& d) {
    py::module_ pickle = py::module_::import("pickle");
    return pickle.attr("dumps")(d);
  }, py::arg("flatir_dict"), "Serialize FlatIR dict to bytes");

  m.def("deserialize", [](const py::bytes& b) {
    py::module_ pickle = py::module_::import("pickle");
    return pickle.attr("loads")(b);
  }, py::arg("data"), "Deserialize bytes to FlatIR dict");

  m.def("writeBackParams", [](py::dict& flatir_dict, const std::vector<float>& params) {
    kernel::FlatIR ir = dictToFlatIR(flatir_dict);
    kernel::applyParams(ir, params);
    py::dict updated = flatIRToDict(ir);
    flatir_dict["transforms"] = updated["transforms"];
    flatir_dict["spheres"] = updated["spheres"];
    flatir_dict["boxes"] = updated["boxes"];
    flatir_dict["cylinders"] = updated["cylinders"];
    flatir_dict["smoothKs"] = updated["smoothKs"];
  }, py::arg("flatir_dict"), py::arg("params"), "Write optimized params back into FlatIR dict");

  m.def("extractParams", [](const py::dict& flatir_dict) {
    kernel::FlatIR ir = dictToFlatIR(flatir_dict);
    return kernel::extractParams(ir);
  }, py::arg("flatir_dict"), "Extract raw trainable params from FlatIR dict");

  m.def("unparseDSL", [](const py::dict& flatir_dict) {
    kernel::FlatIR ir = dictToFlatIR(flatir_dict);
    return kernel::unparseDSL(ir);
  }, py::arg("flatir_dict"), "Convert FlatIR dict to DSL string");

  m.def("packForWebGPU", [](const py::dict& flatir_dict) {
    kernel::FlatIR ir = dictToFlatIR(flatir_dict);
    kernel::PackedFlatIR packed = kernel::packForWebGPU(ir);
    return packedFlatIRToDict(packed);
  }, py::arg("flatir_dict"), "Pack FlatIR dict to WGSL-aligned format for WebGPU");
}
