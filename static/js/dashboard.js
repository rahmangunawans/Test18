// Dashboard JavaScript for AniFlix
document.addEventListener('DOMContentLoaded', function() {
    initializeSearchAndFilter();
    initializeModals();
    initializeTooltips();
    initializeProgressIndicators();
    initializeQuickActions();
    initializeEditButtons();
});

// Search and Filter functionality
function initializeSearchAndFilter() {
    const searchInput = document.getElementById('anime-search');
    const genreFilter = document.getElementById('genre-filter');
    const statusFilter = document.getElementById('status-filter');
    const sortFilter = document.getElementById('sort-filter');
    const clearFilters = document.getElementById('clear-filters');

    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performDashboardSearch();
            }, 300);
        });
    }

    if (genreFilter) {
        genreFilter.addEventListener('change', performDashboardSearch);
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', performDashboardSearch);
    }

    if (sortFilter) {
        sortFilter.addEventListener('change', performDashboardSearch);
    }

    if (clearFilters) {
        clearFilters.addEventListener('click', function() {
            if (searchInput) searchInput.value = '';
            if (genreFilter) genreFilter.value = '';
            if (statusFilter) statusFilter.value = '';
            if (sortFilter) sortFilter.value = 'recent';
            performDashboardSearch();
        });
    }
}

function performDashboardSearch() {
    const searchQuery = document.getElementById('anime-search')?.value || '';
    const genre = document.getElementById('genre-filter')?.value || '';
    const status = document.getElementById('status-filter')?.value || '';
    const sort = document.getElementById('sort-filter')?.value || 'recent';

    const params = new URLSearchParams({
        search: searchQuery,
        genre: genre,
        status: status,
        sort: sort
    });

    // Show loading state
    const resultsContainer = document.getElementById('search-results');
    if (resultsContainer) {
        resultsContainer.innerHTML = '<div class="text-center py-8"><div class="animate-spin rounded-full h-12 w-12 border-b-2 border-red-500 mx-auto"></div><p class="text-gray-400 mt-4">Searching...</p></div>';
    }

    fetch(`/dashboard/search?${params}`)
        .then(response => response.json())
        .then(data => {
            displaySearchResults(data);
        })
        .catch(error => {
            console.error('Search error:', error);
            if (resultsContainer) {
                resultsContainer.innerHTML = '<div class="text-center py-8 text-red-400">Search failed. Please try again.</div>';
            }
        });
}

function displaySearchResults(data) {
    const resultsContainer = document.getElementById('search-results');
    if (!resultsContainer) return;

    if (data.results && data.results.length > 0) {
        resultsContainer.innerHTML = data.results.map(item => `
            <div class="bg-gray-800 rounded-lg overflow-hidden hover:transform hover:scale-105 transition-all duration-200 group">
                <div class="relative">
                    <img src="${item.thumbnail_url || '/static/images/placeholder.jpg'}" 
                         alt="${item.title}" 
                         class="w-full h-48 object-cover">
                    <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-opacity duration-200"></div>
                    <div class="absolute top-2 right-2">
                        ${item.progress ? `
                        <div class="bg-black bg-opacity-75 rounded-full px-2 py-1">
                            <span class="text-white text-xs">${Math.round(item.progress)}%</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
                <div class="p-4">
                    <h3 class="text-white font-semibold truncate">${item.title}</h3>
                    <p class="text-gray-400 text-sm">${item.genre || 'Unknown Genre'}</p>
                    <p class="text-gray-500 text-xs">${item.year || ''}</p>
                    ${item.progress ? `
                    <div class="mt-3">
                        <div class="flex justify-between text-xs text-gray-400 mb-1">
                            <span>Episode ${item.current_episode}</span>
                            <span>${Math.round(item.progress)}%</span>
                        </div>
                        <div class="w-full bg-gray-700 rounded-full h-2">
                            <div class="bg-red-500 h-2 rounded-full transition-all duration-300" style="width: ${item.progress}%"></div>
                        </div>
                    </div>
                    ` : ''}
                    <div class="mt-4 flex justify-between items-center">
                        <a href="/anime/${item.id}" class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm transition-colors">
                            ${item.progress ? 'Continue' : 'Watch'}
                        </a>
                        <div class="flex space-x-2">
                            <button class="text-gray-400 hover:text-white transition-colors" onclick="toggleWatchlist(${item.id})">
                                <i class="fas fa-bookmark"></i>
                            </button>
                            <button class="text-gray-400 hover:text-white transition-colors" onclick="shareAnime(${item.id})">
                                <i class="fas fa-share"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    } else {
        resultsContainer.innerHTML = `
            <div class="col-span-full text-center py-12">
                <i class="fas fa-search text-gray-500 text-6xl mb-4"></i>
                <h3 class="text-xl font-semibold text-gray-400 mb-2">No results found</h3>
                <p class="text-gray-500">Try adjusting your search criteria</p>
            </div>
        `;
    }
}

// Modal functionality for confirmations
function initializeModals() {
    // Confirmation modal
    window.showConfirmModal = function(title, message, onConfirm, onCancel) {
        const modal = document.getElementById('confirm-modal');
        const titleEl = document.getElementById('confirm-title');
        const messageEl = document.getElementById('confirm-message');
        const confirmBtn = document.getElementById('confirm-btn');
        const cancelBtn = document.getElementById('cancel-btn');

        if (modal && titleEl && messageEl && confirmBtn && cancelBtn) {
            titleEl.textContent = title;
            messageEl.textContent = message;
            
            confirmBtn.onclick = function() {
                modal.classList.add('hidden');
                if (onConfirm) onConfirm();
            };
            
            cancelBtn.onclick = function() {
                modal.classList.add('hidden');
                if (onCancel) onCancel();
            };
            
            modal.classList.remove('hidden');
        }
    };

    // Close modal on backdrop click
    const modal = document.getElementById('confirm-modal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    }
}

// Admin tooltips
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        const tooltip = document.createElement('div');
        tooltip.className = 'absolute z-50 px-3 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg shadow-sm opacity-0 tooltip invisible';
        tooltip.textContent = element.getAttribute('data-tooltip');
        
        element.appendChild(tooltip);
        
        element.addEventListener('mouseenter', function() {
            tooltip.classList.remove('invisible', 'opacity-0');
            tooltip.classList.add('opacity-100');
        });
        
        element.addEventListener('mouseleave', function() {
            tooltip.classList.add('invisible', 'opacity-0');
            tooltip.classList.remove('opacity-100');
        });
    });
}

// Progress indicators
function initializeProgressIndicators() {
    const progressBars = document.querySelectorAll('.progress-bar');
    
    progressBars.forEach(bar => {
        const progress = bar.getAttribute('data-progress');
        const fill = bar.querySelector('.progress-fill');
        
        if (fill && progress) {
            setTimeout(() => {
                fill.style.width = progress + '%';
            }, 100);
        }
    });
}

// Quick actions
function initializeQuickActions() {
    // Quick search
    window.quickSearch = function(query) {
        const searchInput = document.getElementById('anime-search');
        if (searchInput) {
            searchInput.value = query;
            performDashboardSearch();
        }
    };

    // Quick filter
    window.quickFilter = function(type, value) {
        const filterElement = document.getElementById(type + '-filter');
        if (filterElement) {
            filterElement.value = value;
            performDashboardSearch();
        }
    };
}

// Utility functions
function toggleWatchlist(animeId) {
    fetch(`/api/watchlist/toggle/${animeId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message, data.success ? 'success' : 'error');
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Failed to update watchlist', 'error');
    });
}

function shareAnime(animeId) {
    const url = `${window.location.origin}/anime/${animeId}`;
    
    if (navigator.share) {
        navigator.share({
            title: 'Check out this anime on AniFlix',
            url: url
        });
    } else {
        navigator.clipboard.writeText(url).then(() => {
            showNotification('Link copied to clipboard!', 'success');
        });
    }
}

// Edit watch history modal functions
function showEditModal(episodeId, episodeTitle, contentId) {
    // Create modal HTML
    const modalHTML = `
        <div id="editModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-bold text-white">Edit Watch Progress</h3>
                    <button onclick="closeEditModal()" class="text-gray-400 hover:text-white">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="mb-4">
                    <p class="text-gray-300 text-sm mb-2">Episode: ${episodeTitle}</p>
                    <label class="block text-white text-sm font-medium mb-2">
                        Mark as:
                    </label>
                    <div class="space-y-2">
                        <button onclick="updateWatchStatus(${episodeId}, 'completed')" 
                                class="w-full bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors">
                            <i class="fas fa-check-circle mr-2"></i>Mark as Completed
                        </button>
                        <button onclick="updateWatchStatus(${episodeId}, 'ongoing')" 
                                class="w-full bg-yellow-600 text-white px-4 py-2 rounded hover:bg-yellow-700 transition-colors">
                            <i class="fas fa-clock mr-2"></i>Mark as Ongoing
                        </button>
                        <button onclick="removeFromHistory(${episodeId})" 
                                class="w-full bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors">
                            <i class="fas fa-trash mr-2"></i>Remove from History
                        </button>
                    </div>
                </div>
                <div class="flex justify-end space-x-2 mt-6">
                    <button onclick="closeEditModal()" 
                            class="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 transition-colors">
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeEditModal() {
    const modal = document.getElementById('editModal');
    if (modal) {
        modal.remove();
    }
}

function updateWatchStatus(episodeId, status) {
    fetch('/api/watch-history/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            episode_id: episodeId,
            status: status
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Watch status updated successfully!', 'success');
            closeEditModal();
            // Refresh the page to show updated status
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showNotification(data.message || 'Failed to update watch status', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Failed to update watch status', 'error');
    });
}

function removeFromHistory(episodeId) {
    if (confirm('Are you sure you want to remove this from your watch history?')) {
        fetch('/api/watch-history/remove', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                episode_id: episodeId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Removed from watch history!', 'success');
                closeEditModal();
                // Refresh the page to show updated history
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification(data.message || 'Failed to remove from history', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Failed to remove from history', 'error');
        });
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    
    // Match the professional styling from app.js
    const bgColor = {
        'success': 'bg-gradient-to-r from-green-500 to-green-600',
        'error': 'bg-gradient-to-r from-red-500 to-red-600',
        'warning': 'bg-gradient-to-r from-yellow-500 to-yellow-600',
        'info': 'bg-gradient-to-r from-blue-500 to-blue-600'
    }[type] || 'bg-gradient-to-r from-blue-500 to-blue-600';
    
    const icon = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    }[type] || 'fa-info-circle';
    
    notification.className = `notification-toast fixed top-6 right-6 z-[9999] ${bgColor} text-white px-6 py-4 rounded-xl max-w-md transform translate-x-full transition-all duration-500 ease-out border border-white/20`;
    
    notification.innerHTML = `
        <div class="flex items-start space-x-3">
            <div class="flex-shrink-0 mt-0.5">
                <i class="fas ${icon} text-lg"></i>
            </div>
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium leading-5">${message}</p>
            </div>
            <button class="flex-shrink-0 ml-4 text-white/80 hover:text-white transition-colors duration-200" onclick="removeDashboardNotification(this.closest('div').closest('div'))">
                <i class="fas fa-times text-sm"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
        notification.classList.add('translate-x-0');
    }, 100);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        removeDashboardNotification(notification);
    }, 5000);
}

function removeDashboardNotification(notification) {
    if (notification && notification.parentNode) {
        notification.classList.add('notification-removing');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 500);
    }
}

// Admin functions
window.deleteItem = function(type, id, name) {
    showConfirmModal(
        'Confirm Delete',
        `Are you sure you want to delete "${name}"? This action cannot be undone.`,
        function() {
            fetch(`/admin/${type}/${id}/delete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Item deleted successfully', 'success');
                    location.reload();
                } else {
                    showNotification(data.message || 'Delete failed', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Delete failed', 'error');
            });
        }
    );
};

window.editItem = function(type, id) {
    window.location.href = `/admin/${type}/${id}/edit`;
};

// Initialize edit buttons for watch history
function initializeEditButtons() {
    const editButtons = document.querySelectorAll('.edit-history-btn');
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const episodeId = this.getAttribute('data-episode-id');
            const episodeTitle = this.getAttribute('data-episode-title');
            const contentId = this.getAttribute('data-content-id');
            showEditModal(episodeId, episodeTitle, contentId);
        });
    });
}