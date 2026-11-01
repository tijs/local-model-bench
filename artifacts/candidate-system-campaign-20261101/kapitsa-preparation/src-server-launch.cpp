// kapitsa claude|codex|opencode|pi: a coding agent on Kapitsa in one command. It uses the Kapitsa already serving on
// 127.0.0.1:<port>, or starts one (`kapitsa serve` from this binary, logging to a file, with a context sized for
// agents), waits for it, runs the agent pointed at it (src/api/clients.cpp: its environment and options), and stops
// the server it started when the agent exits, with the agent's exit code.
#include "api/clients.h"
#include "gguf/gguf.h"
#include "gguf/import.h"
#include "server/cli.h"
#include "server/beam.h"
#include "server/picker.h"
#include "server/route.h"
#include "server/ui.h"
#include "util/log.h"
#include "util/term.h"

#include <httplib/httplib.h>

#include <fcntl.h>
#include <mach-o/dyld.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>

#include <chrono>
#include <climits>
#include <cstring>
#include <map>
#include <thread>

extern char** environ;

namespace ni {

using json = nlohmann::ordered_json;

namespace {

const char* kHelp =
    "kapitsa claude|codex|opencode|pi [--model M] [--port P] [--context N] [--loops N] [--api-key K] [agent arguments]\n"
    "                                 [-- agent arguments]\n\n"
    "Starts Claude Code, Codex, opencode or Pi on Kapitsa. If Kapitsa is already serving on 127.0.0.1:P (default\n"
    "8000), the agent uses that server; otherwise one is started for it (downloading the model the first time) with\n"
    "the model's own context (less where this Mac's memory is tight), and stopped when the agent exits. Its log is in\n"
    "%s/logs/serve-P.log.\n\n"
    "  --model M     the model to start (35b, 27b, 4b ...; kapitsa --help). Default: asked in a terminal; else the\n"
    "                model picked last if it is downloaded, else the best for this Mac\n"
    "  --port P      the server's port (default 8000)\n"
    "  --context N   its context: tokens, k or m of them (128k, 1m), or max, the model's limit (default: the model's limit, or\n"
    "                the most that keeps the draft model where memory is tight; --ctx N works too)\n"
    "  --loops N     Dory: loops per token, 1-4, when the agent asks for none (default 2; 4 is slower and more\n"
    "                accurate on agentic tasks)\n"
    "  --api-key K   the server's API key, if it was started with one\n\n"
    "Every other argument goes to the agent, e.g.\n"
    "  kapitsa claude -p \"what does this repo do?\"\n"
    "  kapitsa codex exec \"fix the failing test\"\n"
    "  kapitsa opencode run \"add a --verbose flag\"\n"
    "  kapitsa pi -p \"list the TODOs in this repo\"\n"
    "Arguments after -- go to the agent too (for its own --model, --port or --help).\n";

// The executable of this process, for the server it starts
std::string self_path() {
  char buf[PATH_MAX];
  uint32_t n = sizeof buf;
  if (_NSGetExecutablePath(buf, &n) != 0) return "kapitsa";
  char real[PATH_MAX];
  return realpath(buf, real) ? real : buf;
}

// What a GET answers: -1 when nothing listens, else the HTTP status and body
struct Got {
  int status = -1;
  std::string body;
};
Got get(int port, const std::string& path, const std::string& key, int timeout_s) {
  httplib::Client c("127.0.0.1", port);
  c.set_connection_timeout(timeout_s, 0);
  c.set_read_timeout(timeout_s, 0);
  httplib::Headers h;
  if (!key.empty()) h.emplace("Authorization", "Bearer " + key);
  auto r = c.Get(path, h);
  Got g;
  if (r) g.status = r->status, g.body = r->body;
  return g;
}

struct Running {
  std::string model;
  int context = 0;
};

// The Kapitsa on the port: 1 found (*out set), 0 nothing listens, -1 something else answers (*why says what)
int probe(int port, const std::string& key, Running* out, std::string* why) {
  const Got g = get(port, "/v1/models", key, 3);
  if (g.status < 0) return 0;
  if (g.status == 401) {
    *why = "The Kapitsa on port " + std::to_string(port) + " needs an API key: pass --api-key KEY.";
    return -1;
  }
  const json j = json::parse(g.body, nullptr, false);
  if (g.status == 200 && j.is_object() && j.contains("data") && j["data"].is_array() && !j["data"].empty() &&
      j["data"][0].is_object() && j["data"][0].value("owned_by", "") == "nace") {
    const json& m = j["data"][0];
    out->model = m.value("id", "");
    out->context = m.contains("context_length") && m["context_length"].is_number_integer() ? m["context_length"].get<int>() : 0;
    // what one conversation can hold within the memory budget, if less
    if (m.contains("context_fit") && m["context_fit"].is_number_integer() && m["context_fit"].get<int>() > 0)
      out->context = std::min(out->context, m["context_fit"].get<int>());
    if (!out->model.empty() && out->context > 0) return 1;
  }
  *why = "Port " + std::to_string(port) + " is in use by another program. Pass --port with a free port.";
  return -1;
}

// The Homebrew service (`brew services start kapitsa`: a launchd job running `kapitsa serve` without --model at each
// login and again whenever it ends on an error or a signal) when it serves on `port`: the command that stops it, else
// "". A server found on the port is then most likely that one, which the agent's exit leaves running and Activity
// Monitor's Quit only restarts (issue 653). Its job's label is sh.brew.kapitsa in current Homebrew (the reporter's),
// homebrew.mxcl.kapitsa in older ones.
std::string brew_service_stop(int port) {
  const char* home = getenv("HOME");
  std::vector<std::pair<std::string, std::string>> jobs;
  for (const char* label : {"sh.brew.kapitsa", "homebrew.mxcl.kapitsa"}) {
    if (home && *home) jobs.push_back({std::string(home) + "/Library/LaunchAgents/" + label + ".plist", "brew services stop kapitsa"});
    jobs.push_back({std::string("/Library/LaunchDaemons/") + label + ".plist", "sudo brew services stop kapitsa"});
  }
  for (const auto& [plist, stop] : jobs) {
    FILE* f = fopen(plist.c_str(), "rb");
    if (!f) continue;
    std::string s;
    char buf[4096];
    for (size_t n; (n = fread(buf, 1, sizeof buf, f)) > 0;) s.append(buf, n);
    fclose(f);
    // its port: a --port among its arguments (<string>--port</string> <string>P</string>), else serve's 8000
    int p = 8000;
    if (size_t a = s.find("<string>--port</string>"); a != std::string::npos)
      if ((a = s.find("<string>", a + 23)) != std::string::npos) p = atoi(s.c_str() + a + 8);
    if (p == port) return stop;
  }
  return "";
}

std::string last_log_line(const std::string& path) {
  FILE* f = fopen(path.c_str(), "rb");
  if (!f) return "";
  fseek(f, 0, SEEK_END);
  const long size = ftell(f);
  const long from = size > 4096 ? size - 4096 : 0;
  fseek(f, from, SEEK_SET);
  std::string s(size_t(size - from), '\0');
  s.resize(fread(s.data(), 1, s.size(), f));
  fclose(f);
  while (!s.empty() && (s.back() == '\n' || s.back() == '\r' || s.back() == ' ')) s.pop_back();
  size_t a = s.find_last_of("\n\r");
  s = a == std::string::npos ? s : s.substr(a + 1);
  if (s.rfind("[kapitsa] ", 0) == 0) s = s.substr(10);
  size_t e;
  while ((e = s.find("\033[")) != std::string::npos) {  // a terminal escape (the download's progress line)
    size_t k = e + 2;
    while (k < s.size() && !isalpha(uint8_t(s[k]))) ++k;
    s.erase(e, k + 1 - e);
  }
  return s;
}

void print_tail(const std::string& path, int lines) {
  FILE* f = fopen(path.c_str(), "rb");
  if (!f) return;
  std::vector<std::string> v;
  char buf[4096];
  while (fgets(buf, sizeof buf, f)) {
    v.push_back(buf);
    if (int(v.size()) > lines) v.erase(v.begin());
  }
  fclose(f);
  for (const auto& l : v) fputs(l.c_str(), stderr);
}

// What the server's log says about the requests since `from` (its "chat: prompt N (cached M) ..., G tokens in T ms"
// lines), for the line after the agent exits
struct Session {
  int requests = 0;
  long prompt = 0, cached = 0, out = 0;
  double decode_ms = 0;
};
Session session_since(const std::string& path, long from) {
  Session s;
  FILE* f = fopen(path.c_str(), "rb");
  if (!f) return s;
  fseek(f, 0, SEEK_END);
  if (ftell(f) < from) from = 0;  // a new log since (another server)
  fseek(f, from, SEEK_SET);
  char buf[4096];
  while (fgets(buf, sizeof buf, f)) {
    const char* p = strstr(buf, "chat: prompt ");
    if (!p) continue;
    int n = 0, c = 0;
    if (sscanf(p, "chat: prompt %d (cached %d)", &n, &c) != 2) continue;
    const char* t = strstr(p, " tokens in ");
    if (!t) continue;
    const char* q = t;
    while (q > p && q[-1] != ' ') --q;
    int g = atoi(q);
    double ms = atof(t + 11);
    ++s.requests, s.prompt += n, s.cached += c, s.out += g, s.decode_ms += ms;
  }
  fclose(f);
  return s;
}

// Writes `content` to `path` (its folder made first), unless the file already holds it; "" or what went wrong
std::string write_file(const std::string& path, const std::string& content) {
  if (FILE* f = fopen(path.c_str(), "rb")) {
    std::string cur(content.size() + 1, '\0');
    cur.resize(fread(cur.data(), 1, cur.size(), f));
    fclose(f);
    if (cur == content) return "";
  }
  for (size_t p = path.find('/', 1); p != std::string::npos; p = path.find('/', p + 1)) mkdir(path.substr(0, p).c_str(), 0755);
  const std::string tmp = path + ".tmp." + std::to_string(getpid());
  FILE* f = fopen(tmp.c_str(), "wb");
  if (!f) return strerror(errno);
  const bool ok = fwrite(content.data(), 1, content.size(), f) == content.size();
  if (fclose(f) != 0 || !ok || rename(tmp.c_str(), path.c_str()) != 0) {
    const std::string e = strerror(errno);
    unlink(tmp.c_str());
    return e;
  }
  return "";
}

long file_size_of(const std::string& path) {
  struct stat st;
  return stat(path.c_str(), &st) == 0 ? long(st.st_size) : 0;
}

volatile sig_atomic_t g_signal = 0;  // a stop signal while the server starts
pid_t g_child_group = 0;             // where stop signals go while the agent runs

void note_signal(int sig) { g_signal = sig; }
void forward_signal(int sig) {
  if (g_child_group > 0) kill(-g_child_group, sig);
}

std::vector<char*> c_strings(std::vector<std::string>& v) {
  std::vector<char*> p;
  for (auto& s : v) p.push_back(s.data());
  p.push_back(nullptr);
  return p;
}

// The client's major version (opencode changed how it reads its configuration in 2.0), -1 when unknown
int major_version(const std::string& path) {
  int fd[2];
  if (pipe(fd) != 0) return -1;
  const pid_t pid = fork();
  if (pid == 0) {
    dup2(fd[1], 1);
    const int null = open("/dev/null", O_RDWR);
    dup2(null, 0);
    dup2(null, 2);
    close(fd[0]);
    close(fd[1]);
    execl(path.c_str(), path.c_str(), "--version", (char*)nullptr);
    _exit(127);
  }
  close(fd[1]);
  std::string out;
  char buf[256];
  ssize_t n;
  const auto t0 = std::chrono::steady_clock::now();
  fcntl(fd[0], F_SETFL, O_NONBLOCK);
  while (std::chrono::steady_clock::now() - t0 < std::chrono::seconds(5)) {
    n = read(fd[0], buf, sizeof buf);
    if (n > 0) out.append(buf, size_t(n));
    else if (n == 0) break;
    else std::this_thread::sleep_for(std::chrono::milliseconds(20));
  }
  close(fd[0]);
  kill(pid, SIGKILL);
  waitpid(pid, nullptr, 0);
  for (size_t i = 0; i < out.size(); ++i)
    if (isdigit(uint8_t(out[i])) && (i == 0 || !isalnum(uint8_t(out[i - 1])) || out[i - 1] == 'v'))
      return atoi(out.c_str() + i);
  return -1;
}

}  // namespace

std::string find_in_path(const std::string& name) {
  const char* p = getenv("PATH");
  std::string path = p ? p : "/usr/bin:/bin";
  size_t a = 0;
  while (a <= path.size()) {
    size_t b = path.find(':', a);
    if (b == std::string::npos) b = path.size();
    const std::string dir = path.substr(a, b - a);
    const std::string f = (dir.empty() ? "." : dir) + "/" + name;
    struct stat st;
    if (stat(f.c_str(), &st) == 0 && S_ISREG(st.st_mode) && access(f.c_str(), X_OK) == 0) return f;
    a = b + 1;
  }
  return "";
}

int launch_agent(const std::string& name, int argc, char** argv, int first) {
  const std::string help = "kapitsa " + name + " --help";
  std::string model, key;
  int port = 8000, ctx = 0, loops = 0;
  bool yes = false;
  std::vector<std::string> args;
  for (int i = first; i < argc; ++i) {
    const std::string a = argv[i];
    auto value = [&](const char* opt) -> std::string {
      const std::string o = opt;
      if (a == o) {
        if (i + 1 >= argc) usage_error(o + " needs a value", help.c_str());
        return argv[++i];
      }
      return a.substr(o.size() + 1);  // --opt=value
    };
    auto is = [&](const char* opt) { return a == opt || a.rfind(std::string(opt) + "=", 0) == 0; };
    if (a == "--") {
      for (++i; i < argc; ++i) args.push_back(argv[i]);
      break;
    }
    if (a == "--help" || a == "-h") {
      if (term::fancy()) {
        char b[4096];
        snprintf(b, sizeof b, kHelp, hub::tilde(hub::home_dir()).c_str());
        std::string h = b;  // in a terminal, without --model, it asks which model to start
        h.insert(h.find("\n\nEvery other argument"), "\n  --yes         don't ask which model to start: the best for this Mac");
        term::help(h);
      } else {
        printf(kHelp, hub::tilde(hub::home_dir()).c_str());
      }
      return 0;
    }
    if (a == "--yes") yes = true;
    else if (is("--model")) model = value("--model");
    else if (is("--port")) port = to_int("--port", value("--port"), help.c_str());
    else if (is("--context") || is("--ctx")) {
      std::string why;
      ctx = parse_context(value(is("--context") ? "--context" : "--ctx"), &why);
      if (!ctx) usage_error(why, help.c_str());
    }
    else if (is("--loops")) {
      loops = to_int("--loops", value("--loops"), help.c_str());
      if (loops < 1 || loops > 4) usage_error("--loops: 1 to 4", help.c_str());
    }
    else if (is("--api-key")) key = value("--api-key");
    else args.push_back(a);
  }
  if (port < 1 || port > 65535) usage_error("--port must be 1-65535", help.c_str());

  // the agent first: no server is started for one that is not installed
  const std::string path = find_in_path(name);
  if (path.empty()) return fail(api::agent_install_hint(name));
  if (!model.empty() && gguf::is_gguf_file(expand_home(model))) {  // a GGUF: its conversion, made on first use
    try {
      gguf::ImportOptions io;
      io.file = expand_home(model);
      model = gguf::import_model(io);
    } catch (const gguf::Error& e) {
      return fail(e.what(), 2);
    }
  }

  Running run;
  std::string why;
  pid_t server = 0;
  std::vector<std::pair<std::string, int>> switch_to;  // Pi's other models (api::AgentServer::switch_to)
  const std::string log = hub::home_dir() + "/logs/serve-" + std::to_string(port) + ".log";
  const int found = probe(port, key, &run, &why);
  if (found < 0) return fail(why);
  // no --model in a terminal: which model, asked (picker.h), unless a server already runs on the port
  const bool ask = model.empty() && ui::can_prompt(yes);
  if (found == 1) {
    if (!model.empty()) {
      hub::ModelRef want;
      try {
        want = hub::resolve(expand_home(model));
      } catch (const hub::Error& e) {
        return fail(e.what(), 2);
      }
      if (want.id != run.model && want.name != run.model)
        return fail("The Kapitsa on port " + std::to_string(port) + " serves " + run.model + ", not " + model +
                    ". Stop it, or pass --port to start " + model + " on another port.");
      ui::remember(want);
    }
    const std::string asked = ctx == kContextMax ? "max" : term::context(ctx);
    if (ctx != 0 && ctx != run.context && term::fancy())
      ui::warning("The server on port " + std::to_string(port) + " is already running with a " + term::context(run.context) +
                  "-token context; --context " + asked + " applies to a server this command starts.");
    else if (ctx != 0 && ctx != run.context)
      fprintf(stderr, "kapitsa: the server on port %d is already running with a %s-token context; --context %s applies to "
              "a server this command starts.\n", port, term::context(run.context).c_str(), asked.c_str());
    if (loops > 0)
      fprintf(stderr, "kapitsa: the server on port %d is already running; --loops %d applies to a server this command "
              "starts.\n", port, loops);
  } else {
    // start one: the model (downloaded first, with its progress here), a context sized for agents, then `serve`
    EngineOptions opt;
    const size_t budget = default_mem_budget();
    if (ask) {
      const auto pick = ui::pick_model(opt, budget, "kapitsa " + name, ctx);
      if (!pick) return 130;
      model = pick->model;  // as if --model named it
      ctx = pick->context;  // and --context
    }
    hub::ModelRef ref;
    std::string serve_model = model;
    bool elsewhere = false;  // a Mac on the network runs it whole: the server sends its requests there (route.h)
    try {
      // nobody asked: the model picked last when it is downloaded, rather than the best for this Mac downloaded again
      const std::optional<hub::ModelRef> last = model.empty() && !yes ? ui::last_pick_here() : std::nullopt;
      if (last) {
        ref = *last;
        serve_model = hub::short_name(*ref.model, *ref.variant);
        const std::string say = ref.name + ", the model picked last (downloaded). --model picks another.";
        if (term::fancy()) ui::note(say);
        else fprintf(stderr, "kapitsa: no --model given: %s\n", say.c_str());
      } else if (model.empty()) {
        std::string w;
        if (!best_model(opt, budget, &ref, &w)) return fail(w);
        serve_model = ref.model && ref.variant ? hub::short_name(*ref.model, *ref.variant) : ref.dir;
      } else {
        ref = for_this_mac(hub::resolve(expand_home(model)), opt, budget);
        ui::remember(ref);
      }
      if (!runs_whole_here(ref, opt, budget)) {  // then nothing downloads here
        cluster::Browser b;
        b.wait(1.5);
        elsewhere = cluster::pick_server(b.peers(), model_key(ref), false).has_value();
      }
      hub::PullOptions po;
      if (ui::can_prompt(yes)) po.make_room = ui::make_room;  // out of disk space: which models to delete, asked
      if (!elsewhere) hub::ensure(ref, po);
    } catch (const hub::Stopped& e) {
      if (term::fancy()) term::status(""), ui::warning(e.what());
      else fprintf(stderr, "\n%s\n", e.what());
      return 130;
    } catch (const hub::Error& e) {
      return fail(e.what());
    }
    if (!elsewhere)
      if (const std::string why = unsupported_model(ref.dir); !why.empty()) return fail(why);
    // Pi's server switches models (--allow-switch): Pi lists every downloaded model, and picking one there loads it in
    // place of this one, with the context asked for (as each model's own: 0 its default, max its limit)
    const bool switching = name == "pi" && !elsewhere;
    const int ctx_asked = ctx;
    // the context first (serve then picks the slots, and caps a context past the model's limit, saying so): as
    // asked, max the model's limit, else serve's default for this Mac (default_context)
    if (elsewhere) {  // that Mac's server has its context
    } else if (ctx == kContextMax) {
      ctx = model_context_limit(ref.dir);
      if (ctx <= 0)
        return fail(serve_model + " does not state the context it was trained for (max_position_embeddings in its "
                    "config.json), so --context max has no size here: give it in tokens (--context 128k).", 2);
    } else if (ctx == 0) {
      ctx = default_context(ref.dir, opt, budget);
    } else if (const int limit = model_context_limit(ref.dir); limit > 0 && ctx > limit) {
      const std::string say = "--context " + term::context(ctx) + " is more than " + serve_model +
                              " was trained for: it runs with " + term::context(limit) + ".";
      if (term::fancy()) ui::note(say);
      else fprintf(stderr, "kapitsa: %s\n", say.c_str());
      ctx = limit;
    }
    if (const std::string p = port_problem("127.0.0.1", port); !p.empty()) return fail(p);
    mkdir(hub::home_dir().c_str(), 0755);
    mkdir((hub::home_dir() + "/logs").c_str(), 0755);
    std::vector<std::string> sargv = {self_path(), "serve", "--model", serve_model, "--port", std::to_string(port)};
    if (switching && ctx_asked == kContextMax) sargv.insert(sargv.end(), {"--context", "max"});
    else if (ctx > 0 && !(switching && ctx_asked == 0)) sargv.insert(sargv.end(), {"--context", std::to_string(ctx)});
    if (switching) sargv.push_back("--allow-switch");
    if (!key.empty()) sargv.insert(sargv.end(), {"--api-key", key});
    if (loops > 0) sargv.insert(sargv.end(), {"--loops", std::to_string(loops)});
    std::vector<std::string> senv;
    for (char** e = environ; *e; ++e)
      if (strncmp(*e, "KAPITSA_PARENT_PID=", 19) != 0) senv.push_back(*e);
    senv.push_back("KAPITSA_PARENT_PID=" + std::to_string(getpid()));  // it exits with this process, however it ends
    auto sa = c_strings(sargv);
    auto se = c_strings(senv);
    const int lfd = open(log.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (lfd < 0) return fail("Can't write the server's log " + hub::tilde(log) + ": " + strerror(errno));
    server = fork();
    if (server < 0) return fail(std::string("Can't start the server: ") + strerror(errno));
    if (server == 0) {
      setsid();  // its own session: the terminal's Ctrl+C and Ctrl+Z go to the agent, not to it
      const int null = open("/dev/null", O_RDONLY);
      dup2(null, 0);
      dup2(lfd, 1);
      dup2(lfd, 2);
      execve(sa[0], sa.data(), se.data());
      _exit(127);
    }
    close(lfd);
    // wait for /health, showing what the server is doing
    struct sigaction act {};
    act.sa_handler = note_signal;
    sigemptyset(&act.sa_mask);
    struct sigaction old_int, old_term, old_hup;
    sigaction(SIGINT, &act, &old_int);
    sigaction(SIGTERM, &act, &old_term);
    sigaction(SIGHUP, &act, &old_hup);
    const bool tty = isatty(2);
    const std::string what = (ref.model ? ref.model->name : ref.name) +
                             (elsewhere ? ", on another Mac" : ", " + std::to_string(ctx) + "-token context");
    const auto t0 = std::chrono::steady_clock::now();
    int shown = -1;
    bool ready = false;
    // in a terminal: the logo as a loader while the server starts (a spinner where it can't play)
    const bool tui = term::fancy();
    const std::string label = term::bold(ref.model ? ref.model->name : ref.name) + term::dim("  " + std::string(term::kDot) + "  ") +
                              (elsewhere ? "on another Mac" : term::context(ctx) + " context");
    auto secs_since = [t0] { return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count(); };
    std::unique_ptr<ui::Loader> wobble;
    std::unique_ptr<term::Spinner> spinner;
    if (tui && ui::can_animate()) {
      term::line("");
      wobble = std::make_unique<ui::Loader>(
          [&] {
            return std::vector<std::string>{"Starting " + label + "  " + term::dim(term::duration(secs_since())),
                                            term::dim(term::clip(last_log_line(log), std::max(20, term::columns() - ui::kLogoCols - 8)))};
          },
          2);
    } else if (tui) {
      spinner = std::make_unique<term::Spinner>("Starting " + label);
    }
    while (!g_signal) {
      int st;
      if (waitpid(server, &st, WNOHANG) == server) {
        if (tui) {
          wobble.reset(), spinner.reset();
          term::status("");
          term::error("The server stopped while starting. The end of its log (" + hub::tilde(log) + "):");
          print_tail(log, 15);
          return 1;
        }
        if (tty) fprintf(stderr, "\r\033[K");
        fprintf(stderr, "kapitsa: the server stopped while starting. The end of its log (%s):\n", hub::tilde(log).c_str());
        print_tail(log, 15);
        return 1;
      }
      if (get(port, "/health", "", 1).status == 200) {
        ready = true;
        break;
      }
      const int secs = int(std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - t0).count());
      if (tui) {
        if (spinner) spinner->detail(term::clip(last_log_line(log), 60));
      } else if (tty) {
        std::string line = "Starting Kapitsa (" + what + ") " + std::to_string(secs) + "s  " + last_log_line(log);
        if (line.size() > 120) line.resize(120);
        fprintf(stderr, "\r\033[K%s", line.c_str());
      } else if (secs / 15 != shown) {
        shown = secs / 15;
        fprintf(stderr, "Starting Kapitsa (%s) %ds: %s\n", what.c_str(), secs, last_log_line(log).c_str());
      }
      std::this_thread::sleep_for(std::chrono::milliseconds(250));
    }
    if (tui) {
      const std::string done = term::accent(term::kOk) + " " + label + term::dim("  " + std::string(term::kDot) + "  ready in " +
                                                                              term::duration(secs_since()));
      if (wobble) wobble->done({done, ""});
      else if (spinner) spinner->done(ready ? "  " + done : "");
      wobble.reset(), spinner.reset();
    } else if (tty) {
      fprintf(stderr, "\r\033[K");
    }
    sigaction(SIGINT, &old_int, nullptr);
    sigaction(SIGTERM, &old_term, nullptr);
    sigaction(SIGHUP, &old_hup, nullptr);
    if (!ready) {
      kill(server, SIGTERM);
      waitpid(server, nullptr, 0);
      return 128 + int(g_signal);
    }
    if (probe(port, key, &run, &why) != 1) {
      kill(server, SIGTERM);
      waitpid(server, nullptr, 0);
      return fail("The server started but does not answer as Kapitsa: " + why);
    }
    // the models it switches to: the other downloaded ones it lists, each with the context it would load it with
    if (switching) {
      const Got g = get(port, "/v1/models", key, 5);
      const json j = json::parse(g.body, nullptr, false);
      if (g.status == 200 && j.is_object() && j.contains("data") && j["data"].is_array())
        for (const json& m : j["data"]) {
          if (!m.is_object() || m.value("active", true) || !m.value("downloaded", false)) continue;
          const std::string id = m.value("id", "");
          try {
            const hub::ModelRef r = hub::resolve(id);
            if (id.empty() || !unsupported_model(r.dir).empty()) continue;
            const int limit = model_context_limit(r.dir);
            int c = ctx_asked == 0 ? default_context(r.dir, opt, budget) : ctx_asked == kContextMax ? limit
                    : limit > 0 ? std::min(ctx_asked, limit) : ctx_asked;
            if (c <= 0) c = default_context(r.dir, opt, budget);
            switch_to.push_back({id, c});
          } catch (const std::exception&) {
          }
        }
    }
  }

  // the agent
  api::AgentServer s{"http://127.0.0.1:" + std::to_string(port), run.model, run.context, key, switch_to};
  std::map<std::string, std::string> env;
  for (char** e = environ; *e; ++e) {
    const char* eq = strchr(*e, '=');
    if (eq) env[std::string(*e, size_t(eq - *e))] = eq + 1;
  }
  api::AgentLaunch l;
  try {
    l = api::agent_launch(name, path, s, args, env, name == "opencode" ? major_version(path) : -1,
                          hub::home_dir() + "/agents");
  } catch (const std::exception& e) {
    if (server > 0) kill(server, SIGTERM), waitpid(server, nullptr, 0);
    return fail(e.what());
  }
  for (const auto& [file, content] : l.files)
    if (const std::string e = write_file(file, content); !e.empty()) {
      if (server > 0) kill(server, SIGTERM), waitpid(server, nullptr, 0);
      return fail("Can't write " + hub::tilde(file) + ": " + e);
    }
  for (const auto& u : l.unset) env.erase(u);
  for (const auto& [k, v] : l.set) env[k] = v;
  std::vector<std::string> cenv;
  for (const auto& [k, v] : env) cenv.push_back(k + "=" + v);
  auto ca = c_strings(l.argv);
  auto ce = c_strings(cenv);
  char ctxs[32];
  snprintf(ctxs, sizeof ctxs, "%d", run.context);
  const bool tui = term::fancy();
  const long log_from = server > 0 ? 0 : file_size_of(log);  // the requests of this session, for the line at its end
  const std::string service = server == 0 ? brew_service_stop(port) : "";  // the found server is the Homebrew service's
  const std::string service_note = "It is the Homebrew service, which starts it again at login and whenever it is killed: `" +
                                   service + "` stops it.";
  if (tui) {
    if (server == 0 && ask) {  // the question was skipped for it
      const std::string l = "Using the running server: " + term::bold(ui::model_label(run.model)),
                        why = service.empty() ? "stop it to pick another model"
                                              : "the Homebrew service: " + service + ", to pick another model";
      if (4 + term::width(l) + 3 + term::width(why) <= term::columns() - 1) ui::ok(l + term::dim(" (" + why + ")"));
      else ui::ok(l), ui::note(why);
    } else if (server == 0) {
      const std::string dot = term::dim("  " + std::string(term::kDot) + "  "),
                        rest = dot + run.model + dot + term::context(run.context) + " context";
      const std::string l = "Kapitsa on " + term::bold("http://127.0.0.1:" + std::to_string(port)) + rest + " " + term::dim("(already running)");
      // in a narrow terminal: shorter
      ui::ok(4 + term::width(l) <= term::columns() - 1 ? l : "Kapitsa already running on " + term::bold(":" + std::to_string(port)) + rest);
      if (!service.empty()) ui::note(service_note);
    } else
      ui::note("http://127.0.0.1:" + std::to_string(port) + "  " + term::kDot + "  log " + hub::tilde(log));
    for (const auto& n : l.notes) ui::note(n);
    term::line("", stderr);
  } else {
    fprintf(stderr, "Kapitsa: %s, %s-token context, http://127.0.0.1:%d (%s)\n", run.model.c_str(), ctxs, port,
            server > 0 ? ("started for this session; log " + hub::tilde(log)).c_str() : "already running");
    if (!service.empty()) fprintf(stderr, "%s\n", service_note.c_str());
    for (const auto& n : l.notes) fprintf(stderr, "%s\n", n.c_str());
  }

  // The agent gets the terminal as if started from the shell: in a process group of its own made the foreground one,
  // so Ctrl+C and Ctrl+Z reach it alone (the server is in its own session). Signals sent to this process go to it.
  const int tty = open("/dev/tty", O_RDWR | O_CLOEXEC);
  const bool fg = tty >= 0 && tcgetpgrp(tty) == getpgrp();
  sigset_t block, old;
  sigemptyset(&block);
  sigaddset(&block, SIGTTOU);
  sigaddset(&block, SIGTTIN);
  sigprocmask(SIG_BLOCK, &block, &old);
  const pid_t child = fork();
  if (child < 0) {
    if (server > 0) kill(server, SIGTERM), waitpid(server, nullptr, 0);
    return fail(std::string("Can't start ") + name + ": " + strerror(errno));
  }
  if (child == 0) {
    if (fg) {
      setpgid(0, 0);
      tcsetpgrp(tty, getpid());
    }
    sigprocmask(SIG_SETMASK, &old, nullptr);
    execve(ca[0], ca.data(), ce.data());
    fprintf(stderr, "kapitsa: can't run %s: %s\n", ca[0], strerror(errno));
    _exit(127);
  }
  // this process is now in the background: it hands the terminal back and forth without being stopped for it
  signal(SIGTTOU, SIG_IGN);
  signal(SIGTTIN, SIG_IGN);
  if (fg) {
    setpgid(child, child);
    tcsetpgrp(tty, child);
  }
  g_child_group = fg ? child : 0;
  struct sigaction fwd {};
  fwd.sa_handler = fg ? forward_signal : SIG_IGN;
  sigemptyset(&fwd.sa_mask);
  for (int sig : {SIGINT, SIGTERM, SIGHUP, SIGQUIT}) sigaction(sig, &fwd, nullptr);
  if (!fg) {
    // the agent shares this process group (no terminal of ours to hand over): the terminal's signals reach it
    // directly; SIGTERM and SIGHUP sent to this process only are passed on
    struct sigaction pass {};
    pass.sa_handler = [](int sig) {
      if (g_child_group < 0) kill(-g_child_group, sig);
    };
    sigemptyset(&pass.sa_mask);
    g_child_group = -child;
    sigaction(SIGTERM, &pass, nullptr);
    sigaction(SIGHUP, &pass, nullptr);
  }
  sigprocmask(SIG_SETMASK, &old, nullptr);
  int st = 0;
  for (;;) {
    const pid_t w = waitpid(child, &st, WUNTRACED);
    if (w < 0 && errno == EINTR) continue;
    if (w == child && WIFSTOPPED(st)) {
      // Ctrl+Z: take the terminal back and stop like a job; on `fg` hand it back and continue the agent
      if (fg) tcsetpgrp(tty, getpgrp());
      kill(getpid(), SIGSTOP);
      if (fg) tcsetpgrp(tty, child);
      kill(fg ? -child : child, SIGCONT);
      continue;
    }
    break;
  }
  if (fg) tcsetpgrp(tty, getpgrp());
  if (tty >= 0) close(tty);
  if (server > 0) {
    kill(server, SIGTERM);
    for (int i = 0; i < 100 && waitpid(server, nullptr, WNOHANG) == 0; ++i)
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
    if (waitpid(server, nullptr, WNOHANG) == 0) {
      kill(server, SIGKILL);
      waitpid(server, nullptr, 0);
    }
  }
  if (tui) {  // the session in one line: requests, tokens, cache reuse, speed; and the server's fate
    const Session ss = session_since(log, log_from);
    const std::string dot = term::dim("  " + std::string(term::kDot) + "  ");
    std::string l;
    if (ss.requests > 0) {
      char b[64];
      l = std::to_string(ss.requests) + (ss.requests == 1 ? " request" : " requests") + dot + term::count(double(ss.prompt)) +
          " prompt tokens";
      if (ss.prompt > 0) snprintf(b, sizeof b, " (%.0f%% cached)", 100.0 * double(ss.cached) / double(ss.prompt)), l += term::dim(b);
      l += dot + term::count(double(ss.out)) + " out";
      if (ss.decode_ms > 0 && ss.out > ss.requests)
        snprintf(b, sizeof b, " at %.0f tok/s", double(ss.out - ss.requests) / (ss.decode_ms / 1000)), l += b;
      l += dot;
    }
    l += server > 0 ? "the server stopped" : "Kapitsa keeps running on :" + std::to_string(port);
    if (!service.empty()) l += term::dim(" (the Homebrew service: " + service + " stops it)");
    term::line("", stderr);
    ui::ok(l);
  }
  if (WIFEXITED(st)) return WEXITSTATUS(st);
  if (WIFSIGNALED(st)) return 128 + WTERMSIG(st);
  return 1;
}

}  // namespace ni
