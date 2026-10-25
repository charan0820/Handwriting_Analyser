import { useState, useEffect } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  FileText,
  LockSimple,
  Scan,
  TextAlignLeft,
  UploadSimple,
} from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";

export default function Landing({
  open,
  sample,
}: {
  open: () => void;
  sample: () => void;
}) {
  const [original, setOriginal] = useState(true);
  const reduced = useReducedMotion();
  return (
    <>
      <header className="site-header wrap">
        <a className="brand" href="#">
          <span className="brand-icon">
            <TextAlignLeft weight="bold" />
          </span>
          Handwriting<span className="brand-light">Analyser</span>
        </a>
        <nav aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#your-pages">Your pages, digitized</a>
        </nav>
        <button className="button small secondary" onClick={open}>
          Open workspace <ArrowUpRight />
        </button>
      </header>
      <main>
        <section className="hero wrap">
          <div className="hero-copy">
            <h1>
              Turn handwritten
              <br />
              pages into <span>editable documents.</span>
            </h1>
            <p>
              Your ideas deserve more than a page.
              <br />
              Bring handwritten notes into a searchable, editable world.
            </p>
            <div className="hero-actions">
              <button className="button" onClick={open}>
                Transcribe a page <ArrowRight />
              </button>
              <button className="text-button" onClick={sample}>
                Try a sample <ArrowUpRight />
              </button>
            </div>
            <div className="privacy-note">
              <LockSimple /> Entirely local. Your words stay yours.
            </div>
          </div>
          <div
            className="hero-art"
            aria-label="Illustration of a handwritten page becoming editable text"
          >
            <div className="paper-sheet">
              <div className="paper-heading">A thought worth keeping.</div>
              <img
                src="/sample.png"
                alt="English handwritten lines from the IAM dataset, assembled into a demonstration page"
              />
              <div className="line-detections" aria-hidden="true">
                {[0, 1, 2, 3, 4].map((n) => (
                  <motion.div
                    key={n}
                    initial={false}
                    animate={
                      reduced ? {} : { opacity: [0.12, 0.85, 0.85, 0.12] }
                    }
                    transition={{
                      duration: 7,
                      repeat: Infinity,
                      delay: n * 0.3,
                    }}
                  />
                ))}
              </div>
              <span className="paper-foot">HANDWRITTEN ORIGINAL</span>
            </div>
            <motion.div
              className="transcript-sheet"
              initial={false}
              animate={reduced ? {} : { y: [0, -5, 0] }}
              transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
            >
              <div className="transcript-top">
                <span className="file-mark">
                  <FileText weight="duotone" />
                </span>
                <span>
                  Untitled thoughts.txt
                  <small>Ready for your next chapter</small>
                </span>
                <span className="saved-dot" aria-hidden="true" />
              </div>
              <div className="demo-text">
                <p>Every page holds a possibility.</p>
                <p>
                  A passing thought.
                  <br />
                  An idea in the margins.
                  <br />
                  Something worth coming back to.
                </p>
                <p>
                  Make room for what comes next.
                  <span className="typing-caret" />
                </p>
              </div>
              <div className="transcript-bottom">
                <Check /> Editable text <span>TXT · DOCX</span>
              </div>
            </motion.div>
            <span className="demo-caption">
              Illustrative transformation · sample handwriting shown
            </span>
          </div>
        </section>
        <div className="format-strip wrap">
          <span>FROM THE PAGE. INTO YOUR FLOW.</span>
          <div>
            English handwriting <span> / </span> PNG & JPEG <span> / </span> TXT
            & DOCX <span> / </span> Works offline after setup
          </div>
        </div>
        <section className="workflow wrap" id="how-it-works">
          <div className="section-intro">
            <h2>
              A little less typing.
              <br />A lot more possibility.
            </h2>
            <p>
              From a photograph to a document you can make your own. You stay in
              control of every word.
            </p>
          </div>
          <div className="steps">
            {[
              {
                icon: UploadSimple,
                title: "Bring your page.",
                text: "Drop in a scan or photograph. Rotate, crop, and adjust before you begin.",
              },
              {
                icon: Scan,
                title: "Let the lines unfold.",
                text: "Local models find each line and turn your handwriting into digital text.",
              },
              {
                icon: FileText,
                title: "Make it yours.",
                text: "Review alongside the original, edit any word, and download your document.",
              },
            ].map(({ icon: Icon, title, text }, i) => (
              <div className="step" key={title}>
                <div className="step-top">
                  <Icon />
                  <span>0{i + 1}</span>
                </div>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="comparison-section" id="your-pages">
          <div className="wrap comparison">
            <div className="comparison-copy">
              <h2>
                The same words.
                <br />A new beginning.
              </h2>
              <p>
                Keep the original close. Every recognized line stays connected
                to the page, so checking and correcting feels natural.
              </p>
              <div className="segmented" aria-label="Compare example views">
                <button
                  aria-pressed={original}
                  className={original ? "active" : ""}
                  onClick={() => setOriginal(true)}
                >
                  Original page
                </button>
                <button
                  aria-pressed={!original}
                  className={!original ? "active" : ""}
                  onClick={() => setOriginal(false)}
                >
                  Verified transcript
                </button>
              </div>
              <button className="text-button" onClick={sample}>
                Explore the sample <ArrowRight />
              </button>
            </div>
            <div className="comparison-preview">
              {original ? (
                <img src="/sample.png" alt="Bundled handwriting example" />
              ) : (
                <SampleText />
              )}
              <small>
                Assembled IAM line sample · reference transcription, not a model
                prediction
              </small>
            </div>
          </div>
        </section>
        <section className="closing wrap">
          <LockSimple />
          <h2>
            Good ideas start on paper.
            <br />
            They don’t have to stay there.
          </h2>
          <button className="button" onClick={open}>
            Transcribe a page <ArrowRight />
          </button>
          <p>No account. No upload to the cloud. Just your words.</p>
        </section>
      </main>
      <footer className="wrap site-footer">
        <a href="#" className="brand">
          <TextAlignLeft /> Handwriting Analyser
        </a>
        <span>Made for the words worth keeping.</span>
        <button className="text-button" onClick={open}>
          Open workspace <ArrowUpRight />
        </button>
      </footer>
    </>
  );
}
function SampleText() {
  const [text, setText] = useState("Loading reference…");
  useEffect(() => {
    fetch("/sample.json")
      .then((r) => r.json())
      .then((data) => setText(data.text))
      .catch(() =>
        setText("Sample unavailable. Upload your own page in the workspace."),
      );
  }, []);
  return <div className="reference-text">{text}</div>;
}
