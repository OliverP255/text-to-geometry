#include "frontend/ir.h"
#include "frontend/lexer.h"
#include "kernel/builder.h"
#include "kernel/node.h"
#include <cmath>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

namespace frontend {

namespace {

class Parser {
 public:
  Parser(const std::vector<Token>& tokens) : tokens_(tokens), pos_(0) {}

  CompileResult parse() {
    CompileResult result;
    kernel::Builder b;

    if (tokens_.empty()) {
      result.error = "empty input";
      return result;
    }
    if (tokens_[0].type == TokenType::Error) {
      result.error = tokens_[0].ident;
      result.line = tokens_[0].line;
      return result;
    }

    kernel::ShapeH lastShape;
    bool hasReturn = false;
    int lastStmtLine = 0;

    while (!atEof()) {
      if (peek().type == TokenType::Error) {
        return fail(peek().ident, peek().line);
      }
      if (peek().type == TokenType::Ident && peek().ident == "return") {
        advance();
        if (peek().type != TokenType::Var) {
          return fail("expected %N after return", peek().line);
        }
        uint32_t id = peek().varId;
        advance();
        auto it = shapes_.find(id);
        if (it == shapes_.end()) {
          return fail("undefined shape %" + std::to_string(id), peek().line);
        }
        lastShape = it->second;
        hasReturn = true;
        if (!atEof()) {
          return fail("unexpected tokens after return", peek().line);
        }
        break;
      }

      if (peek().type != TokenType::Var) {
        return fail("expected %N = expr", peek().line);
      }
      uint32_t dstId = peek().varId;
      int stmtLine = peek().line;
      advance();

      if (peek().type != TokenType::Eq) {
        return fail("expected =", peek().line);
      }
      advance();

      if (peek().type != TokenType::Ident) {
        return fail("expected op (sphere, box, unite, etc.)", peek().line);
      }
      const std::string& op = peek().ident;
      advance();

      if (peek().type != TokenType::Lparen) {
        return fail("expected (", peek().line);
      }
      advance();

      if (op == "sphere") {
        float r = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectRparen(stmtLine);
        if (!ok_) return failFromOk();
        kernel::ShapeH s = b.sphere(r);
        shapes_[dstId] = s;
        lastShape = s;
        lastStmtLine = stmtLine;
      } else if (op == "box") {
        float x = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        float y = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        float z = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectRparen(stmtLine);
        if (!ok_) return failFromOk();
        kernel::ShapeH s = b.box({x, y, z});
        shapes_[dstId] = s;
        lastShape = s;
        lastStmtLine = stmtLine;
      } else if (op == "plane") {
        float nx = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        float ny = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        float nz = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        float d = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectRparen(stmtLine);
        if (!ok_) return failFromOk();
        kernel::ShapeH s = b.plane({nx, ny, nz}, d);
        shapes_[dstId] = s;
        lastShape = s;
        lastStmtLine = stmtLine;
      } else if (op == "translate") {
        float x = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        float y = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        float z = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectRparen(stmtLine);
        if (!ok_) return failFromOk();
        kernel::TransformH t = b.translate({x, y, z});
        transforms_[dstId] = t;
        lastStmtLine = stmtLine;
      } else if (op == "scale") {
        float x = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        float y = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        float z = expectNum(stmtLine);
        if (!ok_) return failFromOk();
        expectRparen(stmtLine);
        if (!ok_) return failFromOk();
        kernel::TransformH t = b.scale({x, y, z});
        transforms_[dstId] = t;
        lastStmtLine = stmtLine;
      } else if (op == "unite" || op == "intersect") {
        std::vector<kernel::ShapeH> args = expectShapeRefs(stmtLine);
        if (!ok_) return failFromOk();
        expectRparen(stmtLine);
        if (!ok_) return failFromOk();
        kernel::ShapeH s;
        if (op == "unite") {
          s = args.size() == 1 ? args[0] : b.unite(args);
        } else {
          s = args.size() == 1 ? args[0] : b.intersect(args);
        }
        shapes_[dstId] = s;
        lastShape = s;
        lastStmtLine = stmtLine;
      } else if (op == "subtract") {
        kernel::ShapeH a = expectShapeRef(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        kernel::ShapeH b_ = expectShapeRef(stmtLine);
        if (!ok_) return failFromOk();
        expectRparen(stmtLine);
        if (!ok_) return failFromOk();
        kernel::ShapeH s = b.subtract(a, b_);
        shapes_[dstId] = s;
        lastShape = s;
        lastStmtLine = stmtLine;
      } else if (op == "apply") {
        kernel::TransformH t = expectTransformRef(stmtLine);
        if (!ok_) return failFromOk();
        expectComma(stmtLine);
        if (!ok_) return failFromOk();
        kernel::ShapeH s = expectShapeRef(stmtLine);
        if (!ok_) return failFromOk();
        expectRparen(stmtLine);
        if (!ok_) return failFromOk();
        kernel::ShapeH out = b.apply(t, s);
        shapes_[dstId] = out;
        lastShape = out;
        lastStmtLine = stmtLine;
      } else {
        return fail("unknown op: " + op, stmtLine);
      }
    }

    if (!atEof()) {
      return fail("unexpected token at end", peek().line);
    }
    if (!hasReturn) {
      return fail("expected return statement", lastStmtLine);
    }
    if (!lastShape.valid()) {
      result.error = "no shape defined";
      return result;
    }

    kernel::FrozenDAG dag = {};
    b.freeze(lastShape, dag);

    result.ok = true;
    result.dag.rootId = dag.rootId;
    result.dag.headerCount = dag.headerCount;
    result.dag.payloadBytes = dag.payloadBytes;

    if (dag.headerCount > 0 && dag.headers) {
      size_t headerBytes = dag.headerCount * sizeof(kernel::NodeHeader);
      result.dagHeaders.resize(headerBytes);
      std::memcpy(result.dagHeaders.data(), dag.headers, headerBytes);
      result.dag.headers = result.dagHeaders.data();
    }
    if (dag.payloadBytes > 0 && dag.payloads) {
      result.dagPayloads.resize(dag.payloadBytes);
      std::memcpy(result.dagPayloads.data(), dag.payloads, dag.payloadBytes);
      result.dag.payloads = result.dagPayloads.data();
    }

    return result;
  }

 private:
  const std::vector<Token>& tokens_;
  size_t pos_;
  bool ok_ = true;
  std::string lastError_;
  int lastErrorLine_ = 0;
  std::unordered_map<uint32_t, kernel::ShapeH> shapes_;
  std::unordered_map<uint32_t, kernel::TransformH> transforms_;

  const Token& peek() const {
    return pos_ < tokens_.size() ? tokens_[pos_] : tokens_.back();
  }
  void advance() {
    if (pos_ < tokens_.size()) ++pos_;
  }
  bool atEof() const {
    return pos_ >= tokens_.size() || tokens_[pos_].type == TokenType::Eof;
  }

  CompileResult fail(const std::string& msg, int line) {
    CompileResult r;
    r.error = msg;
    r.line = line;
    return r;
  }

  CompileResult failFromOk() {
    CompileResult r;
    r.error = lastError_;
    r.line = lastErrorLine_;
    return r;
  }

  float expectNum(int line) {
    if (peek().type != TokenType::Num) {
      ok_ = false;
      lastError_ = "expected number";
      lastErrorLine_ = peek().line;
      return 0;
    }
    float v = peek().numValue;
    int numLine = peek().line;
    advance();
    if (!std::isfinite(v)) {
      ok_ = false;
      lastError_ = "invalid number (NaN or Inf)";
      lastErrorLine_ = numLine;
      return 0;
    }
    return v;
  }
  void expectComma(int line) {
    if (peek().type != TokenType::Comma) {
      ok_ = false;
      lastError_ = "expected ,";
      lastErrorLine_ = peek().line;
    } else {
      advance();
    }
  }
  void expectRparen(int line) {
    if (peek().type != TokenType::Rparen) {
      ok_ = false;
      lastError_ = "expected )";
      lastErrorLine_ = peek().line;
    } else {
      advance();
    }
  }

  kernel::ShapeH expectShapeRef(int line) {
    if (peek().type != TokenType::Var) {
      ok_ = false;
      lastError_ = "expected %N shape reference";
      lastErrorLine_ = peek().line;
      return kernel::ShapeH{};
    }
    uint32_t id = peek().varId;
    advance();
    auto it = shapes_.find(id);
    if (it == shapes_.end()) {
      ok_ = false;
      lastError_ = "undefined shape %" + std::to_string(id);
      lastErrorLine_ = peek().line;
      return kernel::ShapeH{};
    }
    return it->second;
  }

  kernel::TransformH expectTransformRef(int line) {
    if (peek().type != TokenType::Var) {
      ok_ = false;
      lastError_ = "expected %N transform reference";
      lastErrorLine_ = peek().line;
      return kernel::TransformH{};
    }
    uint32_t id = peek().varId;
    advance();
    auto it = transforms_.find(id);
    if (it == transforms_.end()) {
      ok_ = false;
      lastError_ = "undefined transform %" + std::to_string(id);
      lastErrorLine_ = peek().line;
      return kernel::TransformH{};
    }
    return it->second;
  }

  std::vector<kernel::ShapeH> expectShapeRefs(int line) {
    std::vector<kernel::ShapeH> out;
    kernel::ShapeH s = expectShapeRef(line);
    if (!ok_) return out;
    out.push_back(s);
    while (peek().type == TokenType::Comma) {
      advance();
      s = expectShapeRef(line);
      if (!ok_) return out;
      out.push_back(s);
    }
    return out;
  }
};

}  // namespace

CompileResult compileIR(const char* source) {
  std::vector<Token> tokens = tokenize(source);
  Parser p(tokens);
  return p.parse();
}

}  // namespace frontend
