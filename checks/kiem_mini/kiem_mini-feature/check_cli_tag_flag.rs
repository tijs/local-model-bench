// The task prompt requires wiring `--tag <TAG>` into the `list` CLI
// command, not just implementing filter_by_tag in the library — but
// check_tag_filter.rs only ever exercised the library function directly.
// A logged PASS from before this file existed had its own compiler
// warning ("`tag` is never read") proving the CLI half was never actually
// wired up, and nothing caught it. This drives the real built binary
// end-to-end instead of calling the library function directly.
use std::env;
use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn bin() -> PathBuf {
    PathBuf::from(env!("CARGO_BIN_EXE_notekeep"))
}

fn fresh_workdir(label: &str) -> PathBuf {
    let dir = env::temp_dir().join(format!(
        "notekeep_cli_check_{label}_{}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("create temp workdir");
    dir
}

fn run(dir: &PathBuf, args: &[&str]) -> String {
    let out = Command::new(bin())
        .args(args)
        .current_dir(dir)
        .output()
        .expect("run notekeep binary");
    assert!(
        out.status.success(),
        "`notekeep {}` exited non-zero.\nstdout: {}\nstderr: {}",
        args.join(" "),
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr),
    );
    String::from_utf8_lossy(&out.stdout).to_string()
}

#[test]
fn list_tag_flag_filters_cli_output_by_exact_tag() {
    let dir = fresh_workdir("filter");
    run(&dir, &["create", "Work item\n#work urgent stuff"]);
    run(&dir, &["create", "Homework item\n#homework not urgent"]);
    run(&dir, &["create", "Personal item\n#personal chill"]);

    let unfiltered = run(&dir, &["list"]);
    assert!(
        unfiltered.contains("Work item")
            && unfiltered.contains("Homework item")
            && unfiltered.contains("Personal item"),
        "`list` with no --tag must show every note:\n{unfiltered}"
    );

    let filtered = run(&dir, &["list", "--tag", "work"]);
    assert!(
        filtered.contains("Work item"),
        "`list --tag work` must include the note tagged #work:\n{filtered}"
    );
    assert!(
        !filtered.contains("Homework item"),
        "`list --tag work` must NOT include a note tagged #homework (exact match, not substring):\n{filtered}"
    );
    assert!(
        !filtered.contains("Personal item"),
        "`list --tag work` must NOT include an unrelated note:\n{filtered}"
    );
}

#[test]
fn list_tag_flag_with_no_matches_prints_nothing_and_exits_cleanly() {
    let dir = fresh_workdir("empty");
    run(&dir, &["create", "Personal item\n#personal chill"]);
    let filtered = run(&dir, &["list", "--tag", "nonexistent"]);
    assert!(
        !filtered.contains("Personal item"),
        "`list --tag nonexistent` must filter out every note:\n{filtered}"
    );
}
