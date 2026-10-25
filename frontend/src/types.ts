export type Point = [number, number];
export type Settings = {
  engine: "trocr" | "crnn";
  detector: "kraken" | "projection";
  paragraph_mode: "lines" | "paragraphs";
  preprocessing: "natural" | "enhanced";
  deskew: boolean;
  rotation: 0 | 90 | 180 | 270;
  corners: Point[] | null;
  beam_width: number;
  max_new_tokens: number;
  line_padding: number;
  review_threshold: number;
};
export type Line = {
  id: string;
  polygon: Point[];
  raw_text: string;
  text: string;
  score: number | null;
  warnings: string[];
  reviewed: boolean;
  paragraph_start: boolean;
};
export type DocumentResult = {
  schema_version: number;
  width: number;
  height: number;
  original_width: number;
  original_height: number;
  transform: number[][];
  lines: Line[];
  raw_text: string;
  full_text: string;
  warnings: string[];
  model: Record<string, string>;
  settings: Settings;
  timings: Record<string, number>;
};
export type Job = {
  id: string;
  title: string;
  status: string;
  stage: string;
  completed: number;
  total: number;
  revision: number;
  document: DocumentResult | null;
  error: string | null;
  settings: Settings;
  created: number;
  metrics: { cer: number; wer: number } | null;
  reference?: string | null;
};
export type Capabilities = {
  device: string;
  engines: {
    id: string;
    name: string;
    architecture: string;
    version: string;
    ready: boolean;
    beam_search: boolean;
  }[];
  detectors: { id: string; name: string; ready: boolean }[];
};
export const defaults: Settings = {
  engine: "trocr",
  detector: "kraken",
  paragraph_mode: "paragraphs",
  preprocessing: "natural",
  deskew: true,
  rotation: 0,
  corners: null,
  beam_width: 3,
  max_new_tokens: 128,
  line_padding: 8,
  review_threshold: 0.65,
};
