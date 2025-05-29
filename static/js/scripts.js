document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('.letter-range-btn');
    const songList = document.querySelector('.songs-column .song-list');  // Updated selector
    const songDisplay = document.querySelector('.details-column .song-display');  // Updated selector

    buttons.forEach(button => {
        button.addEventListener('click', async function() {
            // Remove active class from all buttons
            buttons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');

            try {
                const response = await fetch(`/api/songs/${this.dataset.range}`);
                const songs = await response.json();

                // Clear the entire song list (including initial message)
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

                // Add click handlers to the song items
                document.querySelectorAll('.song-item').forEach(item => {
                    item.addEventListener('click', async () => {
                        // Remove active class from all songs
                        document.querySelectorAll('.song-item').forEach(s => s.classList.remove('active'));
                        // Add active class to clicked song
                        item.classList.add('active');

                        const songId = item.dataset.id;
                        const songResponse = await fetch(`/api/song/${songId}`);
                        const songData = await songResponse.json();

                        // Update the right column with song details
                        songDisplay.innerHTML = `
                            <h3>${songData.title}</h3>
                            <div class="song-info">
                                <p><strong>Composer:</strong> ${songData.composer || 'Not specified'}</p>
                                <p><strong>Arrangement:</strong> ${songData.arrangement || 'Not specified'}</p>
                                <p><strong>Key:</strong> ${songData.key_signature || 'Not specified'}</p>
                                <p><strong>Difficulty:</strong> ${songData.difficulty || 'Not specified'}</p>
                                <p><strong>Description:</strong> ${songData.description || 'No description available'}</p>
                                ${songData.pdf_filename ? 
                                    `<div class="mt-4">
                                        <a href="/static/uploads/pdfs/${songData.pdf_filename}" 
                                           target="_blank" 
                                           class="btn btn-primary btn-lg w-100">
                                            <i class="fas fa-file-pdf"></i> View Sheet Music (PDF)
                                        </a>
                                    </div>` : ''}
                                ${songData.audio_filename ? 
                                    `<div class="mt-4">
                                        <h4>Audio Sample</h4>
                                        <audio controls class="w-100">
                                            <source src="/static/uploads/audio/${songData.audio_filename}" type="audio/mpeg">
                                            Your browser does not support the audio element.
                                        </audio>
                                    </div>` : ''}
                            </div>
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

