#define GLAD_GL_IMPLEMENTATION
#include <glad/gl.h>
#include <GLFW/glfw3.h>

#include "frontend/ir.h"
#include "kernel/cuda_renderer.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

static const char* DEFAULT_DSL = R"(
%0 = sphere(1.0)
%1 = box(0.5, 0.5, 0.5)
%2 = unite(%0, %1)
return %2
)";

static const char* VERT_SRC = R"(#version 330 core
layout(location = 0) in vec2 aPos;
layout(location = 1) in vec2 aUV;
out vec2 vUV;
void main() {
  gl_Position = vec4(aPos, 0.0, 1.0);
  vUV = aUV;
}
)";

static const char* FRAG_SRC = R"(#version 330 core
in vec2 vUV;
out vec4 FragColor;
uniform sampler2D uTexture;
void main() {
  FragColor = texture(uTexture, vUV);
}
)";

struct ViewerState {
  int width = 1280;
  int height = 720;
  bool resized = true;
  std::vector<unsigned char> framebuf;
  kernel::CudaRenderer* renderer = nullptr;
};

static void framebufferSizeCallback(GLFWwindow* window, int w, int h) {
  if (w <= 0 || h <= 0) return;
  auto* state = static_cast<ViewerState*>(glfwGetWindowUserPointer(window));
  state->width = w;
  state->height = h;
  state->resized = true;
}

static void keyCallback(GLFWwindow* window, int key, int /*scancode*/,
                        int action, int /*mods*/) {
  if (key == GLFW_KEY_ESCAPE && action == GLFW_PRESS)
    glfwSetWindowShouldClose(window, GLFW_TRUE);
}

static GLuint compileShader(GLenum type, const char* src) {
  GLuint shader = glCreateShader(type);
  glShaderSource(shader, 1, &src, nullptr);
  glCompileShader(shader);
  GLint ok = 0;
  glGetShaderiv(shader, GL_COMPILE_STATUS, &ok);
  if (!ok) {
    char log[512];
    glGetShaderInfoLog(shader, sizeof(log), nullptr, log);
    fprintf(stderr, "Shader compile error: %s\n", log);
    std::exit(1);
  }
  return shader;
}

static GLuint createProgram(const char* vertSrc, const char* fragSrc) {
  GLuint vs = compileShader(GL_VERTEX_SHADER, vertSrc);
  GLuint fs = compileShader(GL_FRAGMENT_SHADER, fragSrc);
  GLuint prog = glCreateProgram();
  glAttachShader(prog, vs);
  glAttachShader(prog, fs);
  glLinkProgram(prog);
  GLint ok = 0;
  glGetProgramiv(prog, GL_LINK_STATUS, &ok);
  if (!ok) {
    char log[512];
    glGetProgramInfoLog(prog, sizeof(log), nullptr, log);
    fprintf(stderr, "Shader link error: %s\n", log);
    std::exit(1);
  }
  glDeleteShader(vs);
  glDeleteShader(fs);
  return prog;
}

static std::string readFile(const char* path) {
  std::ifstream f(path);
  if (!f.is_open()) {
    fprintf(stderr, "Cannot open file: %s\n", path);
    std::exit(1);
  }
  std::ostringstream ss;
  ss << f.rdbuf();
  return ss.str();
}

int main(int argc, char** argv) {
  const char* dslSource = DEFAULT_DSL;
  std::string fileContents;
  if (argc > 1) {
    fileContents = readFile(argv[1]);
    dslSource = fileContents.c_str();
  }

  auto result = frontend::compileIR(dslSource);
  if (!result.ok) {
    fprintf(stderr, "DSL error (line %d): %s\n", result.line,
            result.error.c_str());
    return 1;
  }

  kernel::FlatIR ir = kernel::lower(result.dag);

  if (!glfwInit()) {
    const char* desc = nullptr;
    glfwGetError(&desc);
    fprintf(stderr, "glfwInit failed: %s\n", desc ? desc : "unknown");
    return 1;
  }

  glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
  glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
  glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
#ifdef __APPLE__
  glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
#endif

  ViewerState state;
  GLFWwindow* window =
      glfwCreateWindow(state.width, state.height, "SDF Viewer", nullptr, nullptr);
  if (!window) {
    const char* desc = nullptr;
    glfwGetError(&desc);
    fprintf(stderr, "glfwCreateWindow failed: %s\n", desc ? desc : "unknown");
    glfwTerminate();
    return 1;
  }

  glfwMakeContextCurrent(window);
  glfwSwapInterval(1);

  int version = gladLoadGL(glfwGetProcAddress);
  if (!version) {
    fprintf(stderr, "Failed to initialize GLAD\n");
    glfwDestroyWindow(window);
    glfwTerminate();
    return 1;
  }
  printf("OpenGL %d.%d\n", GLAD_VERSION_MAJOR(version),
         GLAD_VERSION_MINOR(version));

  glfwSetWindowUserPointer(window, &state);
  glfwSetFramebufferSizeCallback(window, framebufferSizeCallback);
  glfwSetKeyCallback(window, keyCallback);

  glfwGetFramebufferSize(window, &state.width, &state.height);

  kernel::CudaRenderer renderer;
  state.renderer = &renderer;
  try {
    renderer.setScene(ir);
  } catch (const std::runtime_error& e) {
    fprintf(stderr, "CudaRenderer error: %s\n", e.what());
    glfwDestroyWindow(window);
    glfwTerminate();
    return 1;
  }

  GLuint program = createProgram(VERT_SRC, FRAG_SRC);

  // clang-format off
  float quadVerts[] = {
    // pos        uv
    -1.f, -1.f,   0.f, 0.f,
     1.f, -1.f,   1.f, 0.f,
     1.f,  1.f,   1.f, 1.f,

    -1.f, -1.f,   0.f, 0.f,
     1.f,  1.f,   1.f, 1.f,
    -1.f,  1.f,   0.f, 1.f,
  };
  // clang-format on

  GLuint vao, vbo;
  glGenVertexArrays(1, &vao);
  glGenBuffers(1, &vbo);
  glBindVertexArray(vao);
  glBindBuffer(GL_ARRAY_BUFFER, vbo);
  glBufferData(GL_ARRAY_BUFFER, sizeof(quadVerts), quadVerts, GL_STATIC_DRAW);
  glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), nullptr);
  glEnableVertexAttribArray(0);
  glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float),
                        reinterpret_cast<void*>(2 * sizeof(float)));
  glEnableVertexAttribArray(1);
  glBindVertexArray(0);

  GLuint texture;
  glGenTextures(1, &texture);
  glBindTexture(GL_TEXTURE_2D, texture);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
  glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
  glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, state.width, state.height, 0,
               GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
  glBindTexture(GL_TEXTURE_2D, 0);

  state.framebuf.resize(static_cast<size_t>(state.width) * state.height * 4);

  while (!glfwWindowShouldClose(window)) {
    glfwPollEvents();

    if (state.resized) {
      state.resized = false;
      glViewport(0, 0, state.width, state.height);
      state.framebuf.resize(
          static_cast<size_t>(state.width) * state.height * 4);
      glBindTexture(GL_TEXTURE_2D, texture);
      glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, state.width, state.height, 0,
                   GL_RGBA, GL_UNSIGNED_BYTE, nullptr);
      glBindTexture(GL_TEXTURE_2D, 0);
    }

    renderer.render(state.width, state.height, 0.f, 0.f, 5.f, 0.f, 0.f, 0.f,
                    state.framebuf.data());

    glBindTexture(GL_TEXTURE_2D, texture);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, state.width, state.height,
                    GL_RGBA, GL_UNSIGNED_BYTE, state.framebuf.data());

    glClear(GL_COLOR_BUFFER_BIT);
    glUseProgram(program);
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, texture);
    glBindVertexArray(vao);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    glBindVertexArray(0);

    glfwSwapBuffers(window);
  }

  glDeleteTextures(1, &texture);
  glDeleteBuffers(1, &vbo);
  glDeleteVertexArrays(1, &vao);
  glDeleteProgram(program);

  glfwDestroyWindow(window);
  glfwTerminate();
  return 0;
}
