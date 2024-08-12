import os
import shutil
import re
import datetime
import flask
from flask import Flask, request, render_template, jsonify, send_file
import zipfile
from threading import Thread
import tkinter as tk
from tkinter import messagebox
import webbrowser
import sys

# Flask application setup
app = Flask(__name__)

def get_current_directory():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.abspath(__file__))


UPLOAD_FOLDER = os.path.join(get_current_directory(), 'uploads')
SORTED_FOLDER = os.path.join(get_current_directory(), 'sorted')
NO_CURRENCY = os.path.join(get_current_directory(), 'noCurrency')

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SORTED_FOLDER, exist_ok=True)
os.makedirs(NO_CURRENCY, exist_ok=True)

folder_name = None


def date_range(name):
    print("Date range")
    pos = name.find('940')
    if pos == -1:
        return None
    search_str = name[pos + len('940'):]
    match = re.search(r'(\d{2})\s(\d{2})', search_str)
    if match:
        day = match.group(1)
        month = match.group(2)
        return f'{day}{month}'
    return None


def sort_files_by_prefix(source_folder, destination_folder, no_currency_folder):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if 'txt' in file:
                parts = file.split(' ')
                prefix = []
                found_currency = False
                for part in parts:
                    if part in ["GNF", "USD", "EUR"]:
                        found_currency = True
                    if found_currency:
                        break
                    prefix.append(part)
                folder_name = ' '.join(prefix).replace('txt', '').strip()
                if found_currency:
                    new_folder = os.path.join(destination_folder, folder_name)
                    if not os.path.exists(new_folder):
                        os.makedirs(new_folder)
                else:
                    new_folder = no_currency_folder
                source_file = os.path.join(root, file)
                destination_file = os.path.join(new_folder, file)
                shutil.copy2(source_file, destination_file)


def sort_no_currency(no_currency_folder, destination_folder):
    for filename in os.listdir(no_currency_folder):
        file_path = os.path.join(no_currency_folder, filename)
        if os.path.isfile(file_path):
            match = re.match(r'^(.*?)(\d+)', filename)
            if match:
                prefix = match.group(1).strip()
                prefix_folder = os.path.join(no_currency_folder, prefix + '_')
                if not os.path.exists(prefix_folder):
                    os.makedirs(prefix_folder)
                destination_path = os.path.join(prefix_folder, filename)
                shutil.move(file_path, destination_path)
    for folder_name in os.listdir(no_currency_folder):
        folder_path = os.path.join(no_currency_folder, folder_name)
        if os.path.isdir(folder_path):
            new_location = os.path.join(destination_folder, folder_name)
            if not os.path.exists(new_location):
                shutil.move(folder_path, new_location)


def sort_files_by_currency(base_folder):
    for root, dirs, files in os.walk(base_folder):
        for file in files:
            match = re.search(r'\b(GNF|USD|EUR)\b', file)
            if match:
                currency = match.group(1)
                currency_folder = os.path.join(root, currency)
                if not os.path.exists(currency_folder):
                    os.makedirs(currency_folder)
                source_file = os.path.join(root, file)
                destination_file = os.path.join(currency_folder, file)
                shutil.move(source_file, destination_file)


def rename_sorted_folder_by_dates(sorted_folder):
    print("----rename_sorted_folder_by_dates----")
    global folder_name
    print("folder_name: ", folder_name)
    dates = []
    for root, dirs, files in os.walk(sorted_folder):
        for dir_name in dirs:
            print("dir_name: ", dir_name)
            date_str = date_range(dir_name)
            print("date_str:", date_str)
            if date_str:
                try:
                    date_obj = datetime.datetime.strptime(date_str, '%d%m')
                    dates.append(date_obj)
                except ValueError:
                    continue
    if dates:
        print("date of MT940's")
        oldest_date = min(dates)
        most_recent_date = max(dates)
        oldest_date_str = oldest_date.strftime('%d%m')
        most_recent_date_str = most_recent_date.strftime('%d%m')
        new_folder_name = f'MT940_{oldest_date_str}_{most_recent_date_str}'
        new_sorted_folder = os.path.join(os.path.dirname(sorted_folder), new_folder_name)
        folder_name = new_folder_name
        if not os.path.exists(new_sorted_folder):
            os.rename(sorted_folder, new_sorted_folder)
            print("new folder_name: ", new_sorted_folder)
            return new_sorted_folder
        else:
            print("folder_name: ", sorted_folder)
            return sorted_folder
    else:
        print("--didnt enter---")
    print(sorted_folder)
    return sorted_folder


def get_first_folder(upload_folder):
    print("----get_first_folder----")
    all_folders = [
        d for d in os.listdir(upload_folder)
        if os.path.isdir(os.path.join(upload_folder, d))
    ]
    if all_folders:
        print("-folder name-", all_folders[0])
        return os.path.join(upload_folder, all_folders[0])
    else:
        raise FileNotFoundError('No directories found in the upload folder.')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download', methods=['GET'])
def download():
    global folder_name
    if not folder_name:
        return jsonify({
            'message':
            'Pas de dossier à télécharger ! Importez le dossier à trier. Pas de nom de dossier'
        })

    sorted_folder_path = os.path.join(SORTED_FOLDER)
    print(f"Sorted folder path: {sorted_folder_path}")

    if not os.path.exists(sorted_folder_path):
        return jsonify({
            'message':
            'Pas de dossier à télécharger ! Importez le dossier à trier. Pas de dossier trié'
        })

    zip_path = os.path.join(SORTED_FOLDER, f'{folder_name}.zip')
    print(f"Zip path: {zip_path}")

    # Check if zip file already exists and delete it if necessary
    if os.path.exists(zip_path):
        os.remove(zip_path)

    # Create the zip file
    print(f"Creating zip file at: {zip_path}")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        print("Adding files to zip file")
        for root, dirs, files in os.walk(sorted_folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=sorted_folder_path)
                zipf.write(file_path, arcname=arcname)

    # Check if zip file was created successfully
    if not os.path.exists(zip_path):
        return jsonify({'message': 'La création du zip à échoué'}), 500

    return send_file(zip_path, as_attachment=True)


@app.route('/reload', methods=['POST'])
def reload():
    try:
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER)
        if os.path.exists(SORTED_FOLDER):
            shutil.rmtree(SORTED_FOLDER)
            os.makedirs(SORTED_FOLDER)
        if os.path.exists(NO_CURRENCY):
            shutil.rmtree(NO_CURRENCY)
            os.makedirs(NO_CURRENCY)
        return jsonify({'message': "Tous les fichiers sont supprimés de l'application!"})
    except Exception as e:
        return jsonify({'message': f'An error occurred: {e}'}), 500


@app.route('/sort', methods=['POST'])
def sort():
    print("----SORTING-----")
    if 'folderUpload' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    files = request.files.getlist('folderUpload')
    for file in files:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)

    sort_files_by_prefix(UPLOAD_FOLDER, SORTED_FOLDER, NO_CURRENCY)
    sort_no_currency(NO_CURRENCY, SORTED_FOLDER)
    sort_files_by_currency(SORTED_FOLDER)

    sample_dir = get_first_folder(UPLOAD_FOLDER)
    sorted_folder_with_dates = rename_sorted_folder_by_dates(sample_dir)

    return jsonify({
        'message':
        f'Les fichiers triés, et ont été déplacés dans le dossier {os.path.basename(sorted_folder_with_dates)}!'
    })


# Tkinter GUI setup
def open_browser():
    webbrowser.open('http://127.0.0.1:5000')


class App:

    def __init__(self, root):
        self.root = root
        root.title("Flask Desktop App")

        self.label = tk.Label(root, text="Bienvenue à l'application de tri de dossiers MT940 !")
        self.label.pack(pady=10)

        self.button = tk.Button(root,
                                text="Ouvrir Tri Dossiers MT940",
                                command=open_browser)
        self.button.pack(pady=10)

        self.quit_button = tk.Button(root, text="Quitter", command=root.quit)
        self.quit_button.pack(pady=10)


def run_flask():
    app.run(port=5000, debug=True, use_reloader=False)


if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    root = tk.Tk()
    app = App(root)
    root.mainloop()
