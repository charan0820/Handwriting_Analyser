import * as Collapsible from "@radix-ui/react-collapsible";
import * as Slider from "@radix-ui/react-slider";
import {
  CaretDown,
  SlidersHorizontal,
  WarningCircle,
} from "@phosphor-icons/react";
import type { Settings, Capabilities } from "./types";
export default function SettingsPanel({
  value,
  onChange,
  capabilities,
  disabled,
}: {
  value: Settings;
  onChange: (v: Settings) => void;
  capabilities: Capabilities | null;
  disabled: boolean;
}) {
  const set = <K extends keyof Settings>(key: K, next: Settings[K]) =>
    onChange({ ...value, [key]: next });
  const engine = capabilities?.engines.find((e) => e.id === value.engine);
  const detector = capabilities?.detectors.find((e) => e.id === value.detector);
  return (
    <fieldset className="settings" disabled={disabled}>
      <legend>
        <SlidersHorizontal /> Transcription settings
      </legend>
      <div className="settings-grid">
        <label>
          Recognition model
          <select
            value={value.engine}
            onChange={(e) =>
              set("engine", e.target.value as Settings["engine"])
            }
          >
            {(
              capabilities?.engines ?? [
                { id: "trocr", name: "TrOCR Handwritten", ready: false },
                { id: "crnn", name: "Project CRNN", ready: false },
              ]
            ).map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
                {e.ready ? "" : " · setup needed"}
              </option>
            ))}
          </select>
        </label>
        <label>
          Line detection
          <select
            value={value.detector}
            onChange={(e) =>
              set("detector", e.target.value as Settings["detector"])
            }
          >
            {(
              capabilities?.detectors ?? [
                { id: "kraken", name: "Kraken learned lines", ready: false },
                {
                  id: "projection",
                  name: "Simple straight lines",
                  ready: true,
                },
              ]
            ).map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
                {e.ready ? "" : " · setup needed"}
              </option>
            ))}
          </select>
        </label>
        <label>
          Image preparation
          <select
            value={value.preprocessing}
            onChange={(e) =>
              set("preprocessing", e.target.value as Settings["preprocessing"])
            }
          >
            <option value="natural">Natural grayscale / color</option>
            <option value="enhanced">Enhanced contrast</option>
          </select>
        </label>
        <label>
          Document layout
          <select
            value={value.paragraph_mode}
            onChange={(e) =>
              set(
                "paragraph_mode",
                e.target.value as Settings["paragraph_mode"],
              )
            }
          >
            <option value="paragraphs">Reflow paragraphs</option>
            <option value="lines">Preserve line breaks</option>
          </select>
        </label>
      </div>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={value.deskew}
          onChange={(e) => set("deskew", e.target.checked)}
        />{" "}
        Automatically straighten the page
      </label>
      {((engine && !engine.ready) || (detector && !detector.ready)) && (
        <p className="setup-note">
          <WarningCircle /> Setup needed for the selected engine or detector.
          Run the documented model / WSL setup, or select the available CRNN and
          simple baseline explicitly.
        </p>
      )}
      <Collapsible.Root>
        <Collapsible.Trigger className="advanced-trigger">
          Advanced model parameters <CaretDown />
        </Collapsible.Trigger>
        <Collapsible.Content className="advanced-content">
          <div className="settings-grid">
            <label>
              Decoder
              <select
                disabled={value.engine === "crnn"}
                value={
                  value.engine === "crnn"
                    ? "greedy"
                    : value.beam_width === 1
                      ? "greedy"
                      : "beam"
                }
                onChange={(e) =>
                  set("beam_width", e.target.value === "greedy" ? 1 : 3)
                }
              >
                <option value="greedy">Greedy</option>
                <option value="beam">Beam search</option>
              </select>
            </label>
            <label>
              Beam width
              <input
                type="number"
                min="1"
                max="5"
                disabled={value.engine === "crnn"}
                value={value.beam_width}
                onChange={(e) =>
                  set(
                    "beam_width",
                    Math.max(1, Math.min(5, Number(e.target.value))),
                  )
                }
              />
            </label>
            <label>
              Output token limit
              <input
                type="number"
                min="16"
                max="256"
                disabled={value.engine === "crnn"}
                value={value.max_new_tokens}
                onChange={(e) =>
                  set(
                    "max_new_tokens",
                    Math.max(16, Math.min(256, Number(e.target.value))),
                  )
                }
              />
            </label>
            <label>
              Line padding (pixels)
              <input
                type="number"
                min="0"
                max="40"
                value={value.line_padding}
                onChange={(e) =>
                  set(
                    "line_padding",
                    Math.max(0, Math.min(40, Number(e.target.value))),
                  )
                }
              />
            </label>
          </div>
          <label className="slider-label">
            Review sensitivity{" "}
            <span>{value.review_threshold.toFixed(2)} model score</span>
            <Slider.Root
              className="slider"
              value={[value.review_threshold]}
              onValueChange={(v) => set("review_threshold", v[0])}
              min={0}
              max={1}
              step={0.05}
              aria-label="Review score threshold"
            >
              <Slider.Track className="slider-track">
                <Slider.Range className="slider-range" />
              </Slider.Track>
              <Slider.Thumb className="slider-thumb" />
            </Slider.Root>
          </label>
          <p className="hint">
            Scores help prioritize review. They are not calibrated accuracy
            estimates.
          </p>
          <dl className="model-info">
            <dt>Architecture</dt>
            <dd>{engine?.architecture ?? "Loading…"}</dd>
            <dt>Model</dt>
            <dd>{engine?.version ?? "—"}</dd>
            <dt>Available device</dt>
            <dd>{capabilities?.device ?? "Connecting…"}</dd>
          </dl>
        </Collapsible.Content>
      </Collapsible.Root>
    </fieldset>
  );
}
