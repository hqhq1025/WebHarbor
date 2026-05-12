import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI
import simpleArgParser as sap


@dataclass
class JudgeArgs:
    run_dir: str = ""
    out: str = ""
    last_k_screenshots: int = 4
    model: str = "gpt-5.1"
    api_key: str = ""
    base_url: str = ""


JUDGE_SYSTEM = """You are a strict grader of web-agent task completion.

You receive:
  - the original natural-language TASK,
  - the agent's trajectory (per step: thought + action + URL + (optional) extracted_content),
  - the agent's final self-reported answer (if any),
  - the LAST K screenshots of the browser, in order. The last image is the
    final state the user would see.

Your job is to decide whether the task was actually completed. Be skeptical.
Common failure modes you must catch:
  - The agent claimed success but the final page does not show the right content.
  - The agent answered with plausible-sounding but wrong information.
  - The agent stopped early (max_steps) without finishing.
  - The agent navigated somewhere unrelated.

Tie-break rules:
  - If the task asks for a fact and the agent's done.text contains a value,
    cross-check that the value is visible in the final screenshot or in
    extracted_content recorded in the trajectory.
  - If the task is a navigational task ("find the page that ..."), the final
    screenshot must show that page.
  - If the agent performed irreversible actions (purchase, post comment, etc.)
    that the task did not ask for, mark success=false and explain.

Respond with ONLY this JSON object:

  {
    "success": <true|false>,
    "confidence": <0.0-1.0>,
    "rationale": "<one paragraph, ≤150 words, citing specific steps/screenshots>",
    "evidence": ["<quote or short paraphrase of supporting signal 1>", "..."],
    "answer_extracted": "<the answer the agent ended up giving, or empty>"
  }
"""


def img_payload(path):
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}}


def trajectory_text(traj, max_step_chars=400):
    lines = []
    lines.append(f"TASK: {traj.get('task', '')}")
    lines.append(f"START URL: {traj.get('start_url', '')}")
    lines.append(f"TERMINATED: {traj.get('terminated')} ({traj.get('termination_reason')})")
    lines.append(f"AGENT'S FINAL ANSWER (self-report): {traj.get('final_answer', '<none>')!r}")
    lines.append(f"AGENT'S SELF-REPORTED SUCCESS: {traj.get('success_self_report', '<none>')}")
    lines.append("")
    lines.append("STEPS:")
    for s in traj.get("steps", []):
        ar = s.get("action_result") or {}
        ec = ar.get("extracted_content") or ""
        line = (
            f"  [{s['step']}] {s['action']} {s.get('params', {})} "
            f"@ {s['url']}\n"
            f"        thought: {s.get('thought', '')[:max_step_chars]}"
        )
        if ec:
            line += f"\n        extracted: {ec[:max_step_chars]}"
        if ar.get("error"):
            line += f"\n        error: {ar['error']}"
        lines.append(line)
    return "\n".join(lines)


def build_messages(traj, screenshot_paths):
    text = trajectory_text(traj)
    user_content = [{"type": "text", "text": text + "\n\nLAST SCREENSHOTS (oldest → newest):"}]
    for p in screenshot_paths:
        user_content.append({"type": "text", "text": f"({p.name})"})
        user_content.append(img_payload(p))
    user_content.append({"type": "text", "text": "Now grade. Respond with the JSON only."})
    return [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": user_content},
    ]


def parse_judge_json(raw):
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
        s = s.strip()
    start = s.find("{")
    if start < 0:
        raise ValueError(f"no JSON in judge reply: {raw[:200]!r}")
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(s[start : i + 1])
    raise ValueError(f"unterminated JSON in judge reply: {raw[:200]!r}")


def main():
    args = sap.parse_args(JudgeArgs)
    if not args.run_dir:
        raise SystemExit("--run_dir is required")

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    base_url = args.base_url or os.environ.get("OPENAI_BASE_URL", "")
    if not api_key:
        raise SystemExit("API key missing: set --api_key or OPENAI_API_KEY")
    if not base_url:
        raise SystemExit("Base URL missing: set --base_url or OPENAI_BASE_URL")

    run_dir = Path(args.run_dir)
    traj = json.loads((run_dir / "trajectory.json").read_text())

    shots_dir = run_dir / "screenshots"
    all_shots = sorted(shots_dir.glob("step_*.png"))
    if not all_shots:
        raise SystemExit(f"no screenshots in {shots_dir}")
    last_k = all_shots[-args.last_k_screenshots :]
    print(f"judging {len(traj.get('steps', []))} steps with last {len(last_k)} screenshots: "
          f"{[p.name for p in last_k]}")

    client = OpenAI(base_url=base_url, api_key=api_key)
    messages = build_messages(traj, last_k)

    resp = client.chat.completions.create(model=args.model, messages=messages)
    raw = resp.choices[0].message.content or ""
    try:
        verdict = parse_judge_json(raw)
    except Exception as e:
        verdict = {
            "success": False,
            "confidence": 0.0,
            "rationale": f"judge parse error: {e}",
            "evidence": [],
            "answer_extracted": "",
            "raw_reply": raw,
        }

    verdict["meta"] = {
        "run_dir": str(run_dir),
        "task": traj.get("task", ""),
        "model": args.model,
        "screenshots_used": [p.name for p in last_k],
        "trajectory_steps": len(traj.get("steps", [])),
    }

    out_path = Path(args.out) if args.out else run_dir / "eval.json"
    out_path.write_text(json.dumps(verdict, indent=2))
    print(f"wrote {out_path}")
    print(f"  success: {verdict.get('success')}  confidence: {verdict.get('confidence')}")
    print(f"  rationale: {verdict.get('rationale', '')[:300]}")


if __name__ == "__main__":
    main()
