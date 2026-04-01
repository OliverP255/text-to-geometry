#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace frontend {

enum class TokenType {
  ShapeVar,     // s0, s1, s2, ...
  TransformVar, // t0, t1, t2, ...
  Ident,        // sphere, box, cylinder, translate, scale, rotate, union, intersect, subtract, smooth_union, apply, return
  Num,          // float literal
  Lparen,
  Rparen,
  Comma,
  Eq,           // =
  Error,       // lex error
  Eof,
};

struct Token {
  TokenType type = TokenType::Eof;
  float numValue = 0;
  uint32_t varId = 0;  // for ShapeVar/TransformVar: the numeric part
  std::string ident;   // for Ident: the keyword
  int line = 0;
};

std::vector<Token> tokenize(const char* source);

}  // namespace frontend
