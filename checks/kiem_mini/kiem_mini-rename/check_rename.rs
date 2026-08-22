use notekeep::store;
use std::fs;

fn note(id: &str, title: &str) -> notekeep::Note {
    notekeep::Note {
        id: id.to_string(),
        title: title.to_string(),
        body: String::new(),
        tags: vec![],
        pinned: false,
    }
}

#[test]
fn rename_leaves_exactly_one_note_with_no_duplicate_file() {
    let dir = std::env::temp_dir().join(format!("kiem_rename_test_{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).unwrap();

    store::save(&dir, &note("old-id", "Old Title")).unwrap();
    store::rename(&dir, "old-id", "new-id", "New Title").unwrap();

    let notes = store::load_all(&dir).unwrap();
    assert_eq!(
        notes.len(),
        1,
        "expected exactly one note after rename, found {} — a rename that \
         writes a new file without deleting the old one leaves a stale \
         duplicate entry visible to load_all",
        notes.len()
    );
    assert_eq!(notes[0].id, "new-id");
    assert_eq!(notes[0].title, "New Title");

    assert!(
        !dir.join("old-id.note").exists(),
        "old-id.note should no longer exist on disk after rename"
    );
    assert!(
        dir.join("new-id.note").exists(),
        "new-id.note should exist on disk after rename"
    );

    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn rename_preserves_body_and_pinned_state() {
    let dir = std::env::temp_dir().join(format!("kiem_rename_test2_{}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).unwrap();

    let mut n = note("a", "Title A");
    n.body = "some #tagged body".to_string();
    n.pinned = true;
    store::save(&dir, &n).unwrap();

    store::rename(&dir, "a", "b", "Title B").unwrap();

    let notes = store::load_all(&dir).unwrap();
    assert_eq!(notes.len(), 1);
    assert_eq!(notes[0].body, "some #tagged body");
    assert!(notes[0].pinned, "pinned state should survive a rename");

    let _ = fs::remove_dir_all(&dir);
}
