import os
import subprocess
import asyncio
import logging
from dataclasses import dataclass
from typing import List
import shutil
from pathlib import Path
import tempfile
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("runner_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class RepoConfig:
    repo_url: str
    branch: str
    start_cmd: str
    name: str = None

    def __post_init__(self):
        if not self.name:
            repo_name = self.repo_url.rstrip('/').split('/')[-1]
            repo_name = repo_name.replace('.git', '')
            self.name = f"{repo_name}@{self.branch}"

class RepoRunner:
    def __init__(self, base_dir: str = "projects"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def setup_repo(self, config: RepoConfig) -> Path:
        repo_dir = self.base_dir / config.name
        venv_name = f"{config.name}-venv"
        
        if repo_dir.exists():
            logger.info(f"[{config.name}] Removing existing repository...")
            shutil.rmtree(repo_dir)
        
        repo_dir.mkdir(parents=True, exist_ok=True)
        
        setup_script = f"""#!/bin/bash
set -e

echo "Cloning {config.repo_url} ({config.branch})..."
git clone -b {config.branch} {config.repo_url} {repo_dir} || {{ echo 'Git clone failed'; exit 1; }}

cd {repo_dir}
echo "Creating virtual environment..."
python3 -m venv {venv_name} || {{ echo 'VenV creation failed'; exit 1; }}

. {venv_name}/bin/activate
if [ -f requirements.txt ]; then
    echo "Installing dependencies..."
    pip install --quiet -U -r requirements.txt || {{ echo 'Dependency installation failed'; exit 1; }}
fi
echo "Setup completed successfully"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as script_file:
            script_file.write(setup_script)
            script_path = script_file.name
        
        os.chmod(script_path, 0o755)

        try:
            logger.info(f"[{config.name}] Starting repository setup...")
            process = subprocess.Popen(
                ['/bin/bash', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    logger.info(f"[{config.name} SETUP] {line.strip()}")

            exit_code = process.wait()
            if exit_code != 0:
                raise subprocess.CalledProcessError(exit_code, script_path)

            logger.info(f"[{config.name}] Setup completed successfully")
            return repo_dir, venv_name
        
        except subprocess.CalledProcessError as e:
            logger.error(f"[{config.name}] SETUP FAILED: {str(e)}")
            raise
        finally:
            os.unlink(script_path)
            if process and process.poll() is None:
                process.kill()

    def run_command(self, config: RepoConfig):
        try:
            repo_dir, venv_name = self.setup_repo(config)
            
            run_script = f"""#!/bin/bash
cd {repo_dir}
. {venv_name}/bin/activate
echo "Starting bot process..."
exec {config.start_cmd}
"""
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as script_file:
                script_file.write(run_script)
                script_path = script_file.name
            
            os.chmod(script_path, 0o755)

            process = subprocess.Popen(
                ['/bin/bash', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            process.script_path = script_path
            return process
        
        except Exception as e:
            logger.error(f"[{config.name}] FATAL ERROR: {str(e)}")
            traceback.print_exc()
            return None

async def monitor_process(name, process):
    try:
        while True:
            stdout_line = process.stdout.readline()
            if stdout_line:
                logger.info(f"[{name} STDOUT] {stdout_line.strip()}")
            
            stderr_line = process.stderr.readline()
            if stderr_line:
                logger.error(f"[{name} STDERR] {stderr_line.strip()}")
            
            if process.poll() is not None:
                for line in process.stdout:
                    logger.info(f"[{name} STDOUT] {line.strip()}")
                for line in process.stderr:
                    logger.error(f"[{name} STDERR] {line.strip()}")
                break
            
            await asyncio.sleep(0.1)
        
        exit_code = process.poll()
        logger.info(f"[{name}] Process exited with code {exit_code}")
    finally:
        if hasattr(process, 'script_path') and os.path.exists(process.script_path):
            os.unlink(process.script_path)

async def run_repos(configs: List[RepoConfig]):
    runner = RepoRunner()
    processes = []
    
    try:
        for config in configs:
            process = runner.run_command(config)
            if process:
                processes.append((config.name, process))
                asyncio.create_task(monitor_process(config.name, process))
                logger.info(f"[{config.name}] Bot started successfully")
        
        await asyncio.gather(*[monitor_process(name, p) for name, p in processes])
    except KeyboardInterrupt:
        logger.info("[SYSTEM] Shutting down bots...")
        for name, process in processes:
            try:
                process.kill()
                logger.info(f"[{name}] Terminated")
            except:
                pass

async def main():
    #if repo is private the add token with link as shown below
    configs = [
        RepoConfig("https://<token>@github.com/kagut57/mangabot/", "master", "python3 main.py"),
        RepoConfig("https://github.com/Joyboy125/Auto-Rename-Bot.git", "main", "python3 bot.py")
    ]

    try:
        await run_repos(configs)
    except Exception as e:
        logger.critical(f"[SYSTEM] Critical error: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
