/**
 * static/js/my_fridge.js
 */

const Utils = {
    getCsrfToken: () => document.querySelector('#csrf-token')?.dataset.token || '',
    debounce: (func, wait) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    },
    calculateDday: (expiryDateStr) => {
        if (!expiryDateStr) return { label: '-', isUrgent: false };
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const expiry = new Date(expiryDateStr);
        expiry.setHours(0, 0, 0, 0);
        const diffTime = expiry - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays < 0) return { label: '만료', isUrgent: true };
        if (diffDays === 0) return { label: 'D-Day', isUrgent: true };
        const isUrgent = diffDays <= 3;
        return { label: `D-${diffDays}`, isUrgent: isUrgent };
    }
};

class MyFridgeManager {
    constructor() {
        this.initElements();
        if (this.listContainer || document.getElementById('shelfListContainer')) {
            this.init();
        }
    }

    initElements() {
        this.listContainer = document.getElementById('fridgeList'); 
        this.emptyState = document.getElementById('emptyState');    
        this.categoryFilter = document.getElementById('categoryFilter');
        this.searchInput = document.getElementById('searchInput');
        
        // [중요] HTML에 있는 수정 모달 요소들 연결
        this.editModal = document.getElementById('editModal');
        this.modalTitle = document.getElementById('modalIngredientName');
        this.expiryInput = document.getElementById('expiryInput');
        this.confirmBtn = document.getElementById('confirmBtn');
        this.cancelBtn = document.getElementById('cancelBtn');

        this.ingredients = []; 
        this.currentCategory = 'all';
        this.currentTargetId = null;
    }

    async init() {
        this.attachEventListeners();
        await this.fetchCategories();
        await this.fetchMyIngredients();
    }

    attachEventListeners() {
        if (this.searchInput) {
            this.searchInput.addEventListener('input', Utils.debounce((e) => {
                this.filterIngredients(e.target.value);
            }, 300));
        }
        
        // 모달 버튼 이벤트
        if (this.cancelBtn) this.cancelBtn.addEventListener('click', () => this.closeModal());
        if (this.confirmBtn) this.confirmBtn.addEventListener('click', () => this.updateIngredient());
    }

    async fetchCategories() {
        if (!this.categoryFilter) return;
        try {
            const res = await fetch('/ingredients/api/categories/');
            const categories = await res.json();
            this.renderCategoryFilter(categories);
        } catch (err) { console.error(err); }
    }

    async fetchMyIngredients() {
        try {
            const res = await fetch('/ingredients/api/user-ingredients/?include_expired=true');
            const data = await res.json();
            this.ingredients = Array.isArray(data) ? data : (data.results || []);
            this.renderList(this.ingredients);
        } catch (err) { 
            console.error(err); 
            this.showEmptyState();
        }
    }

    renderCategoryFilter(categories) {
        let html = `<div class="filter-chip active" data-id="all">전체</div>`;
        categories.forEach(cat => {
            html += `<div class="filter-chip" data-id="${cat.id}">${cat.name}</div>`;
        });
        this.categoryFilter.innerHTML = html;

        this.categoryFilter.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                this.categoryFilter.querySelector('.active').classList.remove('active');
                chip.classList.add('active');
                this.currentCategory = chip.dataset.id;
                this.filterIngredients(this.searchInput.value);
            });
        });
    }

    filterIngredients(keyword) {
        let filtered = this.ingredients;
        if (this.currentCategory !== 'all') {
            const catId = parseInt(this.currentCategory);
            // 카테고리 ID 매칭 로직 (API 데이터 구조에 따라 수정 가능)
            // 여기서는 전체를 다시 그리는 방식으로 처리
        }
        if (keyword) {
            filtered = filtered.filter(item => item.ingredient_name.includes(keyword));
        }
        this.renderList(filtered);
    }

    renderList(items) {
        const container = document.getElementById('shelfListContainer'); 
        const emptyState = document.getElementById('emptyState');
        
        if (!container) return;

        if (!items || items.length === 0) {
            container.innerHTML = '';
            container.style.display = 'none';
            if(emptyState) emptyState.style.display = 'block';
            return;
        }

        if(emptyState) emptyState.style.display = 'none';
        container.innerHTML = '';
        container.style.display = 'grid'; // Grid 보이게 설정

        items.forEach(item => {
            const dDay = Utils.calculateDday(item.expire_at);
            const iconUrl = item.icon_url || '/static/images/categories/etc.png';

            const itemDiv = document.createElement('div');
            itemDiv.className = 'shelf-item';
            
            const dDayClass = dDay.isUrgent ? 'd-day-tag urgent' : 'd-day-tag';

            itemDiv.innerHTML = `
                <div class="${dDayClass}">${dDay.label}</div>
                <img src="${iconUrl}" class="ingredient-icon" alt="${item.ingredient_name}" 
                     onerror="this.src='/static/images/categories/etc.png'">
                <div class="shelf-base"></div>
                <div class="ingredient-name">${item.ingredient_name}</div>
            `;

            // 클릭 시 수정 모달 열기
            itemDiv.addEventListener('click', () => this.openEditModal(item));
            container.appendChild(itemDiv);
        });
    }

    showEmptyState() {
        if(this.emptyState) this.emptyState.style.display = 'block';
        const container = document.getElementById('shelfListContainer');
        if(container) container.style.display = 'none';
    }

    // [중요] 모달 열기 함수
    openEditModal(userIngredient) {
        this.currentTargetId = userIngredient.user_ingredient_id;
        this.modalTitle.textContent = userIngredient.ingredient_name;
        this.expiryInput.value = userIngredient.expire_at || '';
        
        // 수정 모달 표시
        this.editModal.style.display = 'flex';
        this.editModal.classList.add('open');
    }

    closeModal() {
        this.editModal.style.display = 'none';
        this.editModal.classList.remove('open');
        this.currentTargetId = null;
    }

    async updateIngredient() {
        if (!this.currentTargetId) return;
        const newDate = this.expiryInput.value;
        const payload = { expire_at: newDate || null };
        
        try {
            const res = await fetch(`/ingredients/api/user-ingredients/${this.currentTargetId}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': Utils.getCsrfToken()
                },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                this.closeModal();
                await this.fetchMyIngredients(); // 목록 새로고침
            } else {
                alert('수정 실패');
            }
        } catch (err) { console.error(err); }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new MyFridgeManager();
});