import os
import msal
import requests
from parameters import * 

site_id = 'oservcombr.sharepoint.com,1a56d7c5-bb8e-4c78-aafb-c0ccaa39d5c8,e7396a79-87bd-4e23-bfb5-92a0b31e858e'
folder_id = '012K4Y663ZLNZ56AX4HRAYJRL4PC3H4Y66'

def init():
    welcome_message = '''
==========================
oserv-cloud-storage - 1.0v
@author: Joao Vidal
==========================

'''
    print(welcome_message)
    while True:
        access_token = get_access_token()
        print('1 - Upload file')
        print('2 - Upload folder')
        print('3 - Download file')
        print('4 - Exit')
        option = input('Choose an option: ')
        
        if option == '1':
            print('Atencao: Você precisa estar no diretorio onde o arquivo esta localizado')
            file_name = input('Enter the file name that you want to upload: ')
            (upload_file(access_token, file_name, folder_id))
        elif option == '2':
            (upload_directory(access_token))
        elif option == '3':
            (download_file(access_token, file_name))
        elif option == '4':
            print('Finishing...')
            break
        else:
            print('Invalid option')
        input('Press Enter to continue...')
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


def list_folder_contents(access_token):
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


def upload_file(access_token, file_name, folder_id):

    url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{folder_id}:/{file_name}:/content'
    
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
        print("Upload bem-sucedido!")
        return response.json()
    else:
        print(f"Erro no upload: {response.status_code}")
        print(response.json())
        return None
    
def create_folder(access_token, folder_name):
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
        print(f"Folder '{folder_name}' criado com sucesso!")
        return response.json()
    else:
        print(f"Erro ao criar a pasta '{folder_name}': {response.status_code}")
        print(response.json())
        return None
    
def upload_directory(access_token):
    folder_name = input('Enter the folder name that you want to upload: ')
    for root, dirs, files in os.walk(folder_name):
        relative_path = os.path.relpath(root, folder_name)
        remote_folder_id = folder_id
        
        if relative_path != '.':
            # Cria a estrutura de pastas no SharePoint
            parts = relative_path.split(os.sep)
            for part in parts:
                folder = create_folder(access_token, part)
                if folder:
                    remote_folder_id = folder['id']
        
        for file_name in files:
            file_path = os.path.join(root, file_name)
            upload_file(access_token, file_path, remote_folder_id)
    
def download_file(access_token):

    file_name = input('Enter the file name that you want to download: ')
    files = list_folder_contents(access_token)
    for file in files['value']:
        print(file['name'])
        if file['name'] == file_name:
            file_id = file['id']
            break

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
        print("Download bem-sucedido!")
        return True
    else:
        print(f"Erro no download: {response.status_code}")
        print(response.json())
        return False

if __name__ == '__main__':
    init()
   