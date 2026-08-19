use crate::Note;
use std::fs;
use std::path::Path;

const SEP: &str = "\n---\n";

pub fn save(dir: &Path, note: &Note) -> std::io::Result<()> {
    fs::create_dir_all(dir)?;
    let pinned_flag = if note.pinned { "1" } else { "0" };
    let content = format!(
        "{}{}{}{}{}{}{}",
        note.id, SEP, note.title, SEP, pinned_flag, SEP, note.body
    );
    fs::write(dir.join(format!("{}.note", note.id)), content)
}

pub fn load_all(dir: &Path) -> std::io::Result<Vec<Note>> {
    let mut notes = Vec::new();
    if !dir.exists() {
        return Ok(notes);
    }
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let content = fs::read_to_string(entry.path())?;
        let parts: Vec<&str> = content.splitn(4, SEP).collect();
        if parts.len() == 4 {
            let tags = crate::extract_tags(parts[3]);
            notes.push(Note {
                id: parts[0].to_string(),
                title: parts[1].to_string(),
                pinned: parts[2] == "1",
                body: parts[3].to_string(),
                tags,
            });
        }
    }
    Ok(notes)
}
