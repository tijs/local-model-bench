use notekeep::{new_note, store};
use std::env;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

fn data_dir() -> PathBuf {
    PathBuf::from("data/notes")
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: notekeep <create|list|tags> [...]");
        std::process::exit(1);
    }
    match args[1].as_str() {
        "create" => {
            let body = args.get(2).cloned().unwrap_or_default();
            let id = format!(
                "{}",
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            );
            let title = body.lines().next().unwrap_or("").to_string();
            let note = new_note(&id, &title, &body);
            store::save(&data_dir(), &note).expect("save failed");
            println!("created {}", note.id);
        }
        "list" => {
            let notes = store::load_all(&data_dir()).expect("load failed");
            for n in notes {
                println!("{} {}", n.id, n.title);
            }
        }
        "tags" => {
            let notes = store::load_all(&data_dir()).expect("load failed");
            let mut all_tags: Vec<String> = notes.iter().flat_map(|n| n.tags.clone()).collect();
            all_tags.sort();
            all_tags.dedup();
            for t in all_tags {
                println!("{t}");
            }
        }
        other => {
            eprintln!("unknown command: {other}");
            std::process::exit(1);
        }
    }
}
