import csv
from flask import Flask, request, render_template, jsonify, send_file
import os
import re
import shutil
from threading import Thread
import tkinter as tk
from tkinter import messagebox
import webbrowser
import zipfile
import sys

flask_app = Flask(__name__)

def get_current_directory():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(get_current_directory(), 'uploads')
PROCESSED_FOLDER = os.path.join(get_current_directory(), 'processed')

folder_name = None
imported_files = 0
file_counter = 0
bad_files = []

# Ensure the folders exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(PROCESSED_FOLDER):
    os.makedirs(PROCESSED_FOLDER)

flask_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@flask_app.route('/')
def index():
    return render_template('index.html')

@flask_app.route('/upload', methods=['POST'])
def upload():
    global folder_name
    global imported_files
    global file_counter
    global bad_files

    print("Uploading")

    if 'files[]' not in request.files or 'importCsv' not in request.files:
        return jsonify({'message': 'Please upload a folder to process'}), 400

    folder_name = request.form.get('folderName')
    import_csv = request.files.get('importCsv')

    if not folder_name:
        return jsonify({'message': 'No folder name provided'}), 400
    
    if not re.match(r'^MT 940 \d{2} \d{2} \d{4}$', folder_name):
        return jsonify({'message': f'Folder name must be "MT 940 dd mm yyyy". {folder_name} is not valid'})

    files = request.files.getlist('files[]')
    for file in files:
        if file:
            imported_files += 1
            filename = file.filename
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)
            print("File imported: ", imported_files)

    if import_csv:
        csv_path = os.path.join(UPLOAD_FOLDER, import_csv.filename)
        import_csv.save(csv_path)

    processed_folder = os.path.join(PROCESSED_FOLDER, folder_name)
    if not os.path.exists(processed_folder):
        os.makedirs(processed_folder)

    print("Script will start ---")
    result = run_python_script(folder_name, csv_path)

    print("imported_files: " , imported_files)
    print("file_counter: " , file_counter)

    if imported_files != file_counter:
        message = "Some files were not processed correctly. | Number of files not processed: " 
        message += str(imported_files-file_counter)
        message += " | \n"
        return jsonify({'message': message, 'result': bad_files})

    return jsonify({'message': 'Files successfully uploaded and processed.'})


@flask_app.route('/download', methods=['GET'])
def download():
    global folder_name
    if not folder_name:
        return jsonify({'message': 'No folder to download ! Upload a folder to be processed first.'})

    processed_folder = os.path.join(PROCESSED_FOLDER, folder_name)
    if not os.path.exists(processed_folder):
        return jsonify({'message': 'No folder to download ! Upload a folder to be processed first.'})

    zip_path = os.path.join(UPLOAD_FOLDER, f'{folder_name}.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(processed_folder):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), processed_folder))

    return send_file(zip_path, as_attachment=True)

@flask_app.route('/reload', methods=['POST'])
def reload():
    # Reloading folders to be able to upload new folders to be processed
    global folder_name
    global imported_files
    global file_counter
    global bad_files
    try:
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER)
        if os.path.exists(PROCESSED_FOLDER):
            shutil.rmtree(PROCESSED_FOLDER)
            os.makedirs(PROCESSED_FOLDER)
        imported_files = 0
        file_counter = 0
        bad_files = []
        folder_name = None
        return jsonify({'message': 'All files successfully deleted from server.'})
    except Exception as e:
        return jsonify({'message': f'An error occurred: {e}'}), 500


def run_python_script(folder_name, csv_path):
    print("-----Script started----")
    folder_path = os.path.join(UPLOAD_FOLDER, folder_name)
    processed_folder = os.path.join(PROCESSED_FOLDER, folder_name)
    account_bic_file = csv_path
    dict_account_bic = create_account_bic_mapping(account_bic_file)
    accs = process_files_in_folder(folder_path, dict_account_bic, processed_folder)
    return accs

def create_account_bic_mapping(filename):
    print("-----BIC mapping started----")
    global file_counter
    account_bic_dict = {}
    with open(filename, newline='', encoding='ISO-8859-1') as csvfile:
        reader = csv.reader(csvfile, delimiter=';')
        next(reader)  # Skips "MT900 FICSW940.recRCU_01122022_0010.zip;;;;;;;;;;;;;;"
        next(reader)  # Skips "REFERENCES;NOM_CLIENT;ID CLIENT;COMPTE T24;;ADRESSE BIC
        for row in reader:
            if len(row) > 7:  # Ensure there are enough columns
                client_name = row[1]
                account_number = row[3]  # Assuming the account number is in the 4th column
                bic_number = row[5]  # Assuming the BIC number is in the 6th column
                currency = row[4]

                if account_number and bic_number:  # Ensure neither is empty
                    account_bic_dict[account_number] = [client_name, bic_number, currency]
    print("BIC Mapping -- DONE ---")
    return account_bic_dict

def find_account_number(content):
    match = re.search(r':25:(\d+)', content)
    if match:  # if the account number is found then return it
        return match.group(1)
    return None

def find_date(content):
    match = re.search(r':20:(\d{8})', content)
    if match:  # if the date is found then return it
        full_date = match.group(1)
        mmdd = full_date[4:]  # Extract MMDD
        flipped_mmdd = mmdd[2:] + mmdd[:2]  # Flip MMDD to DDMM
        return flipped_mmdd
    return None

def find_and_replace_bic(content, new_bic):
    new_bic_with_prefix = f'I940{new_bic}'
    match = re.search(r'(\{2:)([A-Z0-9]{17})', content)
    if match:
        old_bic = match.group(2)
        modified_content = content.replace(old_bic, new_bic_with_prefix, 1)
        return modified_content
    return content

def process_files_in_folder(folder_path, account_bic_dict, processed_folder):
    print("-----Process started----")
    global file_counter
    global bad_files
    account_numbers = []
    if not os.path.exists(processed_folder):
        os.makedirs(processed_folder)
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            print("-----searching for account----", file_counter)
            account_number = find_account_number(content)
            print("-----account found----", file_counter)
            if account_number and account_number in account_bic_dict:
                
                client_name = account_bic_dict[account_number][0]
                new_bic = account_bic_dict[account_number][1]
                currency = account_bic_dict[account_number][2]
                print("-----searching for BIC----", file_counter)
                modified_content = find_and_replace_bic(content, new_bic)
                print("-----BIC found----", file_counter)
                date = find_date(content)

                array_base_files = {}

                print("-----creating file ----", file_counter)
                print(filename)
                base_file_name = f"{client_name} {currency} {date}"
                array_base_files[base_file_name] = 1
                new_file_name = base_file_name + ".txt"
                new_file_path = os.path.join(processed_folder, new_file_name)
                print("-----new file ----", new_file_name)

                while os.path.exists(new_file_path):
                    print("----- file exists ----", new_file_path)
                    new_file_name = f"{base_file_name} {array_base_files[base_file_name]+1}.txt"
                    new_file_path = os.path.join(processed_folder, new_file_name)
                    array_base_files[base_file_name] += 1
                with open(new_file_path, 'w', encoding='utf-8') as new_file:
                    new_file.write(modified_content)
                    file_counter += 1
            else :
                bad_files.append(filename)

            account_numbers.append(account_number)

    return account_numbers

# Tkinter GUI setup
def open_browser():
    webbrowser.open('http://127.0.0.1:5000')

class TkApp:
    def __init__(self, root):
        self.root = root
        root.title("Flask Desktop App")

        self.label = tk.Label(root, text="Welcome to MT940 App!")
        self.label.pack(pady=10)

        self.button = tk.Button(root, text="Open MT940 App", command=open_browser)
        self.button.pack(pady=10)

        self.quit_button = tk.Button(root, text="Quit", command=root.quit)
        self.quit_button.pack(pady=10)

def run_flask():
    flask_app.run(port=5000, debug=True, use_reloader=False)

if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    root = tk.Tk()
    app = TkApp(root)
    root.mainloop()
