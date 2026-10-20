use notekeep::{extract_tags, filter_by_tag, new_note, store};
use std::fs;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[test]
fn extracts_simple_tags() {
    assert_eq!(extract_tags("hello #world #rust"), vec!["world", "rust"]);
}

#[test]
fn no_tags_when_none_present() {
    assert_eq!(extract_tags("just plain text"), Vec::<String>::new());
}

#[test]
fn filters_exact_tags_in_original_order() {
    let notes = vec![
        new_note("first", "First", "#rust"),
        new_note("other", "Other", "#rusty"),
        new_note("last", "Last", "#rust #cli"),
    ];
    let ids: Vec<&str> = filter_by_tag(&notes, "rust")
        .iter()
        .map(|note| note.id.as_str())
        .collect();
    assert_eq!(ids, vec!["first", "last"]);
    assert!(filter_by_tag(&notes, "missing").is_empty());
}

#[test]
fn list_tag_uses_value_after_flag() {
    let dir = std::env::temp_dir().join(format!(
        "notekeep-list-tag-{}-{}",
        std::process::id(),
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    fs::create_dir(&dir).unwrap();
    let notes_dir = dir.join("data/notes");
    for note in [
        new_note("wanted", "Rust note", "#rust"),
        new_note("substring", "Rusty note", "#rusty"),
        new_note("other", "Other note", "#other"),
    ] {
        store::save(&notes_dir, &note).unwrap();
    }
    let output = Command::new(env!("CARGO_BIN_EXE_notekeep"))
        .current_dir(&dir)
        .args(["list", "--tag", "rust"])
        .output()
        .unwrap();
    fs::remove_dir_all(&dir).unwrap();
    assert!(output.status.success(), "{:?}", output);
    assert_eq!(
        String::from_utf8(output.stdout).unwrap(),
        "wanted Rust note\n"
    );
}
