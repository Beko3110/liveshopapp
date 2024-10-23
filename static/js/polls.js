// Import shared socket instance and ROOM_ID
import socket, { ROOM_ID } from './socket-client.js';

function initializePolls() {
    const pollsContainer = document.getElementById('polls-container');
    const createPollForm = document.getElementById('create-poll-form');
    const streamContainer = document.getElementById('stream-container');
    
    if (!pollsContainer || !streamContainer) return;

    // Add error message display area
    const errorDisplay = document.createElement('div');
    errorDisplay.className = 'alert alert-danger d-none';
    errorDisplay.id = 'polls-error';
    pollsContainer.prepend(errorDisplay);

    function showError(message, duration = 5000) {
        console.error('Poll error:', message);
        errorDisplay.textContent = message;
        errorDisplay.classList.remove('d-none');
        setTimeout(() => errorDisplay.classList.add('d-none'), duration);
    }

    function setLoading(element, isLoading) {
        if (isLoading) {
            element.disabled = true;
            element.dataset.originalText = element.innerHTML;
            element.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
        } else {
            element.disabled = false;
            element.innerHTML = element.dataset.originalText;
        }
    }

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
        
        // Submit new poll with error handling
        createPollForm.addEventListener('submit', async e => {
            e.preventDefault();
            const submitBtn = createPollForm.querySelector('button[type="submit"]');
            setLoading(submitBtn, true);

            try {
                const question = document.getElementById('pollQuestion').value.trim();
                const options = Array.from(pollOptions.querySelectorAll('input'))
                                    .map(input => input.value.trim())
                                    .filter(val => val);
                
                if (!question) {
                    throw new Error('Please enter a poll question');
                }
                if (options.length < 2) {
                    throw new Error('Please add at least two options');
                }

                // Use Promise to handle socket emission with timeout
                await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        reject(new Error('Poll creation timed out'));
                    }, 5000);

                    socket.emit('create_poll', {
                        question: question,
                        options: options,
                        room: ROOM_ID
                    }, (response) => {
                        clearTimeout(timeout);
                        if (response?.error) {
                            reject(new Error(response.error));
                        } else {
                            resolve();
                        }
                    });
                });

                createPollForm.reset();
            } catch (error) {
                showError(error.message);
            } finally {
                setLoading(submitBtn, false);
            }
        });
    }
    
    // Handle poll voting with error handling and loading states
    pollsContainer.addEventListener('click', async e => {
        const voteBtn = e.target.closest('.vote-option-btn');
        if (voteBtn && !voteBtn.disabled) {
            try {
                setLoading(voteBtn, true);
                const pollId = voteBtn.dataset.pollId;
                const option = voteBtn.dataset.option;

                await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        reject(new Error('Vote submission timed out'));
                    }, 5000);

                    socket.emit('vote_poll', {
                        poll_id: pollId,
                        option: option,
                        room: ROOM_ID
                    }, (response) => {
                        clearTimeout(timeout);
                        if (response?.error) {
                            reject(new Error(response.error));
                        } else {
                            resolve();
                        }
                    });
                });
            } catch (error) {
                showError(error.message);
            } finally {
                setLoading(voteBtn, false);
            }
        }
        
        const closeBtn = e.target.closest('.close-poll-btn');
        if (closeBtn && !closeBtn.disabled) {
            try {
                setLoading(closeBtn, true);
                const pollId = closeBtn.dataset.pollId;

                await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        reject(new Error('Failed to close poll'));
                    }, 5000);

                    socket.emit('close_poll', {
                        poll_id: pollId,
                        room: ROOM_ID
                    }, (response) => {
                        clearTimeout(timeout);
                        if (response?.error) {
                            reject(new Error(response.error));
                        } else {
                            resolve();
                        }
                    });
                });
            } catch (error) {
                showError(error.message);
            } finally {
                setLoading(closeBtn, false);
            }
        }
    });
    
    // Socket event handlers with error handling
    socket.on('new_poll', data => {
        try {
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
        } catch (error) {
            console.error('Error creating new poll:', error);
            showError('Failed to display new poll');
        }
    });
    
    // Handle poll updates with race condition prevention
    let lastUpdateTimestamp = {};
    socket.on('poll_updated', data => {
        try {
            // Prevent race conditions by checking timestamp
            if (lastUpdateTimestamp[data.poll_id] && data.timestamp < lastUpdateTimestamp[data.poll_id]) {
                console.log('Skipping outdated poll update');
                return;
            }
            lastUpdateTimestamp[data.poll_id] = data.timestamp;

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
        } catch (error) {
            console.error('Error updating poll:', error);
            showError('Failed to update poll results');
        }
    });
    
    // Handle poll closed
    socket.on('poll_closed', data => {
        try {
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
        } catch (error) {
            console.error('Error closing poll:', error);
            showError('Failed to close poll');
        }
    });
}

// Initialize polls when DOM is loaded
document.addEventListener('DOMContentLoaded', initializePolls);

export default initializePolls;
