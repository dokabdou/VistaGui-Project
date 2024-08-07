document.getElementById('uploadForm').addEventListener('submit', function(event) {
    event.preventDefault(); // Prevent the default form submission
    const formData = new FormData(document.getElementById('uploadForm'));

    fetch('/sort', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('message').innerText = data.message;
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('message').innerText = 'An error occurred during the upload.';
    });
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