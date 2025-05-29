document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('.letter-range-btn');
    const songList = document.querySelector('.songs-column .song-list');
    const editFormContainer = document.querySelector('.edit-form-container');

    buttons.forEach(button => {
        button.addEventListener('click', async function() {
            buttons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            try {
                const response = await fetch(`/api/songs/${this.dataset.range}`);
                const songs = await response.json();

                songList.innerHTML = `
                    <h3>Songs ${this.dataset.range}</h3>
                    <div class="song-items">
                        ${songs.map(song => `
                            <div class="song-item" data-id="${song.id}">
                                <h4>${song.title}</h4>
                                ${song.composer ? `<p>${song.composer}</p>` : ''}
                            </div>
                        `).join('')}
                    </div>
                `;

                document.querySelectorAll('.song-item').forEach(item => {
                    item.addEventListener('click', async () => {
                        document.querySelectorAll('.song-item').forEach(s => s.classList.remove('active'));
                        item.classList.add('active');

                        const songId = item.dataset.id;
                        const songResponse = await fetch(`/api/song/${songId}`);
                        const songData = await songResponse.json();

                        // Load edit form with song data
                        editFormContainer.innerHTML = `
                            <h3>Edit: ${songData.title}</h3>
                            <form method="POST" enctype="multipart/form-data">
                                <input type="hidden" name="song_id" value="${songData.id}">
                                <div class="mb-3">
                                    <label class="form-label">Title</label>
                                    <input type="text" class="form-control" name="title" value="${songData.title}" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Composer</label>
                                    <input type="text" class="form-control" name="composer" value="${songData.composer || ''}">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Arrangement</label>
                                    <input type="text" class="form-control" name="arrangement" value="${songData.arrangement || ''}">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Key Signature</label>
                                    <input type="text" class="form-control" name="key" value="${songData.key_signature || ''}">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Difficulty</label>
                                    <select class="form-control" name="difficulty">
                                        <option value="">Select difficulty</option>
                                        <option value="Easy" ${songData.difficulty === 'Easy' ? 'selected' : ''}>Easy</option>
                                        <option value="Medium" ${songData.difficulty === 'Medium' ? 'selected' : ''}>Medium</option>
                                        <option value="Hard" ${songData.difficulty === 'Hard' ? 'selected' : ''}>Hard</option>
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Description</label>
                                    <textarea class="form-control" name="description" rows="3">${songData.description || ''}</textarea>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">PDF File</label>
                                    ${songData.pdf_filename ? 
                                        `<p class="text-muted">Current: ${songData.pdf_filename}</p>` : ''}
                                    <input type="file" class="form-control" name="pdf_file" accept=".pdf">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Audio File</label>
                                    ${songData.audio_filename ? 
                                        `<p class="text-muted">Current: ${songData.audio_filename}</p>` : ''}
                                    <input type="file" class="form-control" name="audio_file" accept=".mp3,.wav">
                                </div>
                                <div class="d-grid gap-2 mt-4">
                                    <button type="submit" class="btn btn-primary">Update Song</button>
                                    <button type="button" class="btn btn-danger" onclick="confirmDelete(${songData.id}, '${songData.title}')">Delete Song</button>
                                    <a href="{{ url_for('home') }}" class="btn btn-secondary">Cancel</a>
                                </div>
                            </form>
                        `;
                    });
                });

            } catch (error) {
                console.error('Error:', error);
                songList.innerHTML = '<p class="text-danger">Error loading songs</p>';
            }
        });
    });
});

async function confirmDelete(songId, songTitle) {
    if (confirm(`Are you SURE you want to delete the song "${songTitle}"?`)) {
        try {
            const response = await fetch(`/api/song/${songId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                alert('Song deleted successfully');
                window.location.href = '/'; // Redirect to home page
            } else {
                throw new Error('Failed to delete song');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error deleting song');
        }
    }
}