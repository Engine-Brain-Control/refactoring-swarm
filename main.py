import argparse
import sys
import os
from dotenv import load_dotenv
from src.utils.logger import log_experiment, ActionType
from src.graph import create_graph
from src.tools import SwarmTools

load_dotenv()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target_dir", type=str, required=True)
    parser.add_argument("--cooldown", type=int, default=0)
    parser.add_argument("--disable_llm", action="store_true")
    parser.add_argument("--output_mode", type=str, choices=["overwrite", "copy"], default="overwrite")
    parser.add_argument("--output_dir", type=str, default="refactored")
    parser.add_argument("--model", type=str, default="llama-3.1-8b-instant")
    parser.add_argument("--max_files", type=int, default=0)
    args = parser.parse_args()

    target_dir = args.target_dir
    cooldown = args.cooldown
    disable_llm = args.disable_llm
    output_mode = args.output_mode
    output_dir = args.output_dir
    model_name = args.model
    max_files = args.max_files
    if output_mode == "copy":
        out_root = os.path.join(target_dir, output_dir)
        os.makedirs(out_root, exist_ok=True)
    
    if not os.path.exists(target_dir):
        print(f"❌ Dossier {target_dir} introuvable.")
        sys.exit(1)

    print(f"🚀 DEMARRAGE SUR : {target_dir}")
    # Using DEBUG for system startup log to satisfy validator
    log_experiment(
        agent_name="System",
        model_used="System",
        action=ActionType.DEBUG,
        details={
            "input_prompt": "STARTUP",
            "output_response": f"Target: {target_dir}"
        },
        status="INFO"
    )

    # Initialize Tools to list files
    tools = SwarmTools(target_dir)
    files = tools.list_files()
    if max_files and max_files > 0:
        files = files[:max_files]
    
    if not files:
        print("⚠️ Aucun fichier Python trouvé dans le dossier cible.")
        sys.exit(0)

    print(f"📄 Fichiers détectés : {files}")

    # Initial State
    initial_state = {
        "target_dir": target_dir,
        "files": files,
        "current_file_index": 0,
        "current_file_path": files[0],
        "current_file_content": "", # Will be read by Auditor
        "pylint_report": "",
        "refactoring_plan": "",
        "test_results": {},
        "iteration_count": 0,
        "max_iterations": 10,
        "status": "STARTING",
        "messages": [],
        "cooldown_seconds": cooldown,
        "disable_llm": disable_llm,
        "output_mode": output_mode,
        "output_dir": output_dir,
        "results": []
    }

    # Create and Run Graph
    app = create_graph(target_dir, model_name)
    
    # We use stream or invoke. Invoke returns the final state.
    # We might want to see progress, so maybe stream?
    # For now invoke is simpler.
    print("🔄 Exécution du Swarm...")
    final_state = app.invoke(initial_state, config={"recursion_limit": 200})
    
    print("✅ MISSION_COMPLETE")
    print("Final State Test Results:", final_state.get("test_results", {}).get("success"))
    res = final_state.get("results", [])
    if res:
        print("📊 Résumé des corrections:")
        for r in res:
            print(f"- File: {r.get('original_path')} -> {r.get('dest_path')} | Mode: {r.get('mode')} | Before: {r.get('before_score')} | After: {r.get('after_score')} | Status: {r.get('status')}")

if __name__ == "__main__":
    main()
