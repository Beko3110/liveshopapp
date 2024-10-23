// Import shared socket instance
import socket from './socket-client.js';

function initializePolls() {
    const pollsContainer = document.getElementById('polls-container');
    const createPollForm = document.getElementById('create-poll-form');
    const streamContainer = document.getElementById('stream-container');
    
    if (!pollsContainer || !streamContainer) return;
    
    const roomId = streamContainer.dataset.roomId;

    if (createPollForm) {
        const addOptionBtn = document.getElementById('add-option');
        const pollOptions = document.getElementById('poll-options');
        
        // Add new option field
        addOptionBtn.addEventListener('click', () => {
            const optionDiv = document.createElement('div');
            optionDiv.className = 'input-group mb-2';
            optionDiv.innerHTML = `
                <input type="text" class="form-control" placeholder="Option ${pollOptions.children.length + 1}">
                <button type="button" class="btn btn-outline-danger remove-option">
                    <i class="bi bi-trash"></i>
                </button>
            `;
            pollOptions.appendChild(optionDiv);
        });
        
        // Remove option
        pollOptions.addEventListener('click', e => {
            if (e.target.closest('.remove-option') && pollOptions.children.length > 2) {
                e.target.closest('.input-group').remove();
            }
        });
        
        // Submit new poll
        createPollForm.addEventListener('submit', e => {
            e.preventDefault();
            const question = document.getElementById('pollQuestion').value.trim();
            const options = Array.from(pollOptions.querySelectorAll('input'))
                                .map(input => input.value.trim())
                                .filter(val => val);
            
            if (question && options.length >= 2) {
                socket.emit('create_poll', {
                    question: question,
                    options: options,
                    room: roomId
                });
                createPollForm.reset();
            }
        });
    }
    
    // Handle poll voting
    pollsContainer.addEventListener('click', e => {
        const voteBtn = e.target.closest('.vote-option-btn');
        if (voteBtn) {
            const pollId = voteBtn.dataset.pollId;
            const option = voteBtn.dataset.option;
            socket.emit('vote_poll', {
                poll_id: pollId,
                option: option,
                room: roomId
            });
        }
        
        const closeBtn = e.target.closest('.close-poll-btn');
        if (closeBtn) {
            const pollId = closeBtn.dataset.pollId;
            socket.emit('close_poll', {
                poll_id: pollId,
                room: roomId
            });
        }
    });
    
    // Handle new poll
    socket.on('new_poll', data => {
        const pollDiv = document.createElement('div');
        pollDiv.className = 'poll-item mb-4 p-3 border rounded';
        pollDiv.dataset.pollId = data.id;
        
        let optionsHtml = '';
        data.options.forEach(option => {
            optionsHtml += `
                <div class="poll-option mb-2">
                    <div class="d-flex align-items-center">
                        <button class="btn btn-outline-primary vote-option-btn" 
                                data-poll-id="${data.id}" 
                                data-option="${option}">
                            ${option}
                        </button>
                        <div class="progress ms-2 flex-grow-1">
                            <div class="progress-bar" role="progressbar" 
                                 style="width: 0%" 
                                 aria-valuenow="0" 
                                 aria-valuemin="0" 
                                 aria-valuemax="100">
                                0 votes (0%)
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        pollDiv.innerHTML = `
            <h5>${data.question}</h5>
            <div class="poll-options">
                ${optionsHtml}
            </div>
            ${data.is_seller ? `
                <button class="btn btn-danger btn-sm mt-2 close-poll-btn" data-poll-id="${data.id}">
                    Close Poll
                </button>
            ` : ''}
        `;
        
        const activePolls = document.getElementById('active-polls');
        activePolls.appendChild(pollDiv);
    });
    
    // Handle poll updates
    socket.on('poll_updated', data => {
        const pollDiv = document.querySelector(`.poll-item[data-poll-id="${data.poll_id}"]`);
        if (pollDiv) {
            const options = pollDiv.querySelectorAll('.poll-option');
            options.forEach(option => {
                const btn = option.querySelector('.vote-option-btn');
                const progressBar = option.querySelector('.progress-bar');
                const optionText = btn.dataset.option;
                const votes = data.votes[optionText] || 0;
                const percentage = data.total_votes > 0 ? (votes / data.total_votes * 100) : 0;
                
                progressBar.style.width = `${percentage}%`;
                progressBar.setAttribute('aria-valuenow', percentage);
                progressBar.textContent = `${votes} votes (${percentage.toFixed(1)}%)`;
            });
        }
    });
    
    // Handle poll closed
    socket.on('poll_closed', data => {
        const pollDiv = document.querySelector(`.poll-item[data-poll-id="${data.poll_id}"]`);
        if (pollDiv) {
            pollDiv.classList.add('closed');
            const closeBtn = pollDiv.querySelector('.close-poll-btn');
            if (closeBtn) {
                closeBtn.remove();
            }
            const voteButtons = pollDiv.querySelectorAll('.vote-option-btn');
            voteButtons.forEach(btn => btn.disabled = true);
        }
    });
}

// Initialize polls when DOM is loaded
document.addEventListener('DOMContentLoaded', initializePolls);

export default initializePolls;
