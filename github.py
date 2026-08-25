import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_USERNAME = "porav-cmd"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def get_user_repos(username=GITHUB_USERNAME):
    try:
        url = f"https://api.github.com/users/{username}/repos"
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        repos = [r["name"] for r in response.json() if not r.get("fork", False)]
        return repos if repos else ["DevFlow", "echo"]
    except Exception as e:
        print(f"Warning: GitHub API error fetching repos ({e}). Using fallback repo list...")
        return ["DevFlow", "echo"]


def get_repo_files(repo_name):
    try:
        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/git/trees/main?recursive=1"
        headers = {}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        tree = data.get("tree", [])

        files = []
        for item in tree:
            if item.get("type") == "blob":
                files.append(item["path"])
        return files
    except Exception as e:
        print(f"Warning: GitHub API error ({e}). Using local fallback file tree...")
        fallback_files = []
        for root, _, filenames in os.walk("."):
            for fname in filenames:
                rel_path = os.path.relpath(os.path.join(root, fname), ".").replace("\\", "/")
                if not rel_path.startswith(".venv") and not rel_path.startswith(".git"):
                    fallback_files.append(rel_path)
        return fallback_files


def filter_meaningful_files(files):

    filtered_files = []

    ignored_names = {
        "__init__.py",
        ".gitignore",
        "manage.py",
    }

    ignored_directories = {
        "migrations",
        "__pycache__",
        ".git",
    }

    ignored_extensions = {
        ".html",
        ".css",
        ".js",
    }

    for file in files:

        filename = file.split("/")[-1]
        directories = file.split("/")

        if filename in ignored_names:
            continue

        if any(
            directory in directories
            for directory in ignored_directories
        ):
            continue

        if any(file.endswith(ext) for ext in ignored_extensions):
            continue

        filtered_files.append(file)

    return filtered_files


repo = get_repo_files("echo")

filtered = filter_meaningful_files(repo)

print("Meaningful files:")

for file in filtered:
    print(file)
    

def get_repo_readme(repo_name):
    try:
        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{repo_name}/readme"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        content = data["content"]
        decoded_bytes = base64.b64decode(content)
        readme_text = decoded_bytes.decode("utf-8")
        return readme_text[:800]
    except Exception as e:
        print(f"Warning: Could not fetch README for {repo_name}: {e}")
        return "No README available for this repository."    

def get_file_content(repo_name, file_path):
    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_USERNAME}/{repo_name}/contents/{file_path}"
    )

    response = requests.get(url)

    response.raise_for_status()

    data = response.json()

    content = data["content"]


    decoded_bytes = base64.b64decode(content)

    file_text = decoded_bytes.decode("utf-8")

    
    file_text = file_text[:2000]

   
    return file_text

if __name__ == "__main__":

    content = get_file_content(
        "echo",
        "api/langgraph_service.py"
    )

    print(content)