import requests
import msal
from parameters import *

def get_access_token():
    app = msal.ConfidentialClientApplication(
        APPLICATION_ID,
        authority=AUTHORITY_URL,
        client_credential=VALUE
    )
    
    result = app.acquire_token_for_client(scopes=SCOPES)
    
    if 'access_token' in result:
        return result['access_token']
    else:
        raise Exception('Could not obtain access token')

def get_root_folder_id(access_token, folder_name):
    url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root/children'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Erro ao listar conteúdo da raiz: {response.status_code}")
        print(response.json())
        return None

    items = response.json().get('value', [])
    for item in items:
        if item['name'] == folder_name and 'folder' in item:
            return item['id']
    return None

if __name__ == '__main__':
    access_token = get_access_token()
    folder_name = 'Oserv Cloud Storage'  # Substitua pelo nome da sua nova pasta raiz
    root_folder_id = get_root_folder_id(access_token, folder_name)
    if root_folder_id:
        print(f"O ID da pasta '{folder_name}' é: {root_folder_id}")
    else:
        print(f"Pasta '{folder_name}' não encontrada.")
