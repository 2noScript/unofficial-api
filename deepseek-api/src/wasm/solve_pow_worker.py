import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wasmsolver import solve_wasm

if __name__ == "__main__":
    args = json.load(sys.stdin)
    try:
        answer, result = solve_wasm(
            algorithm=args["algorithm"],
            challenge=args["challenge"],
            salt=args["salt"],
            expire_at=args["expire_at"],
            difficulty=args["difficulty"],
            signature=args["signature"],
            target_path=args.get("target_path", ""),
        )
        print(json.dumps({"ok": True, "answer": answer, "result": result}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
