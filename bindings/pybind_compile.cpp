#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "frontend/ir.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/optimise.h"
#include "kernel/param_extract.h"
#include "kernel/unparse_dsl.h"
#include <string>
#include <vector>

namespace py = pybind11;

namespace {

// Convert FlatIR to Python dict
py::dict flatIRToDict(const kernel::FlatIR& ir) {
  py::dict d;

  // instrs: list of (op, arg0, arg1, constIdx)
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

  d["transforms"] = ir.transforms;
  d["spheres"] = ir.spheres;
  d["boxes"] = ir.boxes;
  d["planes"] = ir.planes;
  d["rootTemp"] = ir.rootTemp.id;

  return d;
}

// Convert Python dict to FlatIR (for deserialize)
kernel::FlatIR dictToFlatIR(const py::dict& d) {
  kernel::FlatIR ir;

  py::list instrs = d["instrs"];
  for (py::handle h : instrs) {
    py::dict i = h.cast<py::dict>();
    kernel::FlatInstr instr;
    instr.op = static_cast<kernel::FlatOp>(i["op"].cast<int>());
    instr.arg0 = i["arg0"].cast<uint32_t>();
    instr.arg1 = i["arg1"].cast<uint32_t>();
    instr.constIdx = i["constIdx"].cast<uint32_t>();
    ir.instrs.push_back(instr);
  }

  ir.transforms = d["transforms"].cast<std::vector<float>>();
  ir.spheres = d["spheres"].cast<std::vector<float>>();
  ir.boxes = d["boxes"].cast<std::vector<float>>();
  ir.planes = d["planes"].cast<std::vector<float>>();
  ir.rootTemp.id = d["rootTemp"].cast<uint32_t>();

  return ir;
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
    flatir_dict["transforms"] = ir.transforms;
    flatir_dict["spheres"] = ir.spheres;
    flatir_dict["boxes"] = ir.boxes;
    flatir_dict["planes"] = ir.planes;
  }, py::arg("flatir_dict"), py::arg("params"), "Write optimized params back into FlatIR dict");

  m.def("extractParams", [](const py::dict& flatir_dict) {
    kernel::FlatIR ir = dictToFlatIR(flatir_dict);
    return kernel::extractParams(ir);
  }, py::arg("flatir_dict"), "Extract raw trainable params from FlatIR dict");

  m.def("unparseDSL", [](const py::dict& flatir_dict) {
    kernel::FlatIR ir = dictToFlatIR(flatir_dict);
    return kernel::unparseDSL(ir);
  }, py::arg("flatir_dict"), "Convert FlatIR dict to DSL string");
}
