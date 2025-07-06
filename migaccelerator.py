import os
import base64
import requests
import json
import re
from urllib.parse import urlparse

# Headers will be initialized dynamically
headers = {}

def parse_pipeline_url(url):
    """
    Parse Azure DevOps pipeline URL to extract organization, project, and definition ID
    Expected format: https://dev.azure.com/{org}/{project}/_apis/build/definitions/{id}/yaml
    """
    try:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        if 'dev.azure.com' in parsed.netloc:
            org = path_parts[0]
            project = path_parts[1]
            definition_id = path_parts[4]
        else:
            raise ValueError(f"Unsupported URL format: {url}")
            
        return {
            'organization': org,
            'project': project,
            'definition_id': definition_id,
            'base_url': f"https://dev.azure.com/{org}/{project}"
        }
    except Exception as e:
        print(f"Error parsing URL {url}: {e}")
        return None

def get_repositories(org, project):
    url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories?api-version=6.0"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        repos_data = response.json()
        repositories = {repo['name']: repo['id'] for repo in repos_data['value']}
        print(f"Found {len(repositories)} repositories in project {project}")
        return repositories
    else:
        print(f"Failed to retrieve repositories. Status code: {response.status_code}")
        print(f"Error message: {response.text}")
        return {}

def get_converted_yaml_content(yaml_url):
    response = requests.get(yaml_url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to retrieve YAML content from {yaml_url}")
        print(f"Status code: {response.status_code}, Error: {response.text}")
        return None

def get_latest_commit(org, project, repo_id, branch_name="master"):
    base_url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}"
    url = f"{base_url}/refs?filter=heads/{branch_name}&api-version=6.0"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data['value']:
            latest_commit = data['value'][0]['objectId']
            print(f"Latest commit for {branch_name}: {latest_commit}")
            return latest_commit
        else:
            print(f"No commits found for branch {branch_name}")
            return None
    else:
        print(f"Failed to get latest commit. Status code: {response.status_code}")
        return None

def create_branch_with_yaml(org, project, repo_id, repo_name, yaml_content, definition_id):
    new_branch_name = f"converted-pipeline-{definition_id}"
    base_url = f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo_id}"
    
    latest_commit = get_latest_commit(org, project, repo_id, "master")
    if not latest_commit:
        latest_commit = get_latest_commit(org, project, repo_id, "main")
    
    if not latest_commit:
        print(f"Could not find master or main branch for repository {repo_name}")
        return False
    
    url = f"{base_url}/pushes?api-version=6.0"
    
    data = {
        "refUpdates": [
            {
                "name": f"refs/heads/{new_branch_name}",
                "oldObjectId": "0000000000000000000000000000000000000000"
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
                            "content": yaml_content,
                            "contentType": "rawText"
                        }
                    }
                ]
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print(f"✅ Successfully created branch '{new_branch_name}' in repository '{repo_name}'")
        print(f"   Pipeline file: /pipelines/converted-pipeline-{definition_id}.yaml")
        return True
    else:
        print(f"❌ Failed to create branch in repository '{repo_name}'")
        print(f"   Status code: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

def read_input_urls(file_path):
    try:
        with open(file_path, 'r') as file:
            urls = [line.strip() for line in file if line.strip()]
            return urls
    except FileNotFoundError:
        print(f"Input file '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"Error reading input file '{file_path}': {e}")
        return []

def process_pipeline(pipeline_info):
    org = pipeline_info['organization']
    project = pipeline_info['project']
    definition_id = pipeline_info['definition_id']
    
    print(f"\n🔄 Processing pipeline {definition_id} from project '{project}'...")
    
    yaml_url = f"https://dev.azure.com/{org}/{project}/_apis/build/definitions/{definition_id}/yaml"
    yaml_content = get_converted_yaml_content(yaml_url)
    
    if not yaml_content:
        print(f"❌ Failed to get YAML content for pipeline {definition_id}")
        return False
    
    repositories = get_repositories(org, project)
    if not repositories:
        print(f"❌ No repositories found for project {project}")
        return False
    
    target_repo = None
    target_repo_id = None
    
    if project in repositories:
        target_repo = project
        target_repo_id = repositories[project]
    else:
        target_repo = list(repositories.keys())[0]
        target_repo_id = repositories[target_repo]
    
    print(f"📁 Target repository: {target_repo} (ID: {target_repo_id})")
    
    return create_branch_with_yaml(org, project, target_repo_id, target_repo, yaml_content, definition_id)

def main(input_file):
    original_urls = read_input_urls(input_file)
    if not original_urls:
        print("No URLs found in input file. Exiting.")
        return
    
    yaml_urls = []
    for url in original_urls:
        if "_build?definitionId=" in url:
            match = re.search(r'https://dev\.azure\.com/([^/]+)/([^/]+)/_build\?definitionId=(\d+)', url)
            if match:
                org, project, def_id = match.groups()
                yaml_url = f"https://dev.azure.com/{org}/{project}/_apis/build/definitions/{def_id}/yaml"
                yaml_urls.append(yaml_url)
    
    if not yaml_urls:
        print("No valid pipeline URLs found. Exiting.")
        return
    
    print(f"Found {len(yaml_urls)} pipelines to process:")
    for url in yaml_urls:
        print(f"  - {url}")
    
    successful_count = 0
    for yaml_url in yaml_urls:
        pipeline_info = parse_pipeline_url(yaml_url)
        if pipeline_info:
            success = process_pipeline(pipeline_info)
            if success:
                successful_count += 1
        else:
            print(f"❌ Failed to parse URL: {yaml_url}")
    
    print(f"\n📊 Summary: {successful_count}/{len(yaml_urls)} pipelines processed successfully")

def run_pipeline_conversion(pat_env_var="ADO_PAT", input_file="Intial_URL_to_be_converted.txt"):
    global headers

    pat = os.environ.get(pat_env_var)
    if not pat:
        raise ValueError(f"{pat_env_var} environment variable not set.")

    authorization = str(base64.b64encode(bytes(':'+pat, 'ascii')), 'ascii')
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+authorization
    }

    try:
        main(input_file)
        return {"status": "complete"}
    except Exception as e:
        print(f"Error running pipeline conversion: {e}")
        return {"status": "error", "message": str(e)}
        
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run pipeline conversion.")
    parser.add_argument("--pat-env-var", default="ADO_PAT", help="Name of the environment variable containing the Azure DevOps PAT")
    parser.add_argument("--input-file", default="Intial_URL_to_be_converted.txt", help="Input file with pipeline URLs")

    args = parser.parse_args()
    result = run_pipeline_conversion(pat_env_var=args.pat_env_var, input_file=args.input_file)
    print(result)
