import argparse
import configparser
import json
import os
import subprocess
import sys
from datetime import datetime

config = configparser.ConfigParser()
config_file_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config.ini"
)

if not os.path.exists(config_file_path):
    print(f"[✗] ERROR: config.ini not found at {config_file_path}")
    sys.exit(1)
config.read(config_file_path)

try:
    PATHS = config["Paths"]
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = os.path.join(BASE_DIR, PATHS.get("output_dir", "output"))
    JOB_DIR_BASE = os.path.join(BASE_DIR, PATHS.get("job_dir", "jobs"))
    LANGUAGE_FILE = os.path.join(BASE_DIR, PATHS.get("language_file", "languages.json"))
    SITE_CONFIG_FILE_TPL = os.path.join(
        BASE_DIR, PATHS.get("site_config_file", "site_configs.json")
    )
    MODEL_CACHE_DIR = os.path.join(
        BASE_DIR, PATHS.get("model_cache_dir", "language_models")
    )
except KeyError:
    print(f"[✗] ERROR: config.ini is missing the [Paths] section.")
    sys.exit(1)


def run_command(command, error_message):
    """Helper function to run a shell command and check for errors."""
    print(f"\n[+] STAGE: {error_message}")
    print(f"    Running: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, text=True)
        print(f"[✓] SUCCESS: {error_message} completed.")
    except subprocess.CalledProcessError as e:
        print(
            f"\n[✗] ERROR: {error_message} failed! To resume, see the --job-id command."
        )
        print(f"    Error details: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n[✗] ERROR: Command not found. Is Scrapy installed and venv active?")
        print(f"    Error details: {e}")
        sys.exit(1)


def get_seed_urls_from_file(filepath):
    """Reads a .jsonl file from 'discover' and returns a .txt file path."""
    urls = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                urls.append(json.loads(line)["url"])
    except Exception as e:
        print(f"[✗] ERROR: Could not read seed file {filepath}: {e}")
        sys.exit(1)

    if not urls:
        print(f"[i] No URLs found in {filepath}. Nothing to do.")
        return None

    txt_filepath = filepath.replace(".jsonl", ".txt")
    with open(txt_filepath, "w") as f:
        for url in urls:
            f.write(url + "\n")
    return txt_filepath


def main():
    parser = argparse.ArgumentParser(
        description="Targeted Language Scraping Framework Orchestrator"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    web_parser = subparsers.add_parser(
        "web", help="Run the full WEB scraping pipeline (Discover > Configure > Scrape)"
    )
    web_parser.add_argument(
        "-l",
        "--lang",
        type=str,
        required=True,
        help='Target language key from languages.json (e.g., "filipino")',
    )
    web_parser.add_argument(
        "-t",
        "--terms",
        type=str,
        required=True,
        help='Seed search terms, e.g., "Filipino news,Tagalog articles"',
    )
    web_parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=10,
        help="Number of URLs to discover (default: 10)",
    )

    web_parser.add_argument(
        "--job-id",
        type=str,
        default=None,
        help="Job ID (timestamp) to resume a previous run.",
    )

    pdf_parser = subparsers.add_parser(
        "pdf", help="Run the full PDF scraping pipeline (Discover > Scrape)"
    )
    pdf_parser.add_argument(
        "-l",
        "--lang",
        type=str,
        required=True,
        help='Target language key from languages.json (e.g., "filipino")',
    )
    pdf_parser.add_argument(
        "-t",
        "--terms",
        type=str,
        required=True,
        help='Seed search terms, e.g., "Filipino government forms pdf"',
    )
    pdf_parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=10,
        help="Number of URLs to discover (default: 10)",
    )

    pdf_parser.add_argument(
        "--job-id",
        type=str,
        default=None,
        help="Job ID (timestamp) to resume a previous run.",
    )

    args = parser.parse_args()

    if args.job_id:
        print(f"[i] Resuming job: {args.job_id}")
        JOB_ID = args.job_id
    else:
        JOB_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"[i] Starting new job. To resume this run, use: --job-id {JOB_ID}")

    JOB_DIR = os.path.join(JOB_DIR_BASE, f"{args.command}_{args.lang}_{JOB_ID}")
    SEED_FILE_WEB = os.path.join(OUTPUT_DIR, f"seed_urls_web_{JOB_ID}.jsonl")
    SEED_FILE_PDF = os.path.join(OUTPUT_DIR, f"seed_urls_pdf_{JOB_ID}.jsonl")
    SITE_CONFIG_FILE = SITE_CONFIG_FILE_TPL.replace(".json", f"_{JOB_ID}.json")

    os.makedirs(JOB_DIR_BASE, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"[i] Using job directory for persistence: {JOB_DIR}")

    spider_args = [
        "-a",
        f"language_file={LANGUAGE_FILE}",
        "-a",
        f"model_cache_dir={MODEL_CACHE_DIR}",
    ]

    if args.command == "web":
        print(f"--- Starting WEB Scraping Pipeline for '{args.lang}' ---")

        discover_command = [
            "scrapy",
            "crawl",
            "discover",
            "-a",
            f"seed_terms={args.terms}",
            "-a",
            f"max_urls={args.num}",
            "-o",
            SEED_FILE_WEB,
            "-s",
            f"JOBDIR={JOB_DIR}/discover",
        ]

        if not os.path.exists(SEED_FILE_WEB):
            run_command(discover_command, "Stage 1: Discovering Seed URLs")
        else:
            print(
                f"[i] STAGE 1: Skipping discovery, seed file {SEED_FILE_WEB} already exists."
            )

        seed_txt_file = get_seed_urls_from_file(SEED_FILE_WEB)
        if not seed_txt_file:
            print("--- Pipeline finished early: No URLs discovered. ---")
            sys.exit(0)

        configure_command = [
            "python",
            "-m",
            "unified_scraper.core.config_generator",
            "--input",
            seed_txt_file,
            "--output",
            SITE_CONFIG_FILE,
        ]

        if not os.path.exists(SITE_CONFIG_FILE):
            run_command(configure_command, "Stage 2: Generating Site Configurations")
        else:
            print(
                f"[i] STAGE 2: Skipping config generation, file {SITE_CONFIG_FILE} already exists."
            )

        master_command = [
            "scrapy",
            "crawl",
            "master",
            "-a",
            f"language={args.lang}",
            "-a",
            f"site_config_file={SITE_CONFIG_FILE}",
            "-s",
            f"JOBDIR={JOB_DIR}/master",
        ] + spider_args
        run_command(
            master_command, f"Stage 3: Executing Master Web Scraper for '{args.lang}'"
        )

        print("\n--- WEB Scraping Pipeline Finished ---")

    elif args.command == "pdf":
        print(f"--- Starting PDF Scraping Pipeline for '{args.lang}' ---")

        discover_command = [
            "scrapy",
            "crawl",
            "discover",
            "-a",
            f"seed_terms={args.terms}",
            "-a",
            f"max_urls={args.num}",
            "-o",
            SEED_FILE_PDF,
            "-s",
            f"JOBDIR={JOB_DIR}/discover",
        ]

        if not os.path.exists(SEED_FILE_PDF):
            run_command(discover_command, "Stage 1: Discovering Seed URLs")
        else:
            print(
                f"[i] STAGE 1: Skipping discovery, seed file {SEED_FILE_PDF} already exists."
            )

        seed_txt_file = get_seed_urls_from_file(SEED_FILE_PDF)
        if not seed_txt_file:
            print("--- Pipeline finished early: No URLs discovered. ---")
            sys.exit(0)

        pdf_command = [
            "scrapy",
            "crawl",
            "language_pdf",
            "-a",
            f"lang={args.lang}",
            "-a",
            f"seed_file={seed_txt_file}",
            "-s",
            f"JOBDIR={JOB_DIR}/language_pdf",
        ] + spider_args
        run_command(
            pdf_command, f"Stage 3: Executing PDF Language Scraper for '{args.lang}'"
        )

        print("\n--- PDF Scraping Pipeline Finished ---")


if __name__ == "__main__":
    main()
