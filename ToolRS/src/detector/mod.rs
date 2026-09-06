pub mod template_matcher;
pub use template_matcher::{ArrowDetector, ArrowDirection};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_sample_boat() {
        let detector = ArrowDetector::new("assets/templates", 0.65);
        assert!(!detector.templates.is_empty(), "Templates must not be empty");

        let img = image::open("../assets/test_samples/sample_boat.png")
            .or_else(|_| image::open("assets/test_samples/sample_boat.png"))
            .expect("sample_boat.png should exist")
            .to_rgb8();

        let seq = detector.detect_sequence(&img);
        let seq_strs: Vec<&str> = seq.iter().map(|d| d.as_str()).collect();
        println!("Detected sequence in Rust: {:?}", seq_strs);

        assert_eq!(seq_strs, vec!["DOWN", "LEFT", "LEFT", "UP", "DOWN"]);
    }
}
