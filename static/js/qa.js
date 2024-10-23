// Import shared socket instance
import socket from './socket-client.js';

function initializeQA() {
    const questionsContainer = document.getElementById('questions-container');
    const questionForm = document.getElementById('question-form');
    const streamContainer = document.getElementById('stream-container');
    
    if (!streamContainer) return;
    
    const roomId = streamContainer.dataset.roomId;

    // Question filtering
    const filterButtons = document.createElement('div');
    filterButtons.className = 'btn-group mb-3';
    filterButtons.innerHTML = `
        <button class="btn btn-outline-primary active" data-filter="all">All</button>
        <button class="btn btn-outline-primary" data-filter="answered">Answered</button>
        <button class="btn btn-outline-primary" data-filter="unanswered">Unanswered</button>
    `;
    questionsContainer.parentNode.insertBefore(filterButtons, questionsContainer);

    filterButtons.addEventListener('click', e => {
        if (e.target.matches('button')) {
            // Update active state
            filterButtons.querySelectorAll('button').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');

            // Filter questions
            const filter = e.target.dataset.filter;
            document.querySelectorAll('.question-item').forEach(item => {
                if (filter === 'all' || 
                    (filter === 'answered' && item.classList.contains('answered')) ||
                    (filter === 'unanswered' && !item.classList.contains('answered'))) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        }
    });

    // Submit question
    if (questionForm) {
        questionForm.addEventListener('submit', e => {
            e.preventDefault();
            const input = questionForm.querySelector('input');
            const question = input.value.trim();
            
            if (question) {
                socket.emit('submit_question', {
                    question: question,
                    room: roomId
                });
                input.value = '';
            }
        });
    }

    // Handle new question
    socket.on('new_question', data => {
        const questionDiv = document.createElement('div');
        questionDiv.className = 'question-item mb-3 p-3 border rounded';
        questionDiv.dataset.questionId = data.id;
        
        questionDiv.innerHTML = `
            <div class="d-flex justify-content-between">
                <div>
                    <strong>${data.username}</strong>
                    <small class="text-muted ms-2">${data.time}</small>
                </div>
                <div class="question-votes">
                    <button class="btn btn-sm btn-outline-primary vote-btn" data-question-id="${data.id}">
                        <i class="bi bi-arrow-up"></i> <span class="vote-count">0</span>
                    </button>
                </div>
            </div>
            <p class="mb-1 mt-2">${data.question}</p>
            ${data.is_seller ? `
                <div class="answer-form mt-2">
                    <form class="answer-question-form" data-question-id="${data.id}">
                        <div class="input-group">
                            <input type="text" class="form-control" placeholder="Type your answer...">
                            <button class="btn btn-primary" type="submit">Answer</button>
                        </div>
                    </form>
                </div>
            ` : ''}
        `;
        
        questionsContainer.appendChild(questionDiv);
        setupQuestionInteractions(questionDiv);
    });

    // Setup interactions for existing questions
    document.querySelectorAll('.question-item').forEach(setupQuestionInteractions);

    function setupQuestionInteractions(questionElement) {
        // Vote button
        const voteBtn = questionElement.querySelector('.vote-btn');
        if (voteBtn) {
            voteBtn.addEventListener('click', () => {
                const questionId = voteBtn.dataset.questionId;
                socket.emit('vote_question', {
                    question_id: questionId,
                    room: roomId
                });
            });
        }

        // Answer form
        const answerForm = questionElement.querySelector('.answer-question-form');
        if (answerForm) {
            answerForm.addEventListener('submit', e => {
                e.preventDefault();
                const input = answerForm.querySelector('input');
                const answer = input.value.trim();
                
                if (answer) {
                    socket.emit('submit_answer', {
                        question_id: answerForm.dataset.questionId,
                        answer: answer,
                        room: roomId
                    });
                    input.value = '';
                }
            });
        }
    }

    // Handle question voted
    socket.on('question_voted', data => {
        const questionDiv = document.querySelector(`.question-item[data-question-id="${data.question_id}"]`);
        if (questionDiv) {
            const voteCount = questionDiv.querySelector('.vote-count');
            voteCount.textContent = data.votes;
        }
    });

    // Handle question answered
    socket.on('question_answered', data => {
        const questionDiv = document.querySelector(`.question-item[data-question-id="${data.question_id}"]`);
        if (questionDiv) {
            questionDiv.classList.add('answered');
            const answerForm = questionDiv.querySelector('.answer-form');
            if (answerForm) {
                answerForm.innerHTML = `
                    <div class="answer mt-2 p-2 bg-secondary bg-opacity-10 rounded">
                        <small class="text-muted">Answer:</small>
                        <p class="mb-0">${data.answer}</p>
                    </div>
                `;
            }
        }
    });
}

// Initialize Q&A when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeQA);

export default initializeQA;
