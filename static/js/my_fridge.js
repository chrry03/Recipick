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
        // ... (기존 요소 연결 코드 그대로 유지) ...
        this.listContainer = document.getElementById('fridgeList'); 
        this.emptyState = document.getElementById('emptyState');    
        this.categoryFilter = document.getElementById('categoryFilter');
        this.searchInput = document.getElementById('searchInput');
        
        this.editModal = document.getElementById('editModal');
        this.modalTitle = document.getElementById('modalIngredientName');
        this.expiryInput = document.getElementById('expiryInput');
        this.confirmBtn = document.getElementById('confirmBtn');
        this.cancelBtn = document.getElementById('cancelBtn');

        this.ingredients = []; 
        this.currentCategory = 'all'; // 현재 선택된 카테고리
        this.currentTargetId = null;
    }

    async init() {
        this.attachEventListeners();
        // [수정] fetchCategories()는 제거합니다. (재료 데이터 기반으로 생성하므로)
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
            
            // 데이터 저장
            this.ingredients = Array.isArray(data) ? data : (data.results || []);
            
            // [핵심] 재료 데이터를 기반으로 카테고리 필터 생성
            this.generateCategoryChips();
            
            // 리스트 렌더링
            this.filterIngredients(this.searchInput.value);
            
        } catch (err) { 
            console.error(err); 
            this.showEmptyState();
        }
    }

    // [신규 기능] 현재 재료에 있는 카테고리만 추출하여 칩 생성
    generateCategoryChips() {
        if (!this.categoryFilter) return;

        // 1. 카테고리별 개수 계산
        const counts = {};
        this.ingredients.forEach(item => {
            // API에서 category_name을 받아온다고 가정 (UserIngredientSerializer 확인됨)
            const catName = item.category_name || '기타';
            counts[catName] = (counts[catName] || 0) + 1;
        });

        // 2. 카테고리 이름 정렬 (가나다순)
        const sortedCategories = Object.keys(counts).sort();

        // 3. HTML 생성
        // (1) 전체 탭
        let html = `
            <button class="filter-chip active" data-cat="all">
                전체(${this.ingredients.length})
            </button>
        `;

        // (2) 개별 카테고리 탭
        sortedCategories.forEach(catName => {
            html += `
                <button class="filter-chip" data-cat="${catName}">
                    ${catName}(${counts[catName]})
                </button>
            `;
        });

        this.categoryFilter.innerHTML = html;

        // 4. 클릭 이벤트 연결
        this.categoryFilter.querySelectorAll('.filter-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                // 활성화 스타일 변경
                this.categoryFilter.querySelector('.active')?.classList.remove('active');
                chip.classList.add('active');
                
                // 필터링 실행
                this.currentCategory = chip.dataset.cat;
                this.filterIngredients(this.searchInput.value);
            });
        });
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
// [수정] 필터링 로직 (ID 대신 이름 사용)
    filterIngredients(keyword) {
        let filtered = this.ingredients;

        // 1. 카테고리 필터링
        if (this.currentCategory !== 'all') {
            filtered = filtered.filter(item => {
                const catName = item.category_name || '기타';
                return catName === this.currentCategory;
            });
        }

        // 2. 검색어 필터링
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

            // [핵심 수정] onerror 무한루프 방지 코드 추가
            itemDiv.innerHTML = `
                <div class="${dDayClass}">${dDay.label}</div>
                <img src="${iconUrl}" class="ingredient-icon" alt="${item.ingredient_name}" 
                     onerror="this.onerror=null; this.src='/static/images/categories/etc.png';">
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