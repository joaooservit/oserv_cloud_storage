import os
import msal
import requests
import time
from tqdm import tqdm
from parameters import *

# Diretório corrente inicial
current_folder_id = root_folder_id
current_folder_name = "/"

def main():
    access_token = get_access_token()
    while True:
        command = input(f'[{current_folder_name}] >> ').strip().split()
        if not command:
            continue

        if command[0] == 'ls':
            list_files(access_token)
        elif command[0] == 'upload' and len(command) > 1:
            upload(access_token, command[1])
        elif command[0] == 'download' and len(command) > 1:
            download(access_token, command[1])
        elif command[0] == 'cd' and len(command) > 1:
            change_directory(access_token, command[1])
        elif command[0] == 'help':
            show_help()
        elif command[0] == 'exit':
            print('Finishing...')
            break
        else:
            print('Invalid command')
            show_help()

def show_help():
    help_message = '''
Available commands:
  ls                - List files and directories in the current directory
  upload [path]     - Upload a file or folder to the current directory
  download [path]   - Download a file or folder from the current directory
  cd [directory]    - Change the current directory
  cd ..             - Go up one directory level (cannot go above root)
  help              - Show this help message
  exit              - Exit the program
'''
    print(help_message)

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

CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB por fragmento

def create_upload_session(access_token, file_name, folder_id):
    url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{folder_id}:/{file_name}:/createUploadSession'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    data = {
        "item": {
            "@microsoft.graph.conflictBehavior": "rename",
            "name": file_name
        }
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erro ao criar a sessão de upload: {response.status_code}")
        print(response.json())
        return None
    

def upload_file_in_chunks(access_token, file_name, folder_id=None):
    global current_folder_id
    folder_id = folder_id or current_folder_id
    file_size = os.path.getsize(file_name)
    file_base_name = os.path.basename(file_name)

    upload_session = create_upload_session(access_token, file_base_name, folder_id)
    if not upload_session:
        return None

    upload_url = upload_session['uploadUrl']
    with open(file_name, 'rb') as file_data, tqdm(total=file_size, unit='B', unit_scale=True, desc=file_base_name) as pbar:
        chunk_number = 0
        while True:
            chunk_data = file_data.read(CHUNK_SIZE)
            if not chunk_data:
                break
            start_index = chunk_number * CHUNK_SIZE
            end_index = start_index + len(chunk_data) - 1
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Range': f'bytes {start_index}-{end_index}/{file_size}'
            }
            start_time = time.time()
            response = requests.put(upload_url, headers=headers, data=chunk_data)
            end_time = time.time()
            if response.status_code not in [200, 201, 202]:
                print(f"Erro ao enviar o fragmento {chunk_number}: {response.status_code}")
                print(response.json())
                return None
            chunk_number += 1
            pbar.update(len(chunk_data))
            print(f"Velocidade média do fragmento: {len(chunk_data) / (end_time - start_time) / 1024:.2f} KB/s")

    print("Upload bem-sucedido!")
    return True

def list_files(access_token):
    global current_folder_id
    files = list_folder_contents(access_token, current_folder_id)
    if files is None or 'value' not in files:
        print(f"Erro ao listar conteúdo da pasta '{current_folder_name}'.")
        return

    for file in files['value']:
        file_type = 'DIR' if 'folder' in file else 'FILE'
        print(f"{file['name']} - {file_type}")

def list_folder_contents(access_token, folder_id):
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
        upload_file_in_chunks(access_token, file_name)

def upload_file(access_token, file_name, folder_id=None):
    global current_folder_id
    folder_id = folder_id or current_folder_id
    file_base_name = os.path.basename(file_name)
    url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{folder_id}:/{file_base_name}:/content'

    file_size = os.path.getsize(file_name)
    with open(file_name, 'rb') as file_data, tqdm(total=file_size, unit='B', unit_scale=True, desc=file_base_name) as pbar:
        start_time = time.time()
        response = requests.put(
            url,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/octet-stream'
            },
            data=read_in_chunks(file_data, pbar)
        )
        end_time = time.time()

    if response.status_code in [200, 201]:
        print(f"Upload bem-sucedido! Velocidade média: {file_size / (end_time - start_time) / 1024:.2f} KB/s")
        return response.json()
    else:
        print(f"Erro no upload: {response.status_code}")
        print(response.json())
        return None

def read_in_chunks(file_object, pbar, chunk_size=8192):
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        pbar.update(len(data))
        yield data

def create_folder(access_token, folder_name, folder_id=None):
    global current_folder_id
    folder_id = folder_id or current_folder_id
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

def upload_folder(access_token, folder_path):
    global current_folder_id
    folder_name = os.path.basename(folder_path)
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

def download(access_token, file_name):
    files = list_folder_contents(access_token, current_folder_id)
    if files is None or 'value' not in files:
        print("Erro ao obter a lista de arquivos.")
        return

    for file in files['value']:
        if file['name'] == file_name:
            if 'folder' in file:
                download_folder(access_token, file_name, file['id'])
            else:
                download_file(access_token, file_name, file['id'])
            break
    else:
        print(f"Item '{file_name}' não encontrado no SharePoint.")

def download_file(access_token, file_name, file_id):
    url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{file_id}/content'
    
    response = requests.get(
        url,
        headers={'Authorization': f'Bearer {access_token}'},
        stream=True
    )

    total_size = int(response.headers.get('content-length', 0))
    start_time = time.time()
    with open(file_name, 'wb') as file, tqdm(total=total_size, unit='B', unit_scale=True, desc=file_name) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file.write(chunk)
                pbar.update(len(chunk))
    end_time = time.time()

    if response.status_code == 200:
        print(f"Download bem-sucedido! Velocidade média: {total_size / (end_time - start_time) / 1024:.2f} KB/s")
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

def download_folder(access_token, folder_name, folder_id):
    local_folder_name = folder_name.replace(' ', '_')
    os.makedirs(local_folder_name, exist_ok=True)
    
    download_folder_contents(access_token, folder_id, local_folder_name)

def change_directory(access_token, directory_name):
    global current_folder_id, current_folder_name

    if directory_name == '..':
        if current_folder_id == root_folder_id:
            print("Você já está no diretório raiz e não pode subir mais.")
            return

        parent_folder_name = '/'.join(current_folder_name.strip('/').split('/')[:-1])
        parent_folder_id = root_folder_id
        if parent_folder_name:
            parent_folder_contents = list_folder_contents(access_token, root_folder_id)
            for item in parent_folder_contents['value']:
                if item['name'] == parent_folder_name and 'folder' in item:
                    parent_folder_id = item['id']
                    break
        current_folder_id = parent_folder_id
        current_folder_name = '/' if not parent_folder_name else f'/{parent_folder_name}'
    else:
        files = list_folder_contents(access_token, current_folder_id)
        if files is None or 'value' not in files:
            print("Erro ao obter a lista de arquivos.")
            return
        
        for file in files['value']:
            if file['name'] == directory_name and 'folder' in file:
                current_folder_id = file['id']
                current_folder_name = current_folder_name.rstrip('/') + f'/{directory_name}'
                break
        else:
            print(f"Diretório '{directory_name}' não encontrado.")

if __name__ == '__main__':
    main()
