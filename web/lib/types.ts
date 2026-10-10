/** Fields match models/tool_info.py ToolInfo. This file is a sample shape, not a live digest. */
export type ToolInfo = {
  title: string;
  website: string;
  summary: string | null;
  features: string[];
  pricing: string | null;
  source: string;
  target_audience: string | null;
  main_text: string;
  ai_tool_annotation: string | null;
  tags: string[];
  publish_date: string | null;
};

export type DigestFile = {
  label: string;
  tools: ToolInfo[];
};

export type ProofResult = {
  title: string;
  link: string;
  snippet: string;
  source: string;
};

export type ProofResponse = {
  source: "sample" | "live";
  query: string;
  tbs: string;
  results: ProofResult[];
  reason?: string;
};
