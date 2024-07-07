import os
import msal
import requests
from parameters import *

def init():
    welcome_message = '''
==========================
oserv-cloud-storage - 1.0v
@author: Joao Vidal
==========================
'''
    access_token = get_access_token()

    print(welcome_message)
    while True:
        print('1 - Upload file/folder')
        print('2 - Download file/folder')
        print('3 - Exit')
        option = input('Choose an option: ')
        
        if option == '1':
            file_name = input('Enter the file/folder that you want to upload [ FULL PATH ]: ')
            # verifica se ha um ./ no inicio do caminho e remove
            if file_name[0] == '.' and file_name[1] == '/':
                file_name = file_name[2:]
                # adiciona o current_dir no caminho do arquivo
                file_name = os.path.join(os.getcwd(), file_name)
            upload(access_token, file_name)            
        elif option == '2':
            file_name = input('Enter the file/folder that you want to download: ')
            download(access_token, file_name)
        elif option == '3':
            print('Finishing...')
            break
        else:
            print('Invalid option')
        input('Press Enter to continue...')

        # Verifica se o sistema operacional é Windows
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')


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


def list_folder_contents(access_token, folder_id=root_folder_id):
    url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{folder_id}/children'
    response = requests.get(
        url,
        headers={'Authorization': f'Bearer {access_token}'}
    )
    if response.status_code != 200:
        print(f"Erro ao listar conteúdo da pasta: {response.status_code}")
        print(response.json())
        return None
    return response.json()

def upload(access_token, file_name):

    if os.path.isdir(file_name):
        upload_folder(access_token, file_name)
    else: 
        upload_file(access_token, file_name)
    
    print("Upload concluído.")

def upload_file(access_token, file_name, folder_id=root_folder_id):

    file_base_name = os.path.basename(file_name)
    url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{folder_id}:/{file_base_name}:/content'

    with open(file_name, 'rb') as file_data:
        response = requests.put(
            url,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/octet-stream'
            },
            data=file_data
        )
    
    if response.status_code in [200, 201]:
        return response.json()
    else:
        print(f"Erro no upload: {response.status_code}")
        print(response.json())
        return None
    
def create_folder(access_token, folder_name, folder_id=root_folder_id):
    url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{folder_id}/children'
    
    folder_data = {
        "name": folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "rename"
    }
    
    response = requests.post(
        url,
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        },
        json=folder_data
    )
    
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Erro ao criar a pasta '{folder_name}': {response.status_code}")
        print(response.json())
        return None
    
def upload_folder(access_token, folder_path):
    folder_name = os.path.basename(folder_path)
    # Cria a pasta raiz no SharePoint
    root_folder = create_folder(access_token, folder_name)
    if not root_folder:
        print("Erro ao criar a pasta raiz.")
        return
    
    root_folder_id = root_folder['id']
    
    for root, dirs, files in os.walk(folder_path):
        relative_path = os.path.relpath(root, folder_path)
        remote_folder_id = root_folder_id

        if relative_path != '.':
            parts = relative_path.split(os.sep)
            for part in parts:
                folder = create_folder(access_token, part, remote_folder_id)
                if folder:
                    remote_folder_id = folder['id']
        
        for file_name in files:
            file_path = os.path.join(root, file_name)
            upload_file(access_token, file_path, remote_folder_id)

def download_file(access_token, file_name, file_id):
    url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{file_id}/content'
    
    response = requests.get(
        url,
        headers={'Authorization': f'Bearer {access_token}'},
        stream=True
    )
    
    if response.status_code == 200:
        with open(file_name, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return True
    else:
        print(f"Erro no download: {response.status_code}")
        print(response.json())
        return False

def download_folder_contents(access_token, folder_id, local_folder_name):
    files = list_folder_contents(access_token, folder_id)
    
    if files is None or 'value' not in files:
        print(f"Erro ao listar conteúdo da pasta '{local_folder_name}'.")
        return
    
    for file in files['value']:
        if 'folder' in file:
            subfolder_name = file['name'].replace(' ', '_')
            local_subfolder_path = os.path.join(local_folder_name, subfolder_name)
            os.makedirs(local_subfolder_path, exist_ok=True)
            download_folder_contents(access_token, file['id'], local_subfolder_path)
        else:
            file_name = file['name'].replace(' ', '_')
            local_file_path = os.path.join(local_folder_name, file_name)
            download_file(access_token, local_file_path, file['id'])

def download_folder(access_token, folder_name):
    files = list_folder_contents(access_token)
    if files is None or 'value' not in files:
        print("Erro ao obter a lista de arquivos.")
        return
    
    folder_id = None
    for file in files['value']:
        if file['name'] == folder_name:
            folder_id = file['id']
            break
    
    if folder_id is None:
        print(f"Folder '{folder_name}' não encontrado no SharePoint.")
        return
    
    local_folder_name = folder_name.replace(' ', '_')
    os.makedirs(local_folder_name, exist_ok=True)
    
    download_folder_contents(access_token, folder_id, local_folder_name)

def download(access_token, file_name):
    # Verifica se o arquivo é uma pasta no SharePoint
    files = list_folder_contents(access_token)
    if files is None or 'value' not in files:
        print("Erro ao obter a lista de arquivos.")
        return

    for file in files['value']:
        if file['name'] == file_name:
            if 'folder' in file:
                download_folder(access_token, file_name)
            else:
                download_file(access_token, file_name, file['id'])
            break
    else:
        print(f"Item '{file_name}' não encontrado no SharePoint.")
    
    print("Download concluído.")

if __name__ == '__main__':
    init()
