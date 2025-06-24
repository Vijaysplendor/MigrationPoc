import base64
import yaml
import requests
from requests.auth import HTTPBasicAuth

     
# Download the yaml file using REST API

def initial_conversion():
    # Input file containing the URLs
    input_file = "Intial_URL_to_be_converted.txt"
    # Output file
    output_file = "converted_urls.txt"

    # Clear the contents of outfile if any
    print(f"Clearing the contents of outfile if any .....")
    with open(output_file, 'w') as file:
        pass

    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            print(f"Value of url is - {line}")
        
            # Extract text before _build
            text_before_build = line.split('_build')[0]
        
            # Extract definitionID value
            definition_id = line.split('definitionId=')[1].split('&')[0]
        
            # Construct new URL
            new_url = f"{text_before_build}_apis/build/definitions/{definition_id}/yaml"
            print(f"Converted REST API url is - {new_url}")
            print("------------------------------------------------------------------------------------------")
        
            # Write extracted text to output file
            with open(output_file, 'a') as out_f:
                out_f.write(f"{new_url}\n")

def convert_classic_to_yaml(url,url_count):
    #validate each url
    #base_url = url
    pat = ''
               
    authorization = str(base64.b64encode(bytes(':'+pat, 'ascii')), 'ascii')

    headers = {
         'Accept': 'application/json',
         'Authorization': 'Basic '+authorization
    }
    print(f'Pipeline url to be converted to yaml format is {url}')
    print(f'pipeline : {url_count}')
    response = requests.get(url, headers=headers)
    print(f'Authentication is success and response is {response}')
    response.raise_for_status()

    # Set the output file path
    outfile = "pipeline" + str(url_count) + ".yaml"
    print(f'The converted yaml pipeline is available in the path: {outfile}')
    
    # Extract the YAML content
    yaml_content = response.json()["yaml"]

    # Remove "..." from the YAML content
    yaml_content = yaml_content.replace("...", "")

    # Write the YAML content to the output file
    with open(outfile, "w") as f:
        f.write(yaml_content)

# Main execution
if __name__ == '__main__':
    initial_conversion ()
    with open("converted_urls.txt", "r") as f:
       un_parsed_urls = f.readlines()
    parsed_urls = [url.replace("\n", "") for url in un_parsed_urls]
    url_count = 0
    for url in parsed_urls:
        url_count += 1
        convert_classic_to_yaml (url, url_count)
        print(f'Total number of urls converted to yaml format is: {url_count}')
        print(f'------------------------------------------------------------------------------------------------')
