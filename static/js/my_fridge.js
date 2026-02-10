/**
 * static/js/my_fridge.js
 * 내 냉장고 조회 및 관리 기능
 */

// ==========================================
// 1. 공통 유틸리티 (필수)
// ==========================================
const Utils = {
    getCsrfToken: () => {
        return document.querySelector('#csrf-token')?.getAttribute('data-token') || '';
    },
    debounce: (func, wait) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func(...args), wait);
        };
    },
    calculateDday: (expiryDateStr) => {
        if (!expiryDateStr) return { label: '-', isUrgent: false, text: '' };
        
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        const expiry = new Date(expiryDateStr);
        expiry.setHours(0, 0, 0, 0);
        
        const diffTime = expiry - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays < 0) return { label: '만료', isUrgent: true, text: '만료' }; 
        if (diffDays === 0) return { label: 'D-Day', isUrgent: true, text: '오늘' };
        
        const isUrgent = diffDays <= 3;
        return { label: `D-${diffDays}`, isUrgent: isUrgent, text: `${diffDays}일 전` };
    }
};

// ==========================================
// 2. 내 냉장고 매니저
// ==========================================
class MyFridgeManager {
    constructor() {
        this.initElements();
        // 컨테이너가 있는 경우에만 실행
        if (this.listContainer) {
            this.init();
        }
    }

    initElements() {
        // [중요 수정] my_fridge.html의 실제 ID인 'fridgeList'로 변경
        this.listContainer = document.getElementById('fridgeList'); 
        this.emptyState = document.getElementById('emptyState');    
        this.categoryFilter = document.getElementById('categoryFilter');
        this.searchInput = document.getElementById('searchInput');
        
        // 모달 관련
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

        if (this.cancelBtn) {
            this.cancelBtn.addEventListener('click', () => this.closeModal());
        }
        if (this.confirmBtn) {
            this.confirmBtn.addEventListener('click', () => this.updateIngredient());
        }
    }

    // --- API Calls ---
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

    // --- Render ---
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

        // 1. 카테고리 필터
        if (this.currentCategory !== 'all') {
            const catId = parseInt(this.currentCategory);
            filtered = filtered.filter(item => {
                // item.ingredient.category가 객체일 수도 있고 ID일 수도 있음
                const catInfo = item.ingredient.category;
                const itemId = (typeof catInfo === 'object') ? catInfo.id : catInfo;
                return itemId === catId;
            });
        }

        // 2. 검색어 필터
        if (keyword) {
            filtered = filtered.filter(item => item.ingredient_name.includes(keyword));
        }

        this.renderList(filtered);
    }

    renderList(items) {
        if (!items || items.length === 0) {
            this.showEmptyState();
            return;
        }

        this.showListState();
        this.listContainer.innerHTML = '';

        items.forEach(item => {
            const dDay = Utils.calculateDday(item.expire_at);
            const isExpired = dDay.isUrgent; // 만료 또는 임박
            
            // 아이콘 이미지
            const iconName = item.ingredient.icon_name || null;
            const iconHtml = iconName 
                ? `<img src="/static/images/icons/${iconName}" class="item-img" onerror="this.src='/static/images/icons/default_food.png'">` 
                : `<div style="font-size:24px;">🍽️</div>`;

            // [중요] my_fridge.css 클래스 (.fridge-item) 사용
            const card = document.createElement('div');
            card.className = 'fridge-item';
            
            // 만료/임박 시 스타일 강조
            const wrapperStyle = isExpired ? 'border: 1px solid #FF5252; background-color: #FFF0F0;' : '';
            const ddayStyle = isExpired ? 'color:#FF5252; font-weight:bold;' : '';

            // my_fridge.css 구조에 맞춘 HTML 생성
            card.innerHTML = `
                <div class="item-icon-wrapper" style="${wrapperStyle}">
                    ${iconHtml}
                    <span class="item-dday" style="${ddayStyle}">${dDay.label}</span>
                </div>
                <div class="item-name">${item.ingredient_name}</div>
            `;

            card.addEventListener('click', () => this.openEditModal(item));
            this.listContainer.appendChild(card);
        });
    }

    showEmptyState() {
        if(this.emptyState) this.emptyState.style.display = 'block';
        if(this.listContainer) this.listContainer.style.display = 'none';
    }

    showListState() {
        if(this.emptyState) this.emptyState.style.display = 'none';
        if(this.listContainer) this.listContainer.style.display = 'grid'; // CSS Grid 활성화
    }

    // --- Modal ---
    openEditModal(userIngredient) {
        this.currentTargetId = userIngredient.user_ingredient_id;
        
        const catInfo = userIngredient.ingredient.category;
        const catId = (typeof catInfo === 'object') ? catInfo.id : catInfo;

        this.modalTitle.textContent = userIngredient.ingredient_name;
        this.expiryInput.value = userIngredient.expire_at || '';
        
        let nameInput = document.getElementById('nameEditInput');
        if (!nameInput) {
            nameInput = document.createElement('input');
            nameInput.id = 'nameEditInput';
            nameInput.type = 'text';
            nameInput.className = 'date-picker';
            nameInput.style.marginBottom = '10px';
            nameInput.placeholder = '재료 이름 수정';
            this.expiryInput.parentNode.insertBefore(nameInput, this.expiryInput);
        }

        if (catId === 17) {
            nameInput.style.display = 'block';
            nameInput.value = userIngredient.ingredient_name;
            this.modalTitle.style.display = 'none';
        } else {
            nameInput.style.display = 'none';
            this.modalTitle.style.display = 'block';
        }

        this.editModal.style.display = 'flex';
    }

    closeModal() {
        this.editModal.style.display = 'none';
        this.currentTargetId = null;
    }

    async updateIngredient() {
        if (!this.currentTargetId) return;
        
        const newDate = this.expiryInput.value;
        const nameInput = document.getElementById('nameEditInput');
        const newName = (nameInput && nameInput.style.display === 'block') ? nameInput.value : null;

        const payload = { expire_at: newDate || null };
        if (newName) payload.ingredient_name = newName;
        
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
                await this.fetchMyIngredients(); 
            } else {
                alert('수정 실패');
            }
        } catch (err) { console.error(err); }
    }
}

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    new MyFridgeManager();
});