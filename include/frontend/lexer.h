#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace frontend {

enum class TokenType {
  Var,      // %N
  Ident,    // sphere, box, plane, translate, scale, unite, intersect, subtract, apply, return
  Num,      // float literal
  Lparen,
  Rparen,
  Comma,
  Eq,       // =
  Error,    // lex error
  Eof,
};

struct Token {
  TokenType type = TokenType::Eof;
  float numValue = 0;
  uint32_t varId = 0;  // for Var: the %N value
  std::string ident;   // for Ident: the keyword
  int line = 0;
};

std::vector<Token> tokenize(const char* source);

}  // namespace frontend
