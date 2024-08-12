document.getElementById('importCsv').addEventListener('change', function() {
    const label = document.querySelector('label[for="importCsv"]');
    const fileName = this.files[0] ? this.files[0].name : 'Choose CSV File';
    label.textContent = fileName;
});

document.getElementById('fileInput').addEventListener('change', function() {
    const label = document.querySelector('label[for="fileInput"]');
    const folderName = this.files[0] ? this.files[0].webkitRelativePath.split('/')[0] : 'Choose Folder';
    label.textContent = folderName;
});

document.getElementById('uploadForm').addEventListener('submit', function(event) {
    event.preventDefault();

    const formData = new FormData();
    const importCsv = document.getElementById('importCsv').files[0];
    const files = document.getElementById('fileInput').files;

    if (importCsv) {
        formData.append('importCsv', importCsv);
    }

    for (const file of files) {
        formData.append('files[]', file);
    }

    const folderName = files.length > 0 ? files[0].webkitRelativePath.split('/')[0] : '';

    formData.append('folderName', folderName);

    fetch('/upload', {
        method: 'POST',
        body: formData
    }).then(response => response.json())
    .then(data => {
        let message = data.message;
        if (data.result !== undefined) {
            message += ' | These are the files : ' + data.result;
        }
        document.getElementById('message').textContent = message;
    }).catch(error => console.error('Error:', error));
});

document.getElementById('downloadButton').onclick = function () {
    fetch('/download', {
        method: 'GET'
    }).then(response => response.blob())
    .then(blob => {
        if (blob.type === 'application/json') {
            blob.text().then(text => {
            const data = JSON.parse(text);
            document.getElementById('message').textContent = data.message;
            });
        } else {
            window.location.href = '/download';
            setTimeout(() => {
                fetch('/reload', {
                    method: 'POST'
                }).then(response => response.json())
                .then(data => {
                    document.getElementById('message').textContent = data.message;
                }).catch(error => console.error('Error:', error));
            }, 5000);
        }
    }).catch(error => console.error('Error:', error));
};

document.getElementById('reloadButton').addEventListener('click', function() {
    fetch('/reload', {
        method: 'POST'
    }).then(response => response.json())
    .then(data => {
        document.getElementById('message').textContent = data.message;
    }).catch(error => console.error('Error:', error));
});