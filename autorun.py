import json
import subprocess
import sys
import os
import datetime

def main():
    """
    Reads configuration from config.json and runs the analysis command.
    The analysis date is dynamically set to the current date.
    """
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    cli_path = os.path.join(script_dir, "cli", "main.py")

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: {config_path} not found.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not decode {config_path}.", file=sys.stderr)
        sys.exit(1)

    # Dynamically set the analysis date to the current date
    analysis_date = datetime.datetime.now().strftime("%Y-%m-%d")

    command = [
        sys.executable,
        cli_path,
        "analyze",
        "--ticker", config["ticker"],
        "--analysis-date", analysis_date,
        "--research-depth", str(config["research_depth"]),
        "--llm-provider", config["llm_provider"],
        "--shallow-thinker", config["shallow_thinker"],
        "--deep-thinker", config["deep_thinker"],
    ]

    for analyst in config["analysts"]:
        command.extend(["--analysts", analyst])

    try:
        # Run the command from the script's directory
        subprocess.run(command, check=True, cwd=script_dir)
    except subprocess.CalledProcessError as e:
        print(f"Error running analysis: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: Python interpreter or script not found.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
