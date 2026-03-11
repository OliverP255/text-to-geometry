#include "frontend/lexer.h"
#include <cctype>
#include <cstdlib>
#include <cstring>

//Tokenize the dag into DSL

namespace frontend {

std::vector<Token> tokenize(const char* source) {
  std::vector<Token> tokens;
  const char* p = source;
  int line = 1;

  while (*p) {
    while (*p == ' ' || *p == '\t' || *p == '\r') ++p;
    if (*p == '#' || (*p == '/' && p[1] == '/')) {
      while (*p && *p != '\n') ++p;
      continue;
    }
    if (*p == '\n') {
      ++line;
      ++p;
      continue;
    }
    if (!*p) break;

    Token t;
    t.line = line;

    if (*p == 's' && std::isdigit(static_cast<unsigned char>(p[1]))) {
      ++p;
      unsigned long val = 0;
      while (std::isdigit(static_cast<unsigned char>(*p))) {
        val = val * 10 + (*p - '0');
        ++p;
      }
      t.type = TokenType::ShapeVar;
      t.varId = static_cast<uint32_t>(val);
      tokens.push_back(t);
      continue;
    }
    if (*p == 't' && std::isdigit(static_cast<unsigned char>(p[1]))) {
      ++p;
      unsigned long val = 0;
      while (std::isdigit(static_cast<unsigned char>(*p))) {
        val = val * 10 + (*p - '0');
        ++p;
      }
      t.type = TokenType::TransformVar;
      t.varId = static_cast<uint32_t>(val);
      tokens.push_back(t);
      continue;
    }

    if (*p == '-' &&
        (std::isdigit(static_cast<unsigned char>(p[1])) ||
         (p[1] == '.' && std::isdigit(static_cast<unsigned char>(p[2]))))) {
      char* end = nullptr;
      float f = std::strtof(p, &end);
      p = end;
      t.type = TokenType::Num;
      t.numValue = f;
      tokens.push_back(t);
      continue;
    }
    if (std::isdigit(static_cast<unsigned char>(*p)) ||
        (*p == '.' && std::isdigit(static_cast<unsigned char>(p[1])))) {
      char* end = nullptr;
      float f = std::strtof(p, &end);
      p = end;
      t.type = TokenType::Num;
      t.numValue = f;
      tokens.push_back(t);
      continue;
    }

    if (std::isalpha(static_cast<unsigned char>(*p)) ||
        *p == '_') {
      const char* start = p;
      while (std::isalnum(static_cast<unsigned char>(*p)) || *p == '_') ++p;
      t.ident.assign(start, p);
      t.type = TokenType::Ident;
      tokens.push_back(t);
      continue;
    }

    if (*p == '(') {
      t.type = TokenType::Lparen;
      ++p;
      tokens.push_back(t);
      continue;
    }
    if (*p == ')') {
      t.type = TokenType::Rparen;
      ++p;
      tokens.push_back(t);
      continue;
    }
    if (*p == ',') {
      t.type = TokenType::Comma;
      ++p;
      tokens.push_back(t);
      continue;
    }
    if (*p == '=') {
      t.type = TokenType::Eq;
      ++p;
      tokens.push_back(t);
      continue;
    }

    t.type = TokenType::Error;
    t.ident = "unexpected character";
    tokens.push_back(t);
    return tokens;
  }

  Token eof;
  eof.type = TokenType::Eof;
  eof.line = line;
  tokens.push_back(eof);
  return tokens;
}

}  // namespace frontend
