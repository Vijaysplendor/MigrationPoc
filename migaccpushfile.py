import base64
import requests
from requests.auth import HTTPBasicAuth
import json

# Azure DevOps organization URL and PAT
pat = ''
repository = "PartsUnlimited"
authorization = str(base64.b64encode(bytes(':'+pat, 'ascii')), 'ascii')
headers = {
         'Accept': 'application/json',
         'Authorization': 'Basic '+authorization
    }

#Rest API End Points
initial_base_url = f"https://dev.azure.com/VI20040428/PartsUnlimitedTest/_apis/git/repositories/{repository}"
repo_id_url = f"{initial_base_url}?api-version=6.0"

# code to get the repository_id
def get_repo_id():
    response = requests.get(repo_id_url, headers=headers)
    if response.status_code == 200:
        #Parse the JSON response
        repo_data = response.json()
        repo_id = repo_data['id']
        print(f"Repository ID for {repository} is: {repo_id}")
        return repo_id
    else:
        print(f"Failed to retrieve repo ID. status code: {response.status_code}")
        print(f"Error message: {response.text}")

repository_id = get_repo_id()
#Rest API End Points
base_url = f"https://dev.azure.com/VI20040428/PartsUnlimitedTest/_apis/git/repositories/{repository_id}"
#base_url = f"https://dev.azure.com/VI20040428/PartsUnlimitedTest/_apis/git/repositories/{repository}"
branch_url = f"{base_url}/refs?api-version=6.0"
#commit_url = f"{base_url}/pushes?api-version=6.0"
new_branch_name = "vijay-test-demo"
master_branch_name = "master"
   
# read the yaml file content from local path
def read_local_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
            return content
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        return None
    
def get_latest_commit():
    url = f"{base_url}/refs?filter=heads/{master_branch_name}&api-version=6.0"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    latest_commit = data['value'][0]['objectId']
    print(f"Value of latest commit is: {latest_commit}")
    return latest_commit

def create_branch(file_content):
    latest_commit = get_latest_commit()
    url = f"{base_url}/pushes?api-version=6.0"    
    data = {
        "refUpdates": [
            {
                "name": f"refs/heads/{new_branch_name}",
                "oldObjectId": "0000000000000000000000000000000000000000"
                #"newObjectId": latest_commit
            }
        ],
        "commits": [
            {
                "comment": "creating new branch from master",
                "changes": [
                    {
                        "changeType": "add",
                        "item": {
                            "path": "/pipeline1.yaml"
                        },
                        "newContent": {
                            "content": file_content,
                            "contentType": "rawText"
                        }
                    }
                ]
            }
        ]         
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    print(f"New Branch '{new_branch_name}' created successfully.")
    
         
def main():
    file_path = "pipeline1.yaml"
    file_content = read_local_file(file_path)
    if file_content:
        branch_name = create_branch(file_content)
        


# USage example
if __name__ == '__main__':
    main()
 
