import os
import base64
import requests
import json
import re
import pyyaml
from urllib.parse import urlparse

# Headers will be initialized dynamically
headers = {}

def get_repositories(org, project):
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories?api-version=6.0"
    print(f"\n📥 Requesting repositories from: {url}")
    print(f"🔐 Using headers: {headers}")

    response = requests.get(url, headers=headers)
    print(f"📡 Status code: {response.status_code}")
    print(f"📃 Response: {response.text}")

    if response.status_code == 200:
        repos_data = response.json()
        repositories = {repo['name']: repo['id'] for repo in repos_data['value']}
        print(f"✅ Found {len(repositories)} repositories in project '{project}'")
        return repositories
    else:
        print(f"❌ Failed to retrieve repositories.")
        return {}

def get_converted_yaml_content(yaml_url):
    print(f"\n📥 Fetching YAML content from: {yaml_url}")
    response = requests.get(yaml_url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"❌ Failed to retrieve YAML content.")
        print(f"🔢 Status code: {response.status_code}, 🧾 Error: {response.text}")
        return None

def get_latest_commit(org, project, repo_id, branch_name="master"):
    base_url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}"
    url = f"{base_url}/refs?filter=heads/{branch_name}&api-version=6.0"
    print(f"\n🔍 Getting latest commit for branch '{branch_name}'")

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data['value']:
            latest_commit = data['value'][0]['objectId']
            print(f"✅ Latest commit on '{branch_name}': {latest_commit}")
            return latest_commit
        else:
            print(f"⚠️ No commits found for branch '{branch_name}'")
            return None
    else:
        print(f"❌ Failed to get latest commit. Status code: {response.status_code}")
        return None

def create_branch_with_yaml(org, project, repo_id, repo_name, yaml_content, definition_id):
    new_branch_name = f"converted-pipeline-{definition_id}"
    base_url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}"

    latest_commit = get_latest_commit(org, project, repo_id, "master") or \
                    get_latest_commit(org, project, repo_id, "main")

    if not latest_commit:
        print(f"❌ Could not find master or main branch for repository '{repo_name}'")
        return False

    url = f"{base_url}/pushes?api-version=6.0"

    # ✅ Ensure the YAML content is formatted properly
    try:
        parsed_yaml = yaml.safe_load(yaml_content)
        yaml_content_pretty = yaml.dump(parsed_yaml, sort_keys=False, default_flow_style=False)
        print(f"\n🔍 YAML content reformatted successfully.")
    except Exception as e:
        print(f"⚠️ Failed to reformat YAML: {e}")
        yaml_content_pretty = yaml_content  # fallback

    data = {
        "refUpdates": [
            {
                "name": f"refs/heads/{new_branch_name}",
                "oldObjectId": latest_commit
            }
        ],
        "commits": [
            {
                "comment": f"Add converted YAML pipeline (definition ID: {definition_id})",
                "changes": [
                    {
                        "changeType": "add",
                        "item": {
                            "path": f"/pipelines/converted-pipeline-{definition_id}.yaml"
                        },
                        "newContent": {
                            "content": yaml_content_pretty,
                            "contentType": "rawText"
                        }
                    }
                ]
            }
        ]
    }

    print(f"\n🚀 Creating branch '{new_branch_name}' in repo '{repo_name}'")
    response = requests.post(url, headers=headers, json=data)

    print(f"📡 Push response: {response.status_code}")
    print(f"📃 {response.text}")

    if response.status_code == 201:
        print(f"✅ Successfully created branch and added pipeline YAML.")
        return True
    else:
        print(f"❌ Failed to create branch or commit YAML.")
        return False

def read_input_urls(file_path):
    try:
        with open(file_path, 'r') as file:
            urls = [line.strip() for line in file if line.strip()]
            return urls
    except FileNotFoundError:
        print(f"❌ Input file '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"❌ Error reading input file: {e}")
        return []

def process_pipeline(org, project, definition_id):
    print(f"\n🔄 Processing pipeline definition ID: {definition_id} from project '{project}'")

    yaml_url = f"https://dev.azure.com/{org}/{project}/_apis/build/definitions/{definition_id}/yaml"
    yaml_content = get_converted_yaml_content(yaml_url)

    if not yaml_content:
        return False

    repositories = get_repositories(org, project)
    if not repositories:
        return False

    target_repo = project if project in repositories else list(repositories.keys())[0]
    target_repo_id = repositories[target_repo]

    print(f"📁 Target repository: {target_repo} (ID: {target_repo_id})")

    return create_branch_with_yaml(org, project, target_repo_id, target_repo, yaml_content, definition_id)

def main(input_file):
    original_urls = read_input_urls(input_file)
    if not original_urls:
        print("❌ No URLs found. Exiting.")
        return

    print(f"🔗 Found {len(original_urls)} URLs to process.")

    successful_count = 0

    for url in original_urls:
        match = re.search(r'https://dev\.azure\.com/([^/]+)/([^/]+)/_build\?definitionId=(\d+)', url)
        if match:
            org, project, def_id = match.groups()
            print(f"\n📌 Matched: Org='{org}', Project='{project}', DefinitionID='{def_id}'")
            success = process_pipeline(org, project, def_id)
            if success:
                successful_count += 1
        else:
            print(f"❌ Invalid pipeline URL format: {url}")

    print(f"\n📊 Summary: {successful_count}/{len(original_urls)} pipelines processed successfully.")

def run_pipeline_conversion(pat_env_var="ADO_PAT", input_file="Intial_URL_to_be_converted.txt"):
    global headers

    pat = os.environ.get(pat_env_var)
    if not pat:
        raise ValueError(f"{pat_env_var} environment variable not set.")

    authorization = str(base64.b64encode(bytes(':' + pat, 'ascii')), 'ascii')
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic ' + authorization
    }

    print("🔐 Azure DevOps PAT initialized.")
    try:
        main(input_file)
        return {"status": "complete"}
    except Exception as e:
        print(f"❌ Error during pipeline conversion: {e}")
        return {"status": "error", "message": str(e)}
       
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run pipeline conversion.")
    parser.add_argument("--pat-env-var", default="ADO_PAT", help="Name of the environment variable containing the Azure DevOps PAT")
    parser.add_argument("--input-file", default="Intial_URL_to_be_converted.txt", help="Input file with pipeline URLs")

    args = parser.parse_args()
    result = run_pipeline_conversion(pat_env_var=args.pat_env_var, input_file=args.input_file)
    print(result)
